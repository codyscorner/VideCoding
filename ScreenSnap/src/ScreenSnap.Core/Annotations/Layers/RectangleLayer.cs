using SkiaSharp;

namespace ScreenSnap.Core.Annotations.Layers;

public class RectangleLayer : IAnnotationLayer
{
    public Guid Id { get; } = Guid.NewGuid();
    public SKRect Rect { get; set; }
    public SKColor StrokeColor { get; set; } = SKColors.Red;
    public SKColor FillColor { get; set; } = SKColors.Transparent;
    public float Thickness { get; set; } = 2f;
    public float CornerRadius { get; set; } = 0f;

    public void Render(SKCanvas canvas)
    {
        if (FillColor != SKColors.Transparent)
        {
            using var fillPaint = new SKPaint { Color = FillColor, Style = SKPaintStyle.Fill, IsAntialias = true };
            canvas.DrawRoundRect(Rect, CornerRadius, CornerRadius, fillPaint);
        }

        using var strokePaint = new SKPaint
        {
            Color = StrokeColor,
            StrokeWidth = Thickness,
            Style = SKPaintStyle.Stroke,
            IsAntialias = true,
        };
        canvas.DrawRoundRect(Rect, CornerRadius, CornerRadius, strokePaint);
    }

    public bool HitTest(SKPoint point) => Rect.Contains(point);

    public void Transform(SKMatrix matrix)
    {
        var tl = matrix.MapPoint(new SKPoint(Rect.Left, Rect.Top));
        var br = matrix.MapPoint(new SKPoint(Rect.Right, Rect.Bottom));
        Rect = new SKRect(tl.X, tl.Y, br.X, br.Y);
    }
}
