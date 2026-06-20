using System.Runtime.InteropServices;
using System.Windows.Interop;

namespace ScreenSnap.UI.Services;

/// <summary>
/// Owns a hidden Win32 window used solely to receive WM_HOTKEY messages.
/// Must be created and used on the UI thread.
/// </summary>
public sealed class HotkeyWindow : IDisposable
{
    // P/Invoke — local to this class so Core's NativeMethods can stay internal
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    private const int WM_HOTKEY      = 0x0312;
    public  const uint MOD_NOREPEAT  = 0x4000;

    private HwndSource? _source;
    private readonly Dictionary<int, Action> _registrations = new();
    private int _nextId = 0xC000;   // IDs above 0xBFFF are user-defined

    public void Initialize()
    {
        var p = new HwndSourceParameters("ScreenSnap_HotkeyHost")
        {
            Width = 0,
            Height = 0,
            WindowStyle = unchecked((int)0x80000000),   // WS_POPUP
            ExtendedWindowStyle = 0x00000080,           // WS_EX_TOOLWINDOW — hidden from Alt+Tab
        };
        _source = new HwndSource(p);
        _source.AddHook(WndProcHook);
    }

    /// <summary>
    /// Register a hotkey. Returns the assigned ID, or -1 if already claimed by another app.
    /// </summary>
    public int Register(uint modifiers, uint vk, Action callback)
    {
        if (_source is null) throw new InvalidOperationException("Call Initialize() first.");
        if (vk == 0) return -1;

        int id = _nextId++;
        if (!RegisterHotKey(_source.Handle, id, modifiers | MOD_NOREPEAT, vk))
            return -1;

        _registrations[id] = callback;
        return id;
    }

    public void Unregister(int id)
    {
        if (id < 0 || _source is null) return;
        UnregisterHotKey(_source.Handle, id);
        _registrations.Remove(id);
    }

    private IntPtr WndProcHook(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == WM_HOTKEY && _registrations.TryGetValue(wParam.ToInt32(), out var cb))
        {
            cb();
            handled = true;
        }
        return IntPtr.Zero;
    }

    public void Dispose()
    {
        if (_source is not null)
            foreach (var id in _registrations.Keys.ToList())
                UnregisterHotKey(_source.Handle, id);

        _registrations.Clear();
        _source?.Dispose();
        _source = null;
    }
}
