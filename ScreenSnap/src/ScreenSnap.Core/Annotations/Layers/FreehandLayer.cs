using SkiaSharp;

namespace ScreenSnap.Core.Annotations.Layers;

public class FreehandLayer : IAnnotationLayer
{
    public Guid Id { get; } = Guid.NewGuid();
    public List<SKPoint> Points { get; set; } = new();
    public SKColor Color { get; set; } = SKColors.Red;
    public float Thickness { get; set; } = 3f;

    public void Render(SKCanvas canvas)
    {
        if (Points.Count < 2) return;

        using var paint = new SKPaint
        {
            Color = Color,
            StrokeWidth = Thickness,
            Style = SKPaintStyle.Stroke,
            StrokeCap = SKStrokeCap.Round,
            StrokeJoin = SKStrokeJoin.Round,
            IsAntialias = true,
        };

        using var path = new SKPath();
        path.MoveTo(Points[0]);
        for (int i = 1; i < Points.Count; i++)
            path.LineTo(Points[i]);

        canvas.DrawPath(path, paint);
    }

    public bool HitTest(SKPoint point)
    {
        float threshold = (Thickness + 4f) * (Thickness + 4f);
        for (int i = 1; i < Points.Count; i++)
        {
            var a = Points[i - 1];
            var b = Points[i];
            var dx = b.X - a.X;
            var dy = b.Y - a.Y;
            var lenSq = dx * dx + dy * dy;
            if (lenSq < 0.001f)
            {
                var diffX = point.X - a.X;
                var diffY = point.Y - a.Y;
                if (diffX * diffX + diffY * diffY <= threshold) return true;
                continue;
            }
            var t = Math.Clamp(((point.X - a.X) * dx + (point.Y - a.Y) * dy) / lenSq, 0f, 1f);
            var nearX = a.X + t * dx;
            var nearY = a.Y + t * dy;
            var distX = point.X - nearX;
            var distY = point.Y - nearY;
            if (distX * distX + distY * distY <= threshold) return true;
        }
        return false;
    }

    public void Transform(SKMatrix matrix)
    {
        for (int i = 0; i < Points.Count; i++)
            Points[i] = matrix.MapPoint(Points[i]);
    }
}
