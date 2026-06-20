using Microsoft.Web.WebView2.Core;
using System.Reflection;

namespace AsteroidsApp;

public class MainForm : Form
{
    private Microsoft.Web.WebView2.WinForms.WebView2 _webView;

    public MainForm()
    {
        Text = "ASTEROIDS";
        Width = 1280;
        Height = 720;
        MinimumSize = new Size(1280, 720);
        BackColor = Color.Black;
        StartPosition = FormStartPosition.CenterScreen;

        _webView = new Microsoft.Web.WebView2.WinForms.WebView2
        {
            Dock = DockStyle.Fill
        };
        Controls.Add(_webView);
    }

    protected override async void OnLoad(EventArgs e)
    {
        base.OnLoad(e);

        var env = await CoreWebView2Environment.CreateAsync(null,
            Path.Combine(Path.GetTempPath(), "AsteroidsWebView2"));
        await _webView.EnsureCoreWebView2Async(env);

        _webView.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
        _webView.CoreWebView2.Settings.AreDevToolsEnabled = false;
        _webView.CoreWebView2.Settings.IsStatusBarEnabled = false;

        var asm = Assembly.GetExecutingAssembly();
        using var stream = asm.GetManifestResourceStream("Asteroids.html")
            ?? throw new InvalidOperationException("Embedded HTML not found.");
        using var reader = new StreamReader(stream);
        var html = reader.ReadToEnd();

        var tempPath = Path.Combine(Path.GetTempPath(), "asteroids_game.html");
        File.WriteAllText(tempPath, html);
        _webView.CoreWebView2.Navigate("file:///" + tempPath.Replace("\\", "/"));
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        _webView.Dispose();
        base.OnFormClosing(e);
    }
}
