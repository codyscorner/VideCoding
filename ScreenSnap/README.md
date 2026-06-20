# ScreenSnap

A Windows screen capture and annotation app built with WPF + SkiaSharp. Personal project, Windows 10/11 only.

See [ScreenSnap-Build-Plan.md](ScreenSnap-Build-Plan.md) for the full feature spec and roadmap.

## Stack

- **.NET 10** + WPF
- **SkiaSharp** — all drawing and annotation rendering
- **CommunityToolkit.Mvvm** — MVVM bindings
- **Hardcodet.NotifyIcon.Wpf** — system tray
- **System.Text.Json** — config
- **xUnit** — tests

## Solution Layout

```
src/ScreenSnap.Core/     — capture engine, annotation layers, services, models (no UI dependencies)
src/ScreenSnap.UI/       — WPF app: views, viewmodels, controls (references Core)
src/ScreenSnap.Plugins/  — IPlugin interface
tests/ScreenSnap.Tests/  — xUnit tests for Core
```

## Planned Features

- Region selection, fullscreen, and active window capture
- Annotation tools: arrows, rectangles, text labels, speech bubbles
- Global hotkeys for instant capture
- System tray for background operation
- Undo/redo annotation history
- Copy to clipboard, save to file

## Commands

```bash
dotnet build ScreenSnap.sln
dotnet test tests/ScreenSnap.Tests
dotnet run --project src/ScreenSnap.UI
```

## Status

Scaffold complete — core models, annotation layer interfaces, and capture service stubs are in place. Capture implementations and UI are in progress.
