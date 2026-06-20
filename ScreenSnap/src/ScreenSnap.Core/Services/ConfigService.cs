using System.Text.Json;
using ScreenSnap.Core.Models;

namespace ScreenSnap.Core.Services;

public class ConfigService
{
    private static readonly string ConfigPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "ScreenSnap", "config.json");

    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    public CaptureSettings Settings { get; private set; } = new();

    public void Load()
    {
        if (!File.Exists(ConfigPath)) return;
        var json = File.ReadAllText(ConfigPath);
        Settings = JsonSerializer.Deserialize<CaptureSettings>(json, JsonOptions) ?? new();
    }

    public void Save()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(ConfigPath)!);
        File.WriteAllText(ConfigPath, JsonSerializer.Serialize(Settings, JsonOptions));
    }
}
