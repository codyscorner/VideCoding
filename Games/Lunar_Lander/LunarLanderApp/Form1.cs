using Microsoft.Web.WebView2.Core;
using System.Reflection;

namespace LunarLanderApp;

public class MainForm : Form
{
    private Microsoft.Web.WebView2.WinForms.WebView2 _webView;

    public MainForm()
    {
        Text = "LUNAR LANDER — ARCADE 1979";
        Width = 1280;
        Height = 800;
        MinimumSize = new Size(640, 480);
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
            Path.Combine(Path.GetTempPath(), "LunarLanderWebView2"));
        await _webView.EnsureCoreWebView2Async(env);

        _webView.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
        _webView.CoreWebView2.Settings.AreDevToolsEnabled = false;
        _webView.CoreWebView2.Settings.IsStatusBarEnabled = false;

        var html = LoadEmbeddedHtml();
        _webView.NavigateToString(html);
    }

    private static string LoadEmbeddedHtml()
    {
        var asm = Assembly.GetExecutingAssembly();
        using var stream = asm.GetManifestResourceStream("LunarLander.html")
            ?? throw new InvalidOperationException("Embedded HTML not found.");
        using var reader = new StreamReader(stream);
        return reader.ReadToEnd();
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        _webView.Dispose();
        base.OnFormClosing(e);
    }
}
