# Screen Capture & Annotation Application - Build Plan

**Project Codename**: ScreenSnap  
**Target Platform**: Windows 10/11  
**Primary User**: Personal/private use with extensibility for future features

---

## 1. Project Goals

Build a lightweight, modular screen capture application with rich annotation capabilities that:
- Maps to global hotkeys for instant capture
- Provides markup tools (arrows, boxes, text, speech bubbles)
- Is fully customizable and extensible for personal modifications
- Maintains a clean, maintainable codebase

---

## 2. Feature Requirements

### Core Capture Features
| Feature | Priority | Notes |
|---------|----------|-------|
| Region selection capture | P0 | Click-drag selection with crosshair |
| Full screen capture | P0 | Single hotkey |
| Active window capture | P0 | Auto-detect focused window |
| Multi-monitor support | P1 | Handle different DPIs |
| Delayed capture (timer) | P2 | 3-5-10 second options |
| Scrolling capture | P3 | For long pages/documents |

### Annotation Tools
| Tool | Priority | Implementation Notes |
|------|----------|---------------------|
| Arrow | P0 | Directional, customizable color/thickness |
| Rectangle/Square | P0 | Filled or outline, rounded corners option |
| Ellipse/Circle | P1 | Filled or outline |
| Text box | P0 | Font selection, color, background |
| Speech/thought bubble | P0 | Key differentiator - callout style |
| Freehand drawing | P1 | Pen tool with smoothing |
| Blur/pixelate | P1 | For sensitive info redaction |
| Highlight/marker | P1 | Semi-transparent overlay |
| Numbering/steps | P2 | Auto-increment badges (1, 2, 3...) |
| Crop tool | P1 | Post-capture adjustment |

### Workflow Features
| Feature | Priority | Borrowed From |
|---------|----------|---------------|
| Global hotkey registration | P0 | GreenShot, ShareX |
| System tray integration | P0 | All tools |
| Clipboard copy | P0 | Standard |
| Save to file | P0 | Auto-naming by date/time (Lightscreen) |
| Undo/redo | P0 | Command pattern |
| In-capture annotation toolbar | P1 | Flameshot style |
| Post-capture action chains | P2 | ShareX workflows |
| Capture history | P2 | Thumbnail browser |

---

## 3. Technology Stack

### Recommended Stack
```
Framework:      .NET 10 (LTS) with WPF
Graphics:       SkiaSharp (GPU-accelerated, modern)
Hotkeys:        Win32 RegisterHotKey() via P/Invoke
Architecture:   MVVM with plugin support
Config:         JSON (System.Text.Json)
Installer:      MSIX or single-file publish
```

### Why This Stack
- **WPF over WinForms**: Modern UI, better XAML styling, hardware acceleration
- **SkiaSharp over GDI+**: Cross-platform potential, better performance, layer support
- **.NET 10**: Current LTS (supported to Nov 2028). Note: .NET 8 support ends Nov 2026, so prefer 10 for a new project — fall back to 8 only if the SDK isn't installed (`dotnet --list-sdks`)
- **MVVM**: Clean separation for future UI changes

### Key Libraries
```csharp
// NuGet packages
SkiaSharp                    // 2D graphics rendering (Core + UI)
SkiaSharp.Views.WPF          // WPF integration (UI project ONLY — Core stays UI-free)
CommunityToolkit.Mvvm        // MVVM helpers (UI)
System.Text.Json             // Configuration (Core)
Hardcodet.NotifyIcon.Wpf     // System tray (UI)
```

---

## 4. Architecture Design

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    ScreenSnap App                        │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  Capture    │  │  Annotation │  │  Export/Save    │  │
│  │  Engine     │  │  Editor     │  │  Pipeline       │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                │                   │          │
│  ┌──────┴────────────────┴───────────────────┴───────┐  │
│  │              Core Services Layer                   │  │
│  │  • HotkeyService    • ConfigService               │  │
│  │  • ClipboardService • HistoryService              │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Plugin Interface (IPlugin)            │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Module Breakdown

#### Capture Engine
```csharp
public interface ICaptureService
{
    // SKBitmap (SkiaSharp), NOT System.Drawing.Bitmap — keeps Core UI-free
    // and avoids GDI+ <-> Skia conversions in the editor pipeline
    Task<SKBitmap> CaptureRegionAsync();
    Task<SKBitmap> CaptureWindowAsync(IntPtr hwnd);
    Task<SKBitmap> CaptureFullScreenAsync();
    Task<SKBitmap> CaptureMonitorAsync(int monitorIndex);
}
```
- Uses `Windows.Graphics.Capture` API (modern) or GDI BitBlt (fallback)
- Handles DPI awareness for multi-monitor setups

