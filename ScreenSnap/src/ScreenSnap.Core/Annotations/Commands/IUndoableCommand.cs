namespace ScreenSnap.Core.Annotations.Commands;

public interface IUndoableCommand
{
    void Execute();
    void Undo();
}
