using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

/// <summary>
/// Minimal launcher — finds pythonw.exe and runs main.py from the app folder.
/// No console window. Fast startup (< 1 second to visible window).
/// </summary>
static class Launcher
{
    [STAThread]
    static void Main()
    {
        // App folder = directory this EXE lives in
        string appDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\', '/');

        // Find pythonw.exe: check venv first, then PATH
        string pythonw = FindPythonW(appDir);
        if (pythonw == null)
        {
            MessageBox.Show(
                "Could not find pythonw.exe.\n\n" +
                "Please ensure Python 3.12 is installed and on your PATH,\n" +
                "or place a .venv folder next to this EXE.",
                "Picture Flipper — Python Not Found",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return;
        }

        string mainPy = Path.Combine(appDir, "main.py");
        if (!File.Exists(mainPy))
        {
            MessageBox.Show(
                "main.py not found next to this EXE.\n\nPath: " + mainPy,
                "Picture Flipper — Missing File",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return;
        }

        var psi = new ProcessStartInfo
        {
            FileName = pythonw,
            Arguments = "\"" + mainPy + "\"",
            WorkingDirectory = appDir,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        try { Process.Start(psi); }
        catch (Exception ex)
        {
            MessageBox.Show("Failed to launch:\n" + ex.Message,
                "Picture Flipper — Launch Error",
                MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    static string FindPythonW(string appDir)
    {
        // 1. .venv next to the EXE (recommended — matches dev environment)
        string venvPy = Path.Combine(appDir, ".venv", "Scripts", "pythonw.exe");
        if (File.Exists(venvPy)) return venvPy;

        // 2. venv one level up (repo root venv)
        string upVenvPy = Path.Combine(appDir, "..", ".venv", "Scripts", "pythonw.exe");
        if (File.Exists(upVenvPy)) return Path.GetFullPath(upVenvPy);

        // 3. System PATH
        string pathEnv = Environment.GetEnvironmentVariable("PATH") ?? "";
        foreach (string dir in pathEnv.Split(';'))
        {
            string candidate = Path.Combine(dir.Trim(), "pythonw.exe");
            if (File.Exists(candidate)) return candidate;
        }

        return null;
    }
}
