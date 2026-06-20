using SkiaSharp;

namespace ScreenSnap.Core.Annotations.Layers;

public class TextLayer : IAnnotationLayer
{
    public Guid Id { get; } = Guid.NewGuid();
    public string Text { get; set; } = string.Empty;
    public SKPoint Position { get; set; }
    public SKColor TextColor { get; set; } = SKColors.Black;
    public SKColor BackgroundColor { get; set; } = SKColors.Transparent;
    public float FontSize { get; set; } = 14f;
    public string FontFamily { get; set; } = "Segoe UI";

    public void Render(SKCanvas canvas)
    {
        using var typeface = SKTypeface.FromFamilyName(FontFamily);
        using var font = new SKFont(typeface, FontSize);
        using var paint = new SKPaint { Color = TextColor, IsAntialias = true };

        if (BackgroundColor != SKColors.Transparent)
        {
            font.MeasureText(Text, out var bounds);
            var bgRect = SKRect.Create(Position.X + bounds.Left - 2, Position.Y + bounds.Top - 2,
                                      bounds.Width + 4, bounds.Height + 4);
            using var bgPaint = new SKPaint { Color = BackgroundColor, Style = SKPaintStyle.Fill };
            canvas.DrawRect(bgRect, bgPaint);
        }

        canvas.DrawText(Text, Position, SKTextAlign.Left, font, paint);
    }

    public bool HitTest(SKPoint point)
    {
        using var typeface = SKTypeface.FromFamilyName(FontFamily);
        using var font = new SKFont(typeface, FontSize);
        font.MeasureText(Text, out var bounds);
        var hitRect = SKRect.Create(Position.X + bounds.Left - 4, Position.Y + bounds.Top - 4,
                                    bounds.Width + 8, bounds.Height + 8);
        return hitRect.Contains(point);
    }

    public void Transform(SKMatrix matrix) => Position = matrix.MapPoint(Position);
}
