using SkiaSharp;

namespace ScreenSnap.Core.Annotations.Layers;

public class EllipseLayer : IAnnotationLayer
{
    public Guid Id { get; } = Guid.NewGuid();
    public SKRect Rect { get; set; }
    public SKColor StrokeColor { get; set; } = SKColors.Red;
    public SKColor FillColor { get; set; } = SKColors.Transparent;
    public float Thickness { get; set; } = 2f;

    public void Render(SKCanvas canvas)
    {
        if (FillColor != SKColors.Transparent)
        {
            using var fillPaint = new SKPaint { Color = FillColor, Style = SKPaintStyle.Fill, IsAntialias = true };
            canvas.DrawOval(Rect, fillPaint);
        }

        using var strokePaint = new SKPaint
        {
            Color = StrokeColor,
            StrokeWidth = Thickness,
            Style = SKPaintStyle.Stroke,
            IsAntialias = true,
        };
        canvas.DrawOval(Rect, strokePaint);
    }

    public bool HitTest(SKPoint point)
    {
        if (Rect.Width < 0.001f || Rect.Height < 0.001f) return false;
        float cx = Rect.MidX, cy = Rect.MidY;
        float rx = Rect.Width / 2f, ry = Rect.Height / 2f;
        float dx = (point.X - cx) / rx;
        float dy = (point.Y - cy) / ry;
        return dx * dx + dy * dy <= 1f;
    }

    public void Transform(SKMatrix matrix)
    {
        var tl = matrix.MapPoint(new SKPoint(Rect.Left, Rect.Top));
        var br = matrix.MapPoint(new SKPoint(Rect.Right, Rect.Bottom));
        Rect = new SKRect(tl.X, tl.Y, br.X, br.Y);
    }
}
