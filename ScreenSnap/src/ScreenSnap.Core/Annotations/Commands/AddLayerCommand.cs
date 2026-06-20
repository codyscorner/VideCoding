using ScreenSnap.Core.Annotations.Layers;

namespace ScreenSnap.Core.Annotations.Commands;

public class AddLayerCommand : IUndoableCommand
{
    private readonly LayerManager _manager;
    private readonly IAnnotationLayer _layer;

    public AddLayerCommand(LayerManager manager, IAnnotationLayer layer)
    {
        _manager = manager;
        _layer = layer;
    }

    public void Execute() => _manager.AddLayer(_layer);
    public void Undo() => _manager.RemoveLayer(_layer);
}
