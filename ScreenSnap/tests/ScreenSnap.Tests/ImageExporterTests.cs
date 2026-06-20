using SkiaSharp;
using ScreenSnap.Core.Annotations;
using ScreenSnap.Core.Services;

namespace ScreenSnap.Tests;

public class ImageExporterTests
{
    [Fact]
    public void Flatten_ReturnsCorrectDimensions()
    {
        using var source = new SKBitmap(100, 80, SKColorType.Bgra8888, SKAlphaType.Opaque);
        source.Erase(SKColors.White);
        var layers = new LayerManager();

        using var flat = ImageExporter.Flatten(source, layers);

        Assert.Equal(100, flat.Width);
        Assert.Equal(80, flat.Height);
    }

    [Fact]
    public void Flatten_DoesNotMutateSource()
    {
        using var source = new SKBitmap(50, 50, SKColorType.Bgra8888, SKAlphaType.Opaque);
        source.Erase(SKColors.Red);
        var layers = new LayerManager();

        using var _ = ImageExporter.Flatten(source, layers);

        Assert.Equal(SKColors.Red, source.GetPixel(10, 10));
    }

    [Fact]
    public void Flatten_ReturnsDistinctObject()
    {
        using var source = new SKBitmap(20, 20, SKColorType.Bgra8888, SKAlphaType.Opaque);
        source.Erase(SKColors.Green);
        var layers = new LayerManager();

        using var flat = ImageExporter.Flatten(source, layers);

        Assert.NotSame(source, flat);
    }

    [Fact]
    public void EncodePng_ReturnsPngMagicBytes()
    {
        using var bmp = new SKBitmap(10, 10, SKColorType.Bgra8888, SKAlphaType.Opaque);
        bmp.Erase(SKColors.Blue);

        var bytes = ImageExporter.EncodePng(bmp);

        Assert.True(bytes.Length > 0);
        // PNG magic: 0x89 'P' 'N' 'G'
        Assert.Equal(0x89, bytes[0]);
        Assert.Equal(0x50, bytes[1]);
        Assert.Equal(0x4E, bytes[2]);
        Assert.Equal(0x47, bytes[3]);
    }

    [Fact]
    public void BuildAutoSavePath_CreatesDirectory()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), $"SSTest_{Guid.NewGuid():N}");
        try
        {
            var path = ImageExporter.BuildAutoSavePath(tempDir, "Screenshot_{date}_{time}");
            Assert.True(Directory.Exists(tempDir));
        }
        finally
        {
            if (Directory.Exists(tempDir)) Directory.Delete(tempDir, recursive: true);
        }
    }

    [Fact]
    public void BuildAutoSavePath_ReturnsFullPathWithPngExtension()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), $"SSTest_{Guid.NewGuid():N}");
        try
        {
            var path = ImageExporter.BuildAutoSavePath(tempDir, "Screenshot_{date}_{time}");
            Assert.EndsWith(".png", path, StringComparison.OrdinalIgnoreCase);
            Assert.StartsWith(tempDir, path, StringComparison.OrdinalIgnoreCase);
        }
        finally
        {
            if (Directory.Exists(tempDir)) Directory.Delete(tempDir, recursive: true);
        }
    }

    [Fact]
    public void BuildAutoSavePath_SubstitutesDateAndTimeTokens()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), $"SSTest_{Guid.NewGuid():N}");
        try
        {
            var before = DateTime.Now;
            var path = ImageExporter.BuildAutoSavePath(tempDir, "Screenshot_{date}_{time}");
            var fileName = Path.GetFileNameWithoutExtension(path);

            // Date portion: "Screenshot_YYYY-MM-DD_HH-mm-ss"
            Assert.Matches(@"^Screenshot_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$", fileName);
        }
        finally
        {
            if (Directory.Exists(tempDir)) Directory.Delete(tempDir, recursive: true);
        }
    }

    [Fact]
    public void BuildAutoSavePath_ExpandsEnvironmentVariables()
    {
        var tempPath = Path.GetTempPath().TrimEnd('\\', '/');
        var template = "%TEMP%\\SSTest_" + Guid.NewGuid().ToString("N");
        var expected = Environment.ExpandEnvironmentVariables(template);
        try
        {
            var path = ImageExporter.BuildAutoSavePath(template, "file_{date}_{time}");
            Assert.StartsWith(expected, path, StringComparison.OrdinalIgnoreCase);
        }
        finally
        {
            if (Directory.Exists(expected)) Directory.Delete(expected, recursive: true);
        }
    }
}
