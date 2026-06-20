using System.Runtime.InteropServices;
using SkiaSharp;
using ScreenSnap.Core.Win32;

namespace ScreenSnap.Core.Capture;

public class GdiCaptureService : ICaptureService
{
    public Task<SKBitmap> CaptureRegionAsync(SKRectI region)
    {
        if (region.Width <= 0 || region.Height <= 0)
            throw new ArgumentException("Region must have positive dimensions.", nameof(region));

        return Task.FromResult(CaptureRect(region.Left, region.Top, region.Width, region.Height));
    }

    public Task<SKBitmap> CaptureFullScreenAsync()
    {
        int x = NativeMethods.GetSystemMetrics(NativeMethods.SM_XVIRTUALSCREEN);
        int y = NativeMethods.GetSystemMetrics(NativeMethods.SM_YVIRTUALSCREEN);
        int w = NativeMethods.GetSystemMetrics(NativeMethods.SM_CXVIRTUALSCREEN);
        int h = NativeMethods.GetSystemMetrics(NativeMethods.SM_CYVIRTUALSCREEN);
        return Task.FromResult(CaptureRect(x, y, w, h));
    }

    public Task<SKBitmap> CaptureMonitorAsync(int monitorIndex)
    {
        var monitors = EnumerateMonitorRects();
        if (monitorIndex < 0 || monitorIndex >= monitors.Count)
            throw new ArgumentOutOfRangeException(nameof(monitorIndex));

        var r = monitors[monitorIndex];
        return Task.FromResult(CaptureRect(r.Left, r.Top, r.Width, r.Height));
    }

    public Task<SKBitmap> CaptureWindowAsync(IntPtr hwnd)
    {
        if (!NativeMethods.GetWindowRect(hwnd, out var rect))
            throw new InvalidOperationException("GetWindowRect failed.");

        int w = rect.Width;
        int h = rect.Height;

        var screenDC = NativeMethods.GetDC(IntPtr.Zero);
        var memDC = NativeMethods.CreateCompatibleDC(screenDC);
        var hBitmap = NativeMethods.CreateCompatibleBitmap(screenDC, w, h);
        var oldObj = NativeMethods.SelectObject(memDC, hBitmap);

        // PW_RENDERFULLCONTENT captures hardware-accelerated content (DX, DComp)
        NativeMethods.PrintWindow(hwnd, memDC, NativeMethods.PW_RENDERFULLCONTENT);

        var bitmap = ExtractBitmap(screenDC, memDC, hBitmap, w, h);

        NativeMethods.SelectObject(memDC, oldObj);
        NativeMethods.DeleteObject(hBitmap);
        NativeMethods.DeleteDC(memDC);
        NativeMethods.ReleaseDC(IntPtr.Zero, screenDC);

        return Task.FromResult(bitmap);
    }

    // ------------------------------------------------------------------
    // Internal helpers
    // ------------------------------------------------------------------

    private static SKBitmap CaptureRect(int x, int y, int width, int height)
    {
        var screenDC = NativeMethods.GetDC(IntPtr.Zero);
        var memDC = NativeMethods.CreateCompatibleDC(screenDC);
        var hBitmap = NativeMethods.CreateCompatibleBitmap(screenDC, width, height);
        var oldObj = NativeMethods.SelectObject(memDC, hBitmap);

        NativeMethods.BitBlt(memDC, 0, 0, width, height, screenDC, x, y, NativeMethods.SRCCOPY);

        var bitmap = ExtractBitmap(screenDC, memDC, hBitmap, width, height);

        NativeMethods.SelectObject(memDC, oldObj);
        NativeMethods.DeleteObject(hBitmap);
        NativeMethods.DeleteDC(memDC);
        NativeMethods.ReleaseDC(IntPtr.Zero, screenDC);

        return bitmap;
    }

    private static SKBitmap ExtractBitmap(IntPtr screenDC, IntPtr memDC, IntPtr hBitmap, int width, int height)
    {
        var bmi = new NativeMethods.BITMAPINFO
        {
            bmiHeader = new NativeMethods.BITMAPINFOHEADER
            {
                biSize = (uint)Marshal.SizeOf<NativeMethods.BITMAPINFOHEADER>(),
                biWidth = width,
                biHeight = -height,   // negative → top-down row order
                biPlanes = 1,
                biBitCount = 32,
                biCompression = NativeMethods.BI_RGB,
            }
        };

        var bytes = new byte[width * height * 4];
        NativeMethods.GetDIBits(memDC, hBitmap, 0, (uint)height, bytes, ref bmi, NativeMethods.DIB_RGB_COLORS);

        // GDI delivers BGRA; SKia Bgra8888 matches that layout exactly
        var skBitmap = new SKBitmap(width, height, SKColorType.Bgra8888, SKAlphaType.Opaque);
        var pixels = skBitmap.GetPixels(out _);
        Marshal.Copy(bytes, 0, pixels, bytes.Length);
        return skBitmap;
    }

    private static List<NativeMethods.RECT> EnumerateMonitorRects()
    {
        var list = new List<NativeMethods.RECT>();
        NativeMethods.EnumDisplayMonitors(IntPtr.Zero, IntPtr.Zero,
            (hMon, _, ref _, _) =>
            {
                var info = new NativeMethods.MONITORINFO
                {
                    cbSize = (uint)Marshal.SizeOf<NativeMethods.MONITORINFO>()
                };
                if (NativeMethods.GetMonitorInfo(hMon, ref info))
                    list.Add(info.rcMonitor);
                return true;
            },
            IntPtr.Zero);
        return list;
    }
}
