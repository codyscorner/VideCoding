namespace ScreenSnap.Plugins;

public interface IPlugin
{
    string Name { get; }
    string Version { get; }
    void Initialize();
    void Shutdown();
}
