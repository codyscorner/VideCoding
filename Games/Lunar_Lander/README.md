# Lunar Lander

A retro arcade-style Lunar Lander game with a phosphor-green terminal aesthetic, implemented as a single HTML file and wrapped in a WinForms desktop app via WebView2.

## How It Works

- `LunarLander.html` — complete game in one file (HTML + CSS + JS), no external dependencies beyond Google Fonts
- `LunarLanderApp/` — WinForms (.NET 10) host that loads the HTML into a WebView2 control for a native desktop window

## Gameplay

- Land the module on a flat landing pad before fuel runs out
- Throttle carefully — too much speed on touchdown and you crash
- VT323 / Share Tech Mono phosphor-green aesthetic inspired by Atari 1979

## Running

**Browser** (simplest):
```
Open LunarLander.html directly in any modern browser
```

**Desktop app** (WinForms/WebView2):
```
dotnet run --project LunarLanderApp
```
Or open `LunarLanderApp/LunarLanderApp.csproj` in Visual Studio and run.

## Requirements (desktop app)

- .NET 10
- Microsoft.Web.WebView2 (NuGet)
- Edge WebView2 Runtime (pre-installed on Windows 11)

## Future Enhancements

- [ ] Persistent high-score table (localStorage)
- [ ] Sound effects toggle
- [ ] Pause key
- [ ] Difficulty settings
