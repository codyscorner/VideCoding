using System.Windows;
using System.Windows.Input;

namespace ScreenSnap.UI.Views;

public partial class TextInputDialog : Window
{
    public string? InputText { get; private set; }

    public TextInputDialog()
    {
        InitializeComponent();
        Loaded += (_, _) => InputBox.Focus();
    }

    private void OkButton_Click(object sender, RoutedEventArgs e) => Confirm();
    private void CancelButton_Click(object sender, RoutedEventArgs e) => DialogResult = false;

    private void InputBox_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter) Confirm();
        if (e.Key == Key.Escape) DialogResult = false;
    }

    private void InputBox_TextChanged(object sender, System.Windows.Controls.TextChangedEventArgs e)
        => OkButton.IsEnabled = !string.IsNullOrWhiteSpace(InputBox.Text);

    private void Confirm()
    {
        InputText = InputBox.Text;
        DialogResult = true;
    }
}
