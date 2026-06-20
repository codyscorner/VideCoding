# ScreenSnap

Windows screen capture and annotation app. Personal project, single developer, Windows 10/11 only.
Full feature spec and rationale: see `ScreenSnap-Build-Plan.md`.

## Stack

- .NET 10 (LTS) with WPF (the build plan originally said .NET 8; .NET 8 support ends Nov 2026 — prefer 10 for new code. Run `dotnet --list-sdks` and adjust `global.json` if needed.)
- SkiaSharp for all rendering (NOT GDI+ / System.Drawing)
- CommunityToolkit.Mvvm for MVVM
- Hardcodet.NotifyIcon.Wpf for system tray
- System.Text.Json for config
- xUnit for tests

## Solution layout

```
src/ScreenSnap.Core/     — capture engine, annotation layers, services, models. NO UI dependencies.
src/ScreenSnap.UI/       — WPF app: views, viewmodels, controls. References Core.
src/ScreenSnap.Plugins/  — IPlugin interface only.
tests/ScreenSnap.Tests/  — xUnit tests for Core.
```

## Commands

```bash
dotnet build ScreenSnap.sln
dotnet test tests/ScreenSnap.Tests
dotnet run --project src/ScreenSnap.UI
```

## Architecture rules (do not violate)

1. **ScreenSnap.Core must never reference WPF or any UI package.** SkiaSharp.Views.WPF belongs in ScreenSnap.UI only. Core uses plain SkiaSharp.
2. **Use SkiaSharp types throughout Core** — capture services return `SKBitmap`, not System.Drawing.Bitmap. Convert at the UI/export boundary only if required.
3. **Annotations are independent layer objects** implementing `IAnnotationLayer` (Render, HitTest, Transform). Non-destructive editing — never bake annotations into the captured bitmap until export.
4. **Undo/redo uses the command pattern via `IUndoableCommand`** — NOT `ICommand`. That name collides with `System.Windows.Input.ICommand` and CommunityToolkit's RelayCommand. Every editor mutation goes through `CommandHistory`.
5. **MVVM in the UI project** — no business logic in code-behind. Use CommunityToolkit source generators (`[ObservableProperty]`, `[RelayCommand]`).

## Windows interop notes

- Global hotkeys: Win32 `RegisterHotKey` P/Invoke, handled via `WndProc` (`WM_HOTKEY = 0x0312`). Always unregister on dispose.
- Capture: prefer `Windows.Graphics.Capture` API, fall back to GDI BitBlt.
- Multi-monitor: app must be per-monitor DPI aware (set in app manifest). Coordinates from Win32 are physical pixels; WPF uses DIPs — convert carefully.

## Conventions

- File-scoped namespaces, 4-space indent (enforced by `.editorconfig`)
- One type per file, filename matches type name
- Async capture APIs end in `Async`
- Config lives in a single JSON file (schema in build plan §9); access only via `ConfigService`
- Default hotkeys: region `Ctrl+Shift+4`, fullscreen `Ctrl+Shift+3`, window `Ctrl+Shift+5` — all user-configurable

## Priorities

Build P0 features first: region/fullscreen/window capture, arrow/rectangle/text/bubble annotations, global hotkeys, tray icon, clipboard copy, save with datetime auto-naming, undo/redo. The speech bubble tool is the key differentiator — don't cut it.
