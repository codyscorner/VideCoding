using SkiaSharp;

namespace ScreenSnap.Core.Annotations.Layers;

public class HighlightLayer : IAnnotationLayer
{
    public Guid Id { get; } = Guid.NewGuid();
    public SKRect Rect { get; set; }
    public SKColor Color { get; set; } = new SKColor(255, 255, 0, 120); // semi-transparent yellow

    public void Render(SKCanvas canvas)
    {
        using var paint = new SKPaint
        {
            Color = Color,
            Style = SKPaintStyle.Fill,
            IsAntialias = false,
        };
        canvas.DrawRect(Rect, paint);
    }

    public bool HitTest(SKPoint point) => Rect.Contains(point);

    public void Transform(SKMatrix matrix)
    {
        var tl = matrix.MapPoint(new SKPoint(Rect.Left, Rect.Top));
        var br = matrix.MapPoint(new SKPoint(Rect.Right, Rect.Bottom));
        Rect = new SKRect(tl.X, tl.Y, br.X, br.Y);
    }
}
