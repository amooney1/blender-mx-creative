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
    using System.IO;

    // Optional pairing secret for the loopback bridge.
    //
    // The file is absent in the tested Mac and Windows installs, and then the
    // plugin sends no auth field. Creating the file is a migration: the add-on
    // preference must hold the same value or every command is refused. Nothing
    // here creates the file, and the token is not written to the plugin log.

    public static class BridgeToken
    {
        public const Int32 MaxLength = 256;

        public static String TokenFilePath(String localAppData) =>
            Path.Combine(localAppData, "Logi", "LogiPluginService", "PluginData", "Blender", "bridge.token");

        // One line, trimmed, at most MaxLength characters. Anything else is
        // treated as "no token" so a damaged file does not get sent.
        public static String Normalize(String text)
        {
            if (String.IsNullOrEmpty(text))
            {
                return "";
            }

            var line = text.Trim();
            if (line.Length == 0 || line.Length > MaxLength)
            {
                return "";
            }

            if (line.IndexOfAny(new[] { '\r', '\n', '\0' }) >= 0)
            {
                return "";
            }

            return line;
        }

        public static String Current()
        {
            try
            {
                var root = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                var path = TokenFilePath(root);
                if (!File.Exists(path))
                {
                    return "";
                }

                return Normalize(File.ReadAllText(path));
            }
            catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException)
            {
                return "";
            }
        }
    }
}
