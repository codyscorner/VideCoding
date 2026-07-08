# Asteroids

A classic Asteroids arcade game implemented as a single-file HTML canvas game, wrapped in a WinForms desktop app via WebView2.

## How It Works

- `index.html` — the complete game: all logic, rendering, and controls in one file, no external dependencies
- `AsteroidsApp/` — WinForms (.NET 10) host that loads the HTML into a WebView2 control for a native desktop window

## Gameplay

- **Arrow Keys**: Rotate left/right and thrust forward
- **Space**: Shoot
- Large asteroids split into medium, medium into small
- 3 lives with invincibility blink on respawn
- Score on HUD; waves increase difficulty

## Running

**Browser** (simplest):
```
Open index.html directly in any modern browser
```

**Desktop app** (WinForms/WebView2):
```
dotnet run --project AsteroidsApp
```
Or open `AsteroidsApp/AsteroidsApp.csproj` in Visual Studio and run.

## Requirements (desktop app)

- .NET 10
- Microsoft.Web.WebView2 (NuGet)
- Edge WebView2 Runtime (pre-installed on Windows 11)

## Future Enhancements

- [ ] Persistent high-score table (localStorage)
- [ ] Sound effects toggle
- [ ] Pause key
- [ ] Difficulty settings
