using ScreenSnap.Core.Annotations.Layers;

namespace ScreenSnap.Core.Annotations.Commands;

public class RemoveLayerCommand : IUndoableCommand
{
    private readonly LayerManager _manager;
    private readonly IAnnotationLayer _layer;

    public RemoveLayerCommand(LayerManager manager, IAnnotationLayer layer)
    {
        _manager = manager;
        _layer = layer;
    }

    public void Execute() => _manager.RemoveLayer(_layer);
    public void Undo() => _manager.AddLayer(_layer);
}
