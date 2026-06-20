using SkiaSharp;

namespace ScreenSnap.Core.Capture;

public interface ICaptureService
{
    // region is in physical (device) pixels — caller converts from WPF DIPs before calling
    Task<SKBitmap> CaptureRegionAsync(SKRectI region);
    Task<SKBitmap> CaptureWindowAsync(IntPtr hwnd);
    Task<SKBitmap> CaptureFullScreenAsync();
    Task<SKBitmap> CaptureMonitorAsync(int monitorIndex);
}
