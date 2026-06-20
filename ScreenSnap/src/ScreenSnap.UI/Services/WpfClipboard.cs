using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using SkiaSharp;

namespace ScreenSnap.UI.Services;

public static class WpfClipboard
{
    // SKBitmap (Bgra8888) maps directly to WPF Bgra32 — no pixel conversion needed.
    public static void SetImage(SKBitmap bmp)
    {
        var wb = new WriteableBitmap(bmp.Width, bmp.Height, 96, 96, PixelFormats.Bgra32, null);
        wb.Lock();
        var bytes = bmp.Bytes;
        Marshal.Copy(bytes, 0, wb.BackBuffer, bytes.Length);
        wb.AddDirtyRect(new Int32Rect(0, 0, bmp.Width, bmp.Height));
        wb.Unlock();
        wb.Freeze();
        Clipboard.SetImage(wb);
    }
}
