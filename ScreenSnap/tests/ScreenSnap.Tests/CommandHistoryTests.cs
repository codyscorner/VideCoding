using ScreenSnap.Core.Annotations.Commands;

namespace ScreenSnap.Tests;

public class CommandHistoryTests
{
    private sealed class CountingCommand : IUndoableCommand
    {
        public int ExecuteCount;
        public int UndoCount;
        public void Execute() => ExecuteCount++;
        public void Undo() => UndoCount++;
    }

    private sealed class LabeledCommand(string label, List<string> log) : IUndoableCommand
    {
        public void Execute() => log.Add($"{label}-exec");
        public void Undo() => log.Add($"{label}-undo");
    }

    [Fact]
    public void Execute_CallsCommandAndEnablesUndo()
    {
        var history = new CommandHistory();
        var cmd = new CountingCommand();
        history.Execute(cmd);
        Assert.Equal(1, cmd.ExecuteCount);
        Assert.True(history.CanUndo);
        Assert.False(history.CanRedo);
    }

    [Fact]
    public void Undo_CallsUndoAndEnablesRedo()
    {
        var history = new CommandHistory();
        var cmd = new CountingCommand();
        history.Execute(cmd);
        history.Undo();
        Assert.Equal(1, cmd.UndoCount);
        Assert.False(history.CanUndo);
        Assert.True(history.CanRedo);
    }

    [Fact]
    public void Redo_ReExecutesCommand()
    {
        var history = new CommandHistory();
        var cmd = new CountingCommand();
        history.Execute(cmd);
        history.Undo();
        history.Redo();
        Assert.Equal(2, cmd.ExecuteCount);
        Assert.True(history.CanUndo);
        Assert.False(history.CanRedo);
    }

    [Fact]
    public void Execute_AfterUndo_ClearsRedoStack()
    {
        var history = new CommandHistory();
        history.Execute(new CountingCommand());
        history.Undo();
        Assert.True(history.CanRedo);

        history.Execute(new CountingCommand());
        Assert.False(history.CanRedo);
    }

    [Fact]
    public void Undo_WhenEmpty_IsNoOp()
    {
        var history = new CommandHistory();
        history.Undo();
        Assert.False(history.CanUndo);
    }

    [Fact]
    public void Redo_WhenEmpty_IsNoOp()
    {
        var history = new CommandHistory();
        history.Redo();
        Assert.False(history.CanRedo);
    }

    [Fact]
    public void Clear_EmptiesBothStacks()
    {
        var history = new CommandHistory();
        history.Execute(new CountingCommand());
        history.Undo();
        history.Clear();
        Assert.False(history.CanUndo);
        Assert.False(history.CanRedo);
    }

    [Fact]
    public void MultipleUndo_RespectsFiloOrder()
    {
        var history = new CommandHistory();
        var log = new List<string>();
        history.Execute(new LabeledCommand("A", log));
        history.Execute(new LabeledCommand("B", log));
        history.Undo();
        history.Undo();
        Assert.Equal(["A-exec", "B-exec", "B-undo", "A-undo"], log);
    }

    [Fact]
    public void RedoAfterMultipleUndos_RestoresCorrectOrder()
    {
        var history = new CommandHistory();
        var log = new List<string>();
        history.Execute(new LabeledCommand("A", log));
        history.Execute(new LabeledCommand("B", log));
        history.Undo();
        history.Undo();
        history.Redo();
        history.Redo();
        Assert.Equal(["A-exec", "B-exec", "B-undo", "A-undo", "A-exec", "B-exec"], log);
    }
}
