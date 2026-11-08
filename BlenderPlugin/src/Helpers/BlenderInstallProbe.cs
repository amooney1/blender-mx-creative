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

    // Answers "is Blender installed?" on Windows without inventing a device id.
    //
    // Foreground switching stays on ClientApplication.GetProcessName(), which
    // already returns "blender" (the process name of blender.exe, without the
    // extension). This probe only looks at well-known install locations so
    // Options+ can offer the application profile before that process has run.
    // It does not search the user profile, read documents, or start Blender.

    public static class BlenderInstallProbe
    {
        public static String FoundationDirectory(String programFiles) =>
            Path.Combine(programFiles, "Blender Foundation");

        public static String VersionlessExecutable(String programFiles) =>
            Path.Combine(FoundationDirectory(programFiles), "Blender", "blender.exe");

        public static String SteamExecutable(String programFilesX86) =>
            Path.Combine(programFilesX86, "Steam", "steamapps", "common", "Blender", "blender.exe");

        public static Boolean TreeContainsBlenderExe(IEnumerable<String> paths)
        {
            if (paths == null)
            {
                return false;
            }

            foreach (var path in paths)
            {
                if (String.Equals(Path.GetFileName(path), "blender.exe", StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            return false;
        }

        // programFiles / programFilesX86 are the two Program Files roots.
        // The delegates keep the disk access out of the unit test.
        public static Boolean IsInstallPresent(
            String programFiles,
            String programFilesX86,
            Func<String, Boolean> directoryExists,
            Func<String, IEnumerable<String>> enumerateBlenderExecutables,
            Func<String, Boolean> fileExists)
        {
            if (fileExists(VersionlessExecutable(programFiles)) || fileExists(SteamExecutable(programFilesX86)))
            {
                return true;
            }

            var foundation = FoundationDirectory(programFiles);
            if (!directoryExists(foundation))
            {
                return false;
            }

            try
            {
                return TreeContainsBlenderExe(enumerateBlenderExecutables(foundation));
            }
            catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException)
            {
                return false;
            }
        }

        public static Boolean IsWindowsInstallPresent()
        {
            if (!OperatingSystem.IsWindows())
            {
                return false;
            }

            var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
            var programFilesX86 = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86);
            return IsInstallPresent(
                programFiles,
                programFilesX86,
                Directory.Exists,
                foundation => Directory.EnumerateFiles(foundation, "blender.exe", SearchOption.AllDirectories),
                File.Exists);
        }
    }
}
