// Blender MX Creative - drive Blender from a Logitech MX Creative Console
// Copyright (C) 2026 Michal Fanta
//
// This program is free software: you can redistribute it and/or modify it
// under the terms of the GNU General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option)
// any later version.
//
// This program is distributed in the hope that it will be useful, but WITHOUT
// ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
// FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License along with
// this program. If not, see <https://www.gnu.org/licenses/>.

namespace Loupedeck.BlenderPlugin
{
    using System;
    using System.Collections.Generic;
    using System.IO;
    using System.Net.Sockets;
    using System.Text;
    using System.Text.Json;
    using System.Threading;

    // Talks to the "MX Console Bridge" add-on over loopback TCP.
    //
    // One request per line of JSON, one response per line. Every response carries
    // a full state snapshot, so a successful command doubles as a state refresh.
    //
    // When the add-on is not running, Invoke reports Unreachable and the caller falls
    // back to sending a keyboard shortcut instead.

    // Why a command did not take effect. The distinction matters: falling back to
    // a keystroke is right when Blender could not be reached, and wrong when
    // Blender heard the command and refused it.
    public enum BridgeResult
    {
        Unreachable,
        Rejected,
        Ok,
    }

    public sealed class BlenderBridge : IDisposable
    {
        public const Int32 DefaultPort = 47800;

        private static readonly TimeSpan ReconnectCooldown = TimeSpan.FromSeconds(2);
        private static readonly TimeSpan PollInterval = TimeSpan.FromMilliseconds(400);
        private const Int32 RequestTimeoutMs = 2000;

        private readonly Object _lock = new Object();

        private TcpClient _client;
        private StreamWriter _writer;
        private StreamReader _reader;
        private DateTime _nextConnectAttempt = DateTime.MinValue;
        private Int32 _nextRequestId;

        private Timer _pollTimer;
        private Boolean _polling;

        public Int32 Port { get; set; } = DefaultPort;

        public Boolean IsConnected { get; private set; }

        public BlenderState State { get; private set; } = new BlenderState();

        // Raised when the state snapshot or the connection status actually changed.
        public event EventHandler Changed;

        public void StartPolling()
        {
            lock (this._lock)
            {
                if (this._polling)
                {
                    return;
                }

                this._polling = true;
                this._pollTimer = new Timer(this.Poll, null, TimeSpan.Zero, PollInterval);
            }
        }

        public void StopPolling()
        {
            lock (this._lock)
            {
                this._polling = false;
                this._pollTimer?.Dispose();
                this._pollTimer = null;
            }

            this.Disconnect();
        }

        // Sends a command and reports how it went.
        public BridgeResult Invoke(String command, Object arguments = null)
        {
            var request = new Dictionary<String, Object>
            {
                ["id"] = Interlocked.Increment(ref this._nextRequestId),
                ["cmd"] = command,
            };

            if (arguments != null)
            {
                request["args"] = arguments;
            }

            // Absent or empty token file: omit auth, which is what the tested
            // installs send. The add-on ignores the field until its preference is set.
            var token = BridgeToken.Current();
            if (!String.IsNullOrEmpty(token))
            {
                request["auth"] = token;
            }

            if (!this.Exchange(request, out var response))
            {
                return BridgeResult.Unreachable;
            }

            if (!response.TryGetProperty("ok", out var ok) || ok.ValueKind != JsonValueKind.True)
            {
                var error = response.TryGetProperty("error", out var e) ? e.GetString() : "unknown error";
                PluginLog.Warning($"Blender rejected '{command}': {error}");
                return BridgeResult.Rejected;
            }

            return BridgeResult.Ok;
        }

        public void Refresh() => this.Invoke("state");

        private void Poll(Object _)
        {
            try
            {
                this.Refresh();
            }
            catch (Exception ex)
            {
                PluginLog.Verbose(ex, "Polling Blender failed");
            }
        }

        private Boolean Exchange(Dictionary<String, Object> request, out JsonElement response)
        {
            response = default;

            lock (this._lock)
            {
                if (!this.EnsureConnected())
                {
                    return false;
                }

                try
                {
                    this._writer.WriteLine(JsonSerializer.Serialize(request));
                    var line = this._reader.ReadLine();
                    if (line == null)
                    {
                        this.DisconnectLocked();
                        return false;
                    }

                    response = JsonDocument.Parse(line).RootElement;
                }
                catch (Exception ex) when (ex is IOException || ex is SocketException || ex is JsonException)
                {
                    PluginLog.Verbose(ex, "Blender bridge request failed");
                    this.DisconnectLocked();
                    return false;
                }
            }

            this.UpdateState(response);
            return true;
        }

        private void UpdateState(JsonElement response)
        {
            if (!response.TryGetProperty("state", out var stateElement))
            {
                return;
            }

            var state = BlenderState.Parse(stateElement);
            if (state.SameAs(this.State))
            {
                return;
            }

            this.State = state;
            this.Changed?.Invoke(this, EventArgs.Empty);
        }

        private Boolean EnsureConnected()
        {
            if (this._client != null && this._client.Connected)
            {
                return true;
            }

            if (DateTime.UtcNow < this._nextConnectAttempt)
            {
                return false;
            }

            this.DisconnectLocked();
            this._nextConnectAttempt = DateTime.UtcNow + ReconnectCooldown;

            var client = new TcpClient { NoDelay = true };
            try
            {
                client.Connect("127.0.0.1", this.Port);
                client.ReceiveTimeout = RequestTimeoutMs;
                client.SendTimeout = RequestTimeoutMs;

                var stream = client.GetStream();
                this._client = client;
                this._reader = new StreamReader(stream, new UTF8Encoding(false));
                this._writer = new StreamWriter(stream, new UTF8Encoding(false)) { AutoFlush = true, NewLine = "\n" };

                this.SetConnected(true);
                PluginLog.Info($"Connected to the Blender bridge on port {this.Port}");
                return true;
            }
            catch (SocketException)
            {
                // The add-on is not running (or Blender is closed); the caller falls
                // back to keystrokes. Dispose here or every retry leaks a socket.
                client.Dispose();
                return false;
            }
        }

        private void Disconnect()
        {
            lock (this._lock)
            {
                this.DisconnectLocked();
            }
        }

        private void DisconnectLocked()
        {
            this._writer?.Dispose();
            this._reader?.Dispose();
            this._client?.Dispose();
            this._writer = null;
            this._reader = null;
            this._client = null;

            this.SetConnected(false);
        }

        private void SetConnected(Boolean connected)
        {
            if (this.IsConnected == connected)
            {
                return;
            }

            this.IsConnected = connected;
            this.Changed?.Invoke(this, EventArgs.Empty);
        }

        public void Dispose() => this.StopPolling();
    }
}
