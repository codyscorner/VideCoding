using SkiaSharp;

namespace ScreenSnap.Core.Annotations.Layers;

public interface IAnnotationLayer
{
    Guid Id { get; }
    void Render(SKCanvas canvas);
    bool HitTest(SKPoint point);
    void Transform(SKMatrix matrix);
}
