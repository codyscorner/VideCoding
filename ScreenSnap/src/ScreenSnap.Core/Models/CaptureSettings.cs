namespace ScreenSnap.Core.Models;

public class CaptureSettings
{
    public string DefaultFormat { get; set; } = "png";
    public int JpegQuality { get; set; } = 90;
    public bool IncludeMouseCursor { get; set; } = false;
    public string AutoSavePath { get; set; } = @"%USERPROFILE%\Screenshots";
    public string FileNamePattern { get; set; } = "Screenshot_{date}_{time}";
    public HotkeySettings Hotkeys { get; set; } = new();
    public EditorSettings Editor { get; set; } = new();
    public BehaviorSettings Behavior { get; set; } = new();
}

public class HotkeySettings
{
    public string RegionCapture { get; set; } = "Ctrl+Shift+4";
    public string FullScreen { get; set; } = "Ctrl+Shift+3";
    public string ActiveWindow { get; set; } = "Ctrl+Shift+5";
}

public class EditorSettings
{
    public string DefaultTool { get; set; } = "arrow";
    public string ArrowColor { get; set; } = "#FF0000";
    public int ArrowThickness { get; set; } = 3;
    public string TextFont { get; set; } = "Segoe UI";
    public int TextSize { get; set; } = 14;
    public string BubbleStyle { get; set; } = "speech";
}

public class BehaviorSettings
{
    public bool OpenEditorAfterCapture { get; set; } = true;
    public bool CopyToClipboardAfterSave { get; set; } = true;
    public bool ShowTrayNotifications { get; set; } = true;
}
