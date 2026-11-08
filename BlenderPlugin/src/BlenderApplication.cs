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

    // Links the plugin to Blender so that the console switches to the Blender
    // profile when Blender comes to the foreground.

    public class BlenderApplication : ClientApplication
    {
        private const String MacBundleName = "org.blenderfoundation.blender";
        private const String MacApplicationPath = "/Applications/Blender.app";

        // Windows process name of blender.exe, without the extension. The same
        // name is what the bridge already used on macOS. Options+ uses this,
        // not a mouse-model id, to decide that Blender is the foreground app.
        protected override String GetProcessName() => "blender";

        protected override String GetBundleName() => MacBundleName;

        public override ClientApplicationStatus GetApplicationStatus()
        {
            // macOS behavior is unchanged: Installed only when Blender.app is
            // in /Applications, otherwise Unknown.
            if (Directory.Exists(MacApplicationPath))
            {
                return ClientApplicationStatus.Installed;
            }

            if (BlenderInstallProbe.IsWindowsInstallPresent())
            {
                return ClientApplicationStatus.Installed;
            }

            return ClientApplicationStatus.Unknown;
        }
    }
}
