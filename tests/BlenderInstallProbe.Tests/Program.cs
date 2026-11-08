using System.Text;
using Loupedeck.BlenderPlugin;

var failures = new List<string>();

void Check(bool condition, string message)
{
    if (!condition)
    {
        failures.Add(message);
    }
}

var root = Path.Combine(Path.GetTempPath(), "blender-probe-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(root);
try
{
    var programFiles = Path.Combine(root, "pf");
    var programFilesX86 = Path.Combine(root, "pfx86");
    Directory.CreateDirectory(programFiles);
    Directory.CreateDirectory(programFilesX86);

    bool Missing(string _) => false;
    IEnumerable<string> NoFiles(string _) => Array.Empty<string>();

    Check(!BlenderInstallProbe.IsInstallPresent(programFiles, programFilesX86, Missing, NoFiles, Missing),
        "empty roots reported an install");

    var versioned = Path.Combine(programFiles, "Blender Foundation", "Blender 5.2", "blender.exe");
    Directory.CreateDirectory(Path.GetDirectoryName(versioned)!);
    File.WriteAllBytes(versioned, new byte[] { 0 });

    bool Dir(string path) => Directory.Exists(path);
    bool FileThere(string path) => File.Exists(path);
    IEnumerable<string> Enumerate(string foundation) =>
        Directory.EnumerateFiles(foundation, "blender.exe", SearchOption.AllDirectories);

    Check(BlenderInstallProbe.IsInstallPresent(programFiles, programFilesX86, Dir, Enumerate, FileThere),
        "versioned Blender Foundation install was not found");
    Check(BlenderInstallProbe.TreeContainsBlenderExe(new[] { versioned }),
        "blender.exe filename was not recognized");
    Check(!BlenderInstallProbe.TreeContainsBlenderExe(new[] { Path.Combine(programFiles, "notes.txt") }),
        "an unrelated file counted as Blender");

    var steam = BlenderInstallProbe.SteamExecutable(programFilesX86);
    Directory.CreateDirectory(Path.GetDirectoryName(steam)!);
    File.WriteAllBytes(steam, new byte[] { 0 });
    Check(FileThere(steam), "steam path was not the expected blender.exe");
    Check(BlenderInstallProbe.IsInstallPresent(Path.Combine(root, "absent"), programFilesX86, Missing, NoFiles, FileThere),
        "Steam blender.exe was not found");

    var thrown = false;
    try
    {
        BlenderInstallProbe.IsInstallPresent(
            programFiles,
            programFilesX86,
            _ => true,
            _ => throw new UnauthorizedAccessException("denied"),
            Missing);
    }
    catch (UnauthorizedAccessException)
    {
        thrown = true;
    }

    Check(!thrown, "an unreadable foundation directory escaped the probe");
    Check(!BlenderInstallProbe.IsWindowsInstallPresent() || OperatingSystem.IsWindows(),
        "non-Windows probe claimed a Windows install");

    Check(BridgeToken.Normalize("  local-secret  ") == "local-secret", "token trim");
    Check(BridgeToken.Normalize("") == "", "empty token");
    Check(BridgeToken.Normalize(null) == "", "null token");
    Check(BridgeToken.Normalize("one\ntwo") == "", "multiline token is not sent");
    Check(BridgeToken.Normalize(new string('a', BridgeToken.MaxLength + 1)) == "", "overlong token is not sent");
    var tokenPath = BridgeToken.TokenFilePath("appdata");
    Check(tokenPath.EndsWith(Path.Combine("PluginData", "Blender", "bridge.token"), StringComparison.Ordinal),
        "token file stays under PluginData");
    Check(tokenPath.IndexOf("Users", StringComparison.OrdinalIgnoreCase) < 0, "token helper did not invent a profile path");
}
finally
{
    Directory.Delete(root, recursive: true);
}

if (failures.Count > 0)
{
    Console.Error.WriteLine(string.Join(Environment.NewLine, failures));
    return 1;
}

Console.WriteLine("BlenderInstallProbe tests passed");
return 0;
