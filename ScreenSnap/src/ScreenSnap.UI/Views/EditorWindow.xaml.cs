using System.Windows;
using System.Windows.Input;
using SkiaSharp;
using ScreenSnap.UI.ViewModels;

namespace ScreenSnap.UI.Views;

public partial class EditorWindow : Window
{
    private EditorViewModel? _vm;

    public EditorWindow(EditorViewModel viewModel)
    {
        InitializeComponent();
        DataContext = viewModel;
        _vm = viewModel;

        Loaded += (_, _) =>
        {
            if (viewModel.SourceBitmap is SKBitmap bmp)
                Canvas.SetSource(bmp, viewModel);
        };

        viewModel.PropertyChanged += (_, e) =>
        {
            if (e.PropertyName == nameof(EditorViewModel.SourceBitmap) && viewModel.SourceBitmap is SKBitmap bmp)
                Canvas.SetSource(bmp, viewModel);
        };

        KeyDown += OnEditorKeyDown;
    }

    // Single-key tool shortcuts (Flameshot style): A=arrow R=rect T=text B=bubble
    // Ctrl combos are handled by the toolbar bindings.
    private void OnEditorKeyDown(object sender, KeyEventArgs e)
    {
        if (_vm is null || Keyboard.Modifiers != ModifierKeys.None) return;
        switch (e.Key)
        {
            case Key.A: _vm.ActiveTool = "arrow";  break;
            case Key.R: _vm.ActiveTool = "rect";   break;
            case Key.T: _vm.ActiveTool = "text";   break;
            case Key.B: _vm.ActiveTool = "bubble"; break;
            case Key.Z: if (_vm.CanUndo) _vm.UndoCommand.Execute(null); break;
            case Key.Y: if (_vm.CanRedo) _vm.RedoCommand.Execute(null); break;
        }
    }
}
