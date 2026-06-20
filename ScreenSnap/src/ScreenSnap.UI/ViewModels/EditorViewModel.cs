using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SkiaSharp;
using ScreenSnap.Core.Annotations;
using ScreenSnap.Core.Annotations.Commands;
using ScreenSnap.Core.Services;
using ScreenSnap.UI.Services;

namespace ScreenSnap.UI.ViewModels;

public partial class EditorViewModel : ObservableObject
{
    private readonly LayerManager _layerManager = new();
    private readonly CommandHistory _history = new();
    private readonly ConfigService _config;

    [ObservableProperty] private SKBitmap? _sourceBitmap;
    [ObservableProperty] private string _activeTool = "arrow";
    [ObservableProperty] private bool _canUndo;
    [ObservableProperty] private bool _canRedo;
    [ObservableProperty] private string _statusText = "Ready";

    public event Action? LayersChanged;

    public EditorViewModel(ConfigService config)
    {
        _config = config;
    }

    partial void OnActiveToolChanged(string value) => StatusText = "Ready";

    [RelayCommand]
    private void ActivateTool(string tool) => ActiveTool = tool;

    [RelayCommand]
    private void Copy()
    {
        if (_sourceBitmap is null) return;
        using var flat = ImageExporter.Flatten(_sourceBitmap, _layerManager);
        WpfClipboard.SetImage(flat);
        StatusText = "Copied to clipboard";
    }

    [RelayCommand]
    private void Save()
    {
        if (_sourceBitmap is null) return;
        try
        {
            using var flat = ImageExporter.Flatten(_sourceBitmap, _layerManager);
            var s = _config.Settings;
            var path = ImageExporter.BuildAutoSavePath(s.AutoSavePath, s.FileNamePattern);
            File.WriteAllBytes(path, ImageExporter.EncodePng(flat));
            StatusText = $"Saved: {Path.GetFileName(path)}";

            if (s.Behavior.CopyToClipboardAfterSave)
                WpfClipboard.SetImage(flat);
        }
        catch (Exception ex)
        {
            StatusText = $"Save failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void Undo()
    {
        _history.Undo();
        RefreshUndoRedo();
        LayersChanged?.Invoke();
    }

    [RelayCommand]
    private void Redo()
    {
        _history.Redo();
        RefreshUndoRedo();
        LayersChanged?.Invoke();
    }

    public void ExecuteCommand(IUndoableCommand cmd)
    {
        _history.Execute(cmd);
        RefreshUndoRedo();
    }

    public LayerManager LayerManager => _layerManager;

    private void RefreshUndoRedo()
    {
        CanUndo = _history.CanUndo;
        CanRedo = _history.CanRedo;
    }

}
