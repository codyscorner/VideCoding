namespace ScreenSnap.Core.Win32;

public static class ScreenInfo
{
    public static double GetSystemDpiScale() => NativeMethods.GetDpiForSystem() / 96.0;

    public static IntPtr GetForegroundWindow() => NativeMethods.GetForegroundWindow();

    public static int MonitorCount()
    {
        int count = 0;
        NativeMethods.EnumDisplayMonitors(IntPtr.Zero, IntPtr.Zero,
            (_, _, ref _, _) => { count++; return true; }, IntPtr.Zero);
        return count;
    }
}
