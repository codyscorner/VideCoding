namespace ScreenSnap.Core.Services;

/// <summary>
/// Converts a human-readable hotkey string like "Ctrl+Shift+4" into
/// the Win32 modifier flags and virtual-key code needed for RegisterHotKey.
/// Supports: Ctrl/Control, Shift, Alt, Win, letters A-Z, digits 0-9, F1-F12.
/// </summary>
public static class HotkeyParser
{
    // Win32 modifier flags — kept here so Core doesn't leak internal NativeMethods to callers
    public const uint MOD_ALT     = 0x0001;
    public const uint MOD_CONTROL = 0x0002;
    public const uint MOD_SHIFT   = 0x0004;
    public const uint MOD_WIN     = 0x0008;

    public static (uint Modifiers, uint Vk) Parse(string hotkeyString)
    {
        uint mods = 0;
        uint vk = 0;

        foreach (var raw in hotkeyString.Split('+'))
        {
            var part = raw.Trim();
            switch (part.ToUpperInvariant())
            {
                case "CTRL":
                case "CONTROL": mods |= MOD_CONTROL; break;
                case "SHIFT":   mods |= MOD_SHIFT;   break;
                case "ALT":     mods |= MOD_ALT;     break;
                case "WIN":     mods |= MOD_WIN;     break;
                default:
                    vk = ResolveVk(part);
                    break;
            }
        }

        return (mods, vk);
    }

    private static uint ResolveVk(string token)
    {
        // VK codes match ASCII for A-Z (0x41-0x5A) and 0-9 (0x30-0x39)
        if (token.Length == 1)
        {
            char c = char.ToUpperInvariant(token[0]);
            if ((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9'))
                return (uint)c;
        }

        // F1-F12: VK_F1 = 0x70 … VK_F12 = 0x7B
        if (token.Length >= 2 && token[0] is 'F' or 'f' &&
            int.TryParse(token[1..], out int fn) && fn >= 1 && fn <= 12)
        {
            return (uint)(0x6F + fn);
        }

        return 0;
    }
}
