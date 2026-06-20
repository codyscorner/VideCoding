using SkiaSharp;

namespace ScreenSnap.Core.Services;

// Actual clipboard interaction requires a UI thread and STA apartment;
// call from UI project after marshalling to the dispatcher.
public interface IClipboardService
{
    void CopyBitmap(SKBitmap bitmap);
}
