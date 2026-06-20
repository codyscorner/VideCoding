using ScreenSnap.Core.Services;

namespace ScreenSnap.Tests;

public class HotkeyParserTests
{
    // MOD_CONTROL=0x0002, MOD_SHIFT=0x0004, MOD_ALT=0x0001
    [Theory]
    [InlineData("Ctrl+Shift+4", 0x0006u, 0x34u)]   // default region hotkey
    [InlineData("Ctrl+Shift+3", 0x0006u, 0x33u)]   // default fullscreen hotkey
    [InlineData("Ctrl+Shift+5", 0x0006u, 0x35u)]   // default window hotkey
    [InlineData("Ctrl+Z",       0x0002u, 0x5Au)]   // undo
    [InlineData("Alt+F4",       0x0001u, 0x73u)]   // VK_F4 = 0x6F+4
    [InlineData("Ctrl+Shift+Alt+F12", 0x0007u, 0x7Bu)] // VK_F12 = 0x6F+12
    public void Parse_ReturnsExpectedModsAndVk(string hotkey, uint expectedMods, uint expectedVk)
    {
        var (mods, vk) = HotkeyParser.Parse(hotkey);
        Assert.Equal(expectedMods, mods);
        Assert.Equal(expectedVk, vk);
    }

    [Fact]
    public void Parse_IsCaseInsensitive()
    {
        var (mods1, vk1) = HotkeyParser.Parse("Ctrl+Shift+A");
        var (mods2, vk2) = HotkeyParser.Parse("ctrl+shift+a");
        Assert.Equal(mods1, mods2);
        Assert.Equal(vk1, vk2);
    }

    [Fact]
    public void Parse_UnknownKey_ReturnsZeroVk()
    {
        var (_, vk) = HotkeyParser.Parse("Ctrl+Unknown");
        Assert.Equal(0u, vk);
    }

    [Theory]
    [InlineData("F1",  0x70u)]
    [InlineData("F6",  0x75u)]
    [InlineData("F12", 0x7Bu)]
    public void Parse_FunctionKeys_ReturnCorrectVk(string key, uint expectedVk)
    {
        var (_, vk) = HotkeyParser.Parse(key);
        Assert.Equal(expectedVk, vk);
    }

    [Theory]
    [InlineData("A", (uint)'A')]
    [InlineData("Z", (uint)'Z')]
    [InlineData("0", (uint)'0')]
    [InlineData("9", (uint)'9')]
    public void Parse_SingleChar_ReturnsAsciiVk(string key, uint expectedVk)
    {
        var (_, vk) = HotkeyParser.Parse(key);
        Assert.Equal(expectedVk, vk);
    }

    [Fact]
    public void Parse_WinModifier_SetsModWin()
    {
        var (mods, _) = HotkeyParser.Parse("Win+D");
        Assert.Equal(HotkeyParser.MOD_WIN, mods);
    }

    [Fact]
    public void Parse_ControlAlias_SameAsCtrl()
    {
        var (mods1, _) = HotkeyParser.Parse("Ctrl+A");
        var (mods2, _) = HotkeyParser.Parse("Control+A");
        Assert.Equal(mods1, mods2);
    }
}
