namespace ScreenSnap.Core.Services;

// Hotkey registration requires a Win32 HWND; HotkeyService lives in Core
// for the interface but must be instantiated and owned by the UI project's
// WndProc host, which passes WM_HOTKEY messages back via OnHotkeyReceived.
public class HotkeyService : IDisposable
{
    private readonly Dictionary<int, Action> _callbacks = new();
    private int _nextId = 1;

    public int Register(Action callback)
    {
        var id = _nextId++;
        _callbacks[id] = callback;
        return id;
    }

    public void OnHotkeyReceived(int id)
    {
        if (_callbacks.TryGetValue(id, out var cb)) cb();
    }

    public void Unregister(int id) => _callbacks.Remove(id);

    public void Dispose() => _callbacks.Clear();
}
