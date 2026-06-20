using System.Windows;
using System.Windows.Controls;

namespace ScreenSnap.UI.Controls;

public partial class ToolPalette : UserControl
{
    public static readonly DependencyProperty SelectedToolProperty =
        DependencyProperty.Register(nameof(SelectedTool), typeof(string), typeof(ToolPalette),
            new FrameworkPropertyMetadata("arrow", FrameworkPropertyMetadataOptions.BindsTwoWayByDefault));

    public string SelectedTool
    {
        get => (string)GetValue(SelectedToolProperty);
        set => SetValue(SelectedToolProperty, value);
    }

    public ToolPalette() => InitializeComponent();

    private void Tool_Checked(object sender, RoutedEventArgs e)
    {
        if (sender is RadioButton rb && rb.Tag is string tag)
            SelectedTool = tag;
    }
}
