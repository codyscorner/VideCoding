using System.IO;
using System.Windows;
using Hardcodet.Wpf.TaskbarNotification;
using SkiaSharp;
using ScreenSnap.Core.Capture;
using ScreenSnap.Core.Services;
using ScreenSnap.Core.Win32;
using ScreenSnap.UI.Services;
using ScreenSnap.UI.ViewModels;
using ScreenSnap.UI.Views;

namespace ScreenSnap.UI;

public partial class App : Application
{
    private TaskbarIcon? _trayIcon;
    private HotkeyWindow? _hotkeyWindow;
    private readonly ConfigService _config = new();
    private readonly GdiCaptureService _captureService = new();

    private void App_OnStartup(object sender, StartupEventArgs e)
    {
        _config.Load();

        _hotkeyWindow = new HotkeyWindow();
        _hotkeyWindow.Initialize();
        RegisterHotkeys();

        _trayIcon = new TaskbarIcon
        {
            ToolTipText = "ScreenSnap",
            ContextMenu = BuildTrayMenu(),
        };
    }

    // ------------------------------------------------------------------
    // Hotkeys
    // ------------------------------------------------------------------

    private readonly List<int> _hotkeyIds = new();

    private void RegisterHotkeys()
    {
        var h = _config.Settings.Hotkeys;
        BindHotkey(h.RegionCapture,  async () => await StartRegionCaptureAsync());
        BindHotkey(h.FullScreen,     async () => await StartFullScreenCaptureAsync());
        BindHotkey(h.ActiveWindow,   async () => await StartWindowCaptureAsync());
    }

    private void BindHotkey(string hotkeyString, Action callback)
    {
        var (mods, vk) = HotkeyParser.Parse(hotkeyString);
        int id = _hotkeyWindow!.Register(mods, vk, callback);
        if (id >= 0)
            _hotkeyIds.Add(id);
        else
            ShowTrayWarning($"Could not register hotkey: {hotkeyString}\n(already claimed by another app)");
    }

    // Called from SettingsWindow after the user saves new hotkeys
    public void ReloadHotkeys()
    {
        foreach (var id in _hotkeyIds) _hotkeyWindow?.Unregister(id);
        _hotkeyIds.Clear();
        RegisterHotkeys();
    }

    // ------------------------------------------------------------------
    // Capture actions
    // ------------------------------------------------------------------

    private async Task StartRegionCaptureAsync()
    {
        // Must run on the UI thread (the overlay is a WPF window)
        await Dispatcher.InvokeAsync(async () =>
        {
            var overlay = new RegionSelectOverlay();
            if (overlay.ShowDialog() != true || overlay.SelectedRegion.IsEmpty) return;

            var dpiScale = ScreenInfo.GetSystemDpiScale();
            var r = overlay.SelectedRegion;
            var physRegion = new SKRectI(
                (int)(r.X * dpiScale),
                (int)(r.Y * dpiScale),
                (int)((r.X + r.Width) * dpiScale),
                (int)((r.Y + r.Height) * dpiScale));

            var bitmap = await _captureService.CaptureRegionAsync(physRegion);
            HandleCaptureResult(bitmap);
        });
    }

    private async Task StartFullScreenCaptureAsync()
    {
        var bitmap = await _captureService.CaptureFullScreenAsync();
        await Dispatcher.InvokeAsync(() => HandleCaptureResult(bitmap));
    }

    private async Task StartWindowCaptureAsync()
    {
        // Snapshot the foreground window BEFORE we do anything that might shift focus
        var hwnd = ScreenInfo.GetForegroundWindow();
        if (hwnd == IntPtr.Zero) return;

        // Brief delay so the hotkey keyup doesn't appear in the capture
        await Task.Delay(150);

        var bitmap = await _captureService.CaptureWindowAsync(hwnd);
        await Dispatcher.InvokeAsync(() => HandleCaptureResult(bitmap));
    }

    // Routes the captured bitmap to the editor or saves silently based on settings.
    private void HandleCaptureResult(SKBitmap bitmap)
    {
        if (_config.Settings.Behavior.OpenEditorAfterCapture)
        {
            var vm = new EditorViewModel(_config);
            vm.SourceBitmap = bitmap;
            new EditorWindow(vm).Show();
        }
        else
        {
            SaveSilently(bitmap);
        }
    }

    private void SaveSilently(SKBitmap bitmap)
    {
        try
        {
            var s = _config.Settings;
            var path = ImageExporter.BuildAutoSavePath(s.AutoSavePath, s.FileNamePattern);
            File.WriteAllBytes(path, ImageExporter.EncodePng(bitmap));

            if (s.Behavior.CopyToClipboardAfterSave)
                WpfClipboard.SetImage(bitmap);

            if (s.Behavior.ShowTrayNotifications)
                ShowTrayInfo($"Saved: {Path.GetFileName(path)}");
        }
        catch (Exception ex)
        {
            ShowTrayWarning($"Save failed: {ex.Message}");
        }
        finally
        {
            bitmap.Dispose();
        }
    }

    // ------------------------------------------------------------------
    // Tray
    // ------------------------------------------------------------------

    private System.Windows.Controls.ContextMenu BuildTrayMenu()
    {
        var menu = new System.Windows.Controls.ContextMenu();

        Add("Capture Region\tCtrl+Shift+4",  async () => await StartRegionCaptureAsync());
        Add("Full Screen\tCtrl+Shift+3",     async () => await StartFullScreenCaptureAsync());
        Add("Active Window\tCtrl+Shift+5",   async () => await StartWindowCaptureAsync());
        menu.Items.Add(new System.Windows.Controls.Separator());
        AddItem("Settings…", OpenSettings);
        menu.Items.Add(new System.Windows.Controls.Separator());
        AddItem("Exit", () => Shutdown());

        return menu;

        void Add(string header, Action click)
        {
            var item = new System.Windows.Controls.MenuItem { Header = header };
            item.Click += (_, _) => click();
            menu.Items.Add(item);
        }

        void AddItem(string header, Action click)
        {
            var item = new System.Windows.Controls.MenuItem { Header = header };
            item.Click += (_, _) => click();
            menu.Items.Add(item);
        }
    }

    private void OpenSettings()
    {
        var vm = new SettingsViewModel(_config);
        vm.HotkeysReloaded += ReloadHotkeys;
        new SettingsWindow(vm).ShowDialog();
    }

    private void ShowTrayInfo(string message)
        => _trayIcon?.ShowBalloonTip("ScreenSnap", message, BalloonIcon.Info);

    private void ShowTrayWarning(string message)
        => _trayIcon?.ShowBalloonTip("ScreenSnap", message, BalloonIcon.Warning);

    protected override void OnExit(ExitEventArgs e)
    {
        _hotkeyWindow?.Dispose();
        _trayIcon?.Dispose();
        base.OnExit(e);
    }
}
