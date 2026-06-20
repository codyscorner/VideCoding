using SkiaSharp;
using ScreenSnap.Core.Annotations;

namespace ScreenSnap.Core.Services;

public static class ImageExporter
{
    /// <summary>
    /// Renders all annotation layers on top of source into a new flattened bitmap.
    /// Caller owns the returned SKBitmap and must dispose it.
    /// </summary>
    public static SKBitmap Flatten(SKBitmap source, LayerManager layers)
    {
        var result = source.Copy();
        using var canvas = new SKCanvas(result);
        layers.RenderAll(canvas);
        canvas.Flush();
        return result;
    }

    public static byte[] EncodePng(SKBitmap bitmap)
    {
        using var image = SKImage.FromBitmap(bitmap);
        using var data = image.Encode(SKEncodedImageFormat.Png, 100);
        return data.ToArray();
    }

    /// <summary>
    /// Expands the directory template, ensures it exists, and builds a unique file path.
    /// Supports {date} and {time} tokens in the pattern.
    /// </summary>
    public static string BuildAutoSavePath(string dirTemplate, string pattern)
    {
        var dir = Environment.ExpandEnvironmentVariables(dirTemplate);
        Directory.CreateDirectory(dir);
        var now = DateTime.Now;
        var name = pattern
            .Replace("{date}", now.ToString("yyyy-MM-dd"))
            .Replace("{time}", now.ToString("HH-mm-ss"));
        return Path.Combine(dir, name + ".png");
    }
}