#### Annotation Editor
```csharp
public interface IAnnotationLayer
{
    Guid Id { get; }
    void Render(SKCanvas canvas);
    bool HitTest(SKPoint point);
    void Transform(SKMatrix matrix);
}

// Concrete implementations
public class ArrowLayer : IAnnotationLayer { }
public class RectangleLayer : IAnnotationLayer { }
public class TextLayer : IAnnotationLayer { }
public class BubbleLayer : IAnnotationLayer { }
```
- Layer-based architecture for non-destructive editing
- Each annotation is an independent object
- Command pattern for undo/redo

#### Hotkey Service
```csharp
public class HotkeyService : IDisposable
{
    [DllImport("user32.dll")]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);
    
    public void Register(Keys key, ModifierKeys modifiers, Action callback);
    public void Unregister(int id);
}
```

---

## 5. Key Implementation Details

### Global Hotkey Registration (Win32)
```csharp
// Constants
const uint MOD_ALT = 0x0001;
const uint MOD_CONTROL = 0x0002;
const uint MOD_SHIFT = 0x0004;

// Register Ctrl+Shift+S for region capture
RegisterHotKey(hwnd, HOTKEY_REGION, MOD_CONTROL | MOD_SHIFT, (uint)Keys.S);

// Handle in WndProc
protected override void WndProc(ref Message m)
{
    if (m.Msg == WM_HOTKEY)
    {
        int id = m.WParam.ToInt32();
        // Trigger appropriate capture mode
    }
}
```

### Undo/Redo with Command Pattern
```csharp
// Named IUndoableCommand (not ICommand) to avoid collision with
// System.Windows.Input.ICommand and CommunityToolkit.Mvvm's RelayCommand
public interface IUndoableCommand
{
    void Execute();
    void Undo();
}

public class AddLayerCommand : IUndoableCommand
{
    private readonly IAnnotationLayer _layer;
    private readonly LayerManager _manager;
    
    public void Execute() => _manager.AddLayer(_layer);
    public void Undo() => _manager.RemoveLayer(_layer);
}

public class CommandHistory
{
    private Stack<IUndoableCommand> _undoStack = new();
    private Stack<IUndoableCommand> _redoStack = new();
    
    public void Execute(IUndoableCommand cmd) { cmd.Execute(); _undoStack.Push(cmd); _redoStack.Clear(); }
    public void Undo() { var cmd = _undoStack.Pop(); cmd.Undo(); _redoStack.Push(cmd); }
    public void Redo() { var cmd = _redoStack.Pop(); cmd.Execute(); _undoStack.Push(cmd); }
}
```

### Speech Bubble Implementation
```csharp
public class BubbleLayer : IAnnotationLayer
{
    public SKPoint TailPoint { get; set; }      // Where the tail points
    public SKRect BubbleRect { get; set; }      // Main bubble area
    public string Text { get; set; }
    public BubbleStyle Style { get; set; }      // Speech vs Thought
    
    public void Render(SKCanvas canvas)
    {
        using var path = new SKPath();
        
        // Draw rounded rectangle for bubble body
        path.AddRoundRect(BubbleRect, 10, 10);
        
        // Add tail triangle
        path.MoveTo(TailAnchorPoint);
        path.LineTo(TailPoint);
        path.LineTo(TailAnchorPoint2);
        path.Close();
        
        canvas.DrawPath(path, _fillPaint);
        canvas.DrawPath(path, _strokePaint);
        
        // Draw text
        canvas.DrawText(Text, TextPosition, _textPaint);
    }
}
```

---

## 6. Default Hotkey Configuration

| Action | Default Hotkey | Configurable |
|--------|---------------|--------------|
| Region capture | `Ctrl+Shift+4` | Yes |
| Full screen | `Ctrl+Shift+3` | Yes |
| Active window | `Ctrl+Shift+5` | Yes |
| Quick save last | `Ctrl+Shift+S` | Yes |
| Open editor | `Ctrl+Shift+E` | Yes |

---

## 7. Project Structure

