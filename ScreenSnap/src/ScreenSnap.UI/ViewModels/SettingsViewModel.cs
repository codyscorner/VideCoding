using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ScreenSnap.Core.Models;
using ScreenSnap.Core.Services;

namespace ScreenSnap.UI.ViewModels;

public partial class SettingsViewModel : ObservableObject
{
    private readonly ConfigService _config;

    [ObservableProperty] private string _regionHotkey = "Ctrl+Shift+4";
    [ObservableProperty] private string _fullScreenHotkey = "Ctrl+Shift+3";
    [ObservableProperty] private string _activeWindowHotkey = "Ctrl+Shift+5";
    [ObservableProperty] private bool _openEditorAfterCapture = true;
    [ObservableProperty] private bool _copyToClipboardAfterSave = true;
    [ObservableProperty] private bool _showTrayNotifications = true;
    [ObservableProperty] private string _autoSavePath = @"%USERPROFILE%\Screenshots";

    // Raised after Save() when hotkeys were changed; App re-registers Win32 hotkeys
    public event Action? HotkeysReloaded;

    public SettingsViewModel(ConfigService config)
    {
        _config = config;
        LoadFromSettings(config.Settings);
    }

    [RelayCommand]
    private void Save()
    {
        bool hotkeysChanged =
            _config.Settings.Hotkeys.RegionCapture != RegionHotkey ||
            _config.Settings.Hotkeys.FullScreen    != FullScreenHotkey ||
            _config.Settings.Hotkeys.ActiveWindow  != ActiveWindowHotkey;

        _config.Settings.Hotkeys.RegionCapture = RegionHotkey;
        _config.Settings.Hotkeys.FullScreen = FullScreenHotkey;
        _config.Settings.Hotkeys.ActiveWindow = ActiveWindowHotkey;
        _config.Settings.Behavior.OpenEditorAfterCapture = OpenEditorAfterCapture;
        _config.Settings.Behavior.CopyToClipboardAfterSave = CopyToClipboardAfterSave;
        _config.Settings.Behavior.ShowTrayNotifications = ShowTrayNotifications;
        _config.Settings.AutoSavePath = AutoSavePath;
        _config.Save();

        if (hotkeysChanged)
            HotkeysReloaded?.Invoke();
    }

    private void LoadFromSettings(CaptureSettings s)
    {
        RegionHotkey = s.Hotkeys.RegionCapture;
        FullScreenHotkey = s.Hotkeys.FullScreen;
        ActiveWindowHotkey = s.Hotkeys.ActiveWindow;
        OpenEditorAfterCapture = s.Behavior.OpenEditorAfterCapture;
        CopyToClipboardAfterSave = s.Behavior.CopyToClipboardAfterSave;
        ShowTrayNotifications = s.Behavior.ShowTrayNotifications;
        AutoSavePath = s.AutoSavePath;
    }
}
