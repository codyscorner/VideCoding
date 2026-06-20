using SkiaSharp;

namespace ScreenSnap.Core.Annotations.Layers;

public enum BubbleStyle { Speech, Thought }

public class BubbleLayer : IAnnotationLayer
{
    public Guid Id { get; } = Guid.NewGuid();
    public SKRect BubbleRect { get; set; }
    public SKPoint TailPoint { get; set; }
    public string Text { get; set; } = string.Empty;
    public BubbleStyle Style { get; set; } = BubbleStyle.Speech;
    public SKColor FillColor { get; set; } = SKColors.White;
    public SKColor StrokeColor { get; set; } = SKColors.Black;
    public SKColor TextColor { get; set; } = SKColors.Black;
    public float StrokeWidth { get; set; } = 2f;
    public float FontSize { get; set; } = 14f;
    public float CornerRadius { get; set; } = 10f;

    public void Render(SKCanvas canvas)
    {
        using var fillPaint = new SKPaint { Color = FillColor, Style = SKPaintStyle.Fill, IsAntialias = true };
        using var strokePaint = new SKPaint { Color = StrokeColor, StrokeWidth = StrokeWidth, Style = SKPaintStyle.Stroke, IsAntialias = true };

        if (Style == BubbleStyle.Speech)
            RenderSpeech(canvas, fillPaint, strokePaint);
        else
            RenderThought(canvas, fillPaint, strokePaint);

        using var font = new SKFont { Size = FontSize };
        using var textPaint = new SKPaint { Color = TextColor, IsAntialias = true };
        canvas.DrawText(Text, BubbleRect.MidX, BubbleRect.MidY + FontSize * 0.35f, SKTextAlign.Center, font, textPaint);
    }

    private void RenderSpeech(SKCanvas canvas, SKPaint fill, SKPaint stroke)
    {
        using var path = new SKPath();
        path.AddRoundRect(BubbleRect, CornerRadius, CornerRadius);

        var anchor1 = new SKPoint(BubbleRect.MidX - 8, BubbleRect.Bottom);
        var anchor2 = new SKPoint(BubbleRect.MidX + 8, BubbleRect.Bottom);
        path.MoveTo(anchor1);
        path.LineTo(TailPoint);
        path.LineTo(anchor2);
        path.Close();

        canvas.DrawPath(path, fill);
        canvas.DrawPath(path, stroke);
    }

    private void RenderThought(SKCanvas canvas, SKPaint fill, SKPaint stroke)
    {
        canvas.DrawRoundRect(BubbleRect, CornerRadius, CornerRadius, fill);
        canvas.DrawRoundRect(BubbleRect, CornerRadius, CornerRadius, stroke);

        var steps = 3;
        var startX = BubbleRect.MidX;
        var startY = BubbleRect.Bottom;
        for (int i = 1; i <= steps; i++)
        {
            float t = (float)i / (steps + 1);
            var cx = startX + (TailPoint.X - startX) * t;
            var cy = startY + (TailPoint.Y - startY) * t;
            var r = 5f - i;
            canvas.DrawCircle(cx, cy, r, fill);
            canvas.DrawCircle(cx, cy, r, stroke);
        }
    }

    public bool HitTest(SKPoint point) => BubbleRect.Contains(point);

    public void Transform(SKMatrix matrix)
    {
        var tl = matrix.MapPoint(new SKPoint(BubbleRect.Left, BubbleRect.Top));
        var br = matrix.MapPoint(new SKPoint(BubbleRect.Right, BubbleRect.Bottom));
        BubbleRect = new SKRect(tl.X, tl.Y, br.X, br.Y);
        TailPoint = matrix.MapPoint(TailPoint);
    }
}