```
ScreenSnap/
├── src/
│   ├── ScreenSnap.Core/
│   │   ├── Capture/
│   │   │   ├── ICaptureService.cs
│   │   │   ├── RegionCaptureService.cs
│   │   │   └── WindowCaptureService.cs
│   │   ├── Annotations/
│   │   │   ├── Layers/
│   │   │   │   ├── IAnnotationLayer.cs
│   │   │   │   ├── ArrowLayer.cs
│   │   │   │   ├── RectangleLayer.cs
│   │   │   │   ├── TextLayer.cs
│   │   │   │   └── BubbleLayer.cs
│   │   │   ├── LayerManager.cs
│   │   │   └── Commands/
│   │   │       ├── IUndoableCommand.cs
│   │   │       └── CommandHistory.cs
│   │   ├── Services/
│   │   │   ├── HotkeyService.cs
│   │   │   ├── ClipboardService.cs
│   │   │   └── ConfigService.cs
│   │   └── Models/
│   │       └── CaptureSettings.cs
│   │
│   ├── ScreenSnap.UI/
│   │   ├── App.xaml
│   │   ├── Views/
│   │   │   ├── EditorWindow.xaml
│   │   │   ├── RegionSelectOverlay.xaml
│   │   │   └── SettingsWindow.xaml
│   │   ├── ViewModels/
│   │   │   ├── EditorViewModel.cs
│   │   │   └── SettingsViewModel.cs
│   │   └── Controls/
│   │       ├── AnnotationCanvas.cs
│   │       └── ToolPalette.xaml
│   │
│   └── ScreenSnap.Plugins/
│       └── IPlugin.cs
│
├── tests/
│   └── ScreenSnap.Tests/
│
├── docs/
│   └── architecture.md
│
└── ScreenSnap.sln
```

---

## 8. Ideas Borrowed from Research

| Idea | Source | Implementation |
|------|--------|----------------|
| In-capture floating toolbar | Flameshot | Toolbar appears at capture boundary |
| Workflow/action chains | ShareX | Post-capture action pipeline |
| Auto-naming by datetime | Lightscreen | `Screenshot_2024-01-15_14-30-22.png` |
| Plugin architecture | GreenShot/ShareX | `IPlugin` interface with MEF |
| Keyboard-driven annotation | Flameshot | Single-key tool selection (A=arrow, T=text) |
| Toast notifications | ShareX | Confirm saves/copies non-intrusively |
| Remember last tool settings | Flameshot | Persist color/thickness between sessions |
| Smart guides | ShareX | Alignment hints during annotation |

---

## 9. Configuration File Format

```json
{
  "capture": {
    "defaultFormat": "png",
    "jpegQuality": 90,
    "includeMouseCursor": false,
    "autoSavePath": "%USERPROFILE%\\Screenshots",
    "fileNamePattern": "Screenshot_{date}_{time}"
  },
  "hotkeys": {
    "regionCapture": "Ctrl+Shift+4",
    "fullScreen": "Ctrl+Shift+3",
    "activeWindow": "Ctrl+Shift+5"
  },
  "editor": {
    "defaultTool": "arrow",
    "arrowColor": "#FF0000",
    "arrowThickness": 3,
    "textFont": "Segoe UI",
    "textSize": 14,
    "bubbleStyle": "speech"
  },
  "behavior": {
    "openEditorAfterCapture": true,
    "copyToClipboardAfterSave": true,
    "showTrayNotifications": true
  }
}
```

---

## 10. Getting Started Commands

```bash
# Create solution
dotnet new sln -n ScreenSnap

# Create projects
dotnet new classlib -n ScreenSnap.Core -o src/ScreenSnap.Core
dotnet new wpf -n ScreenSnap.UI -o src/ScreenSnap.UI
dotnet new classlib -n ScreenSnap.Plugins -o src/ScreenSnap.Plugins
dotnet new xunit -n ScreenSnap.Tests -o tests/ScreenSnap.Tests

# Add to solution
dotnet sln add src/ScreenSnap.Core
dotnet sln add src/ScreenSnap.UI
dotnet sln add src/ScreenSnap.Plugins
dotnet sln add tests/ScreenSnap.Tests

# Add packages
cd src/ScreenSnap.Core
dotnet add package SkiaSharp

cd ../ScreenSnap.UI
dotnet add package SkiaSharp.Views.WPF      # WPF integration lives in UI, NOT Core
dotnet add package Hardcodet.NotifyIcon.Wpf
dotnet add package CommunityToolkit.Mvvm
dotnet add reference ../ScreenSnap.Core
```

---

## 11. Reference Repositories

- **GreenShot**: https://github.com/greenshot/greenshot (C#, plugin architecture)
- **ShareX**: https://github.com/ShareX/ShareX (C#, workflows)
- **Flameshot**: https://github.com/flameshot-org/flameshot (C++/Qt, UX patterns)
- **Ksnip**: https://github.com/ksnip/ksnip (C++/Qt, annotations)

---

*Document created for Fable 5 build reference*  
*Last updated: 2026-06-10 (rev 2 — IUndoableCommand rename, SKBitmap capture API, SkiaSharp.Views.WPF moved to UI project, .NET 10 LTS)*
