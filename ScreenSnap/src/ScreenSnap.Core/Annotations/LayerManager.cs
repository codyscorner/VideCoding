using SkiaSharp;
using ScreenSnap.Core.Annotations.Layers;
using ScreenSnap.Core.Annotations.Commands;

namespace ScreenSnap.Core.Annotations;

public class LayerManager
{
    private readonly List<IAnnotationLayer> _layers = new();

    public IReadOnlyList<IAnnotationLayer> Layers => _layers;

    public void AddLayer(IAnnotationLayer layer) => _layers.Add(layer);

    public void RemoveLayer(IAnnotationLayer layer) => _layers.Remove(layer);

    public void MoveLayerUp(IAnnotationLayer layer)
    {
        var i = _layers.IndexOf(layer);
        if (i >= 0 && i < _layers.Count - 1)
            (_layers[i], _layers[i + 1]) = (_layers[i + 1], _layers[i]);
    }

    public void MoveLayerDown(IAnnotationLayer layer)
    {
        var i = _layers.IndexOf(layer);
        if (i > 0)
            (_layers[i], _layers[i - 1]) = (_layers[i - 1], _layers[i]);
    }

    public IAnnotationLayer? HitTest(SKPoint point)
    {
        for (int i = _layers.Count - 1; i >= 0; i--)
            if (_layers[i].HitTest(point)) return _layers[i];
        return null;
    }

    public void RenderAll(SKCanvas canvas)
    {
        foreach (var layer in _layers)
            layer.Render(canvas);
    }

    public void Clear() => _layers.Clear();
}
