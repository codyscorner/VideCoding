using SkiaSharp;

namespace ScreenSnap.Core.Annotations.Layers;

public class ArrowLayer : IAnnotationLayer
{
    public Guid Id { get; } = Guid.NewGuid();
    public SKPoint Start { get; set; }
    public SKPoint End { get; set; }
    public SKColor Color { get; set; } = SKColors.Red;
    public float Thickness { get; set; } = 3f;

    public void Render(SKCanvas canvas)
    {
        using var paint = new SKPaint
        {
            Color = Color,
            StrokeWidth = Thickness,
            IsAntialias = true,
            Style = SKPaintStyle.Stroke,
        };

        canvas.DrawLine(Start, End, paint);

        // Draw arrowhead
        var dir = End - Start;
        var len = MathF.Sqrt(dir.X * dir.X + dir.Y * dir.Y);
        if (len < 0.001f) return;
        var unit = new SKPoint(dir.X / len, dir.Y / len);
        var arrowLen = Math.Max(Thickness * 4, 12f);
        var arrowWidth = arrowLen * 0.5f;
        var perp = new SKPoint(-unit.Y, unit.X);

        var tip = End;
        var base1 = new SKPoint(tip.X - unit.X * arrowLen + perp.X * arrowWidth,
                                tip.Y - unit.Y * arrowLen + perp.Y * arrowWidth);
        var base2 = new SKPoint(tip.X - unit.X * arrowLen - perp.X * arrowWidth,
                                tip.Y - unit.Y * arrowLen - perp.Y * arrowWidth);

        using var path = new SKPath();
        path.MoveTo(tip);
        path.LineTo(base1);
        path.LineTo(base2);
        path.Close();

        using var fillPaint = new SKPaint { Color = Color, IsAntialias = true, Style = SKPaintStyle.Fill };
        canvas.DrawPath(path, fillPaint);
    }

    public bool HitTest(SKPoint point)
    {
        // Distance from point to line segment
        var dx = End.X - Start.X;
        var dy = End.Y - Start.Y;
        var lenSq = dx * dx + dy * dy;
        if (lenSq < 0.001f) return false;
        var t = Math.Clamp(((point.X - Start.X) * dx + (point.Y - Start.Y) * dy) / lenSq, 0f, 1f);
        var nearX = Start.X + t * dx;
        var nearY = Start.Y + t * dy;
        var distSq = (point.X - nearX) * (point.X - nearX) + (point.Y - nearY) * (point.Y - nearY);
        return distSq <= (Thickness + 4) * (Thickness + 4);
    }

    public void Transform(SKMatrix matrix)
    {
        Start = matrix.MapPoint(Start);
        End = matrix.MapPoint(End);
    }
}
