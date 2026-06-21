using System.Windows;
using System.Windows.Input;
using SkiaSharp;
using SkiaSharp.Views.Desktop;
using SkiaSharp.Views.WPF;
using ScreenSnap.Core.Annotations.Commands;
using ScreenSnap.Core.Annotations.Layers;
using ScreenSnap.Core.Win32;
using ScreenSnap.UI.ViewModels;
using ScreenSnap.UI.Views;

namespace ScreenSnap.UI.Controls;

public class AnnotationCanvas : SKElement
{
    private SKBitmap? _source;
    private EditorViewModel? _vm;

    // Drag state (arrow / rect / ellipse / highlight / bubble phase-1)
    private SKPoint _dragStart;
    private bool _isDragging;

    // Bubble two-phase state
    private bool _waitingForBubbleTail;
    private SKRect _pendingBubbleRect;

    // Freehand accumulation
    private FreehandLayer? _freehandInProgress;

    // Transient preview rendered during a drag — never committed to LayerManager
    private IAnnotationLayer? _preview;

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    public void SetSource(SKBitmap bitmap, EditorViewModel vm)
    {
        if (_vm is not null)
            _vm.LayersChanged -= OnLayersChanged;

        _source = bitmap;
        _vm = vm;
        _vm.LayersChanged += OnLayersChanged;

        // Size the WPF element in DIPs so the bitmap maps 1:1 at current DPI
        var dpiScale = ScreenInfo.GetSystemDpiScale();
        Width = bitmap.Width / dpiScale;
        Height = bitmap.Height / dpiScale;

        InvalidateVisual();
    }

    // ------------------------------------------------------------------
    // Painting
    // ------------------------------------------------------------------

    protected override void OnPaintSurface(SKPaintSurfaceEventArgs e)
    {
        var canvas = e.Surface.Canvas;
        canvas.Clear(SKColors.Transparent);

        if (_source is not null)
            canvas.DrawBitmap(_source, SKPoint.Empty);

        _vm?.LayerManager.RenderAll(canvas);
        _preview?.Render(canvas);

        // Draw tail-placement guide when waiting for bubble tail
        if (_waitingForBubbleTail)
            DrawBubbleTailGuide(canvas);
    }

    private void DrawBubbleTailGuide(SKCanvas canvas)
    {
        using var paint = new SKPaint
        {
            Color = new SKColor(0, 120, 215, 180),
            Style = SKPaintStyle.Stroke,
            StrokeWidth = 2,
            PathEffect = SKPathEffect.CreateDash(new[] { 6f, 4f }, 0),
            IsAntialias = true,
        };
        canvas.DrawRoundRect(_pendingBubbleRect, 10, 10, paint);
    }

    // ------------------------------------------------------------------
    // Mouse events
    // ------------------------------------------------------------------

    protected override void OnMouseLeftButtonDown(MouseButtonEventArgs e)
    {
        if (_vm is null) return;
        var pt = ToSk(e.GetPosition(this));

        if (_vm.ActiveTool == "bubble" && _waitingForBubbleTail)
        {
            CommitBubble(pt);
            _waitingForBubbleTail = false;
            _vm.StatusText = "Ready";
            InvalidateVisual();
            return;
        }

        if (_vm.ActiveTool == "text")
        {
            ShowTextInput(pt);
            return;
        }

        if (_vm.ActiveTool == "freehand")
        {
            _freehandInProgress = new FreehandLayer();
            _freehandInProgress.Points.Add(pt);
            _isDragging = true;
            CaptureMouse();
            base.OnMouseLeftButtonDown(e);
            return;
        }

        _dragStart = pt;
        _isDragging = true;
        CaptureMouse();
        base.OnMouseLeftButtonDown(e);
    }

    protected override void OnMouseMove(MouseEventArgs e)
    {
        if (!_isDragging || _vm is null) return;
        var pt = ToSk(e.GetPosition(this));

        if (_vm.ActiveTool == "freehand" && _freehandInProgress is not null)
        {
            _freehandInProgress.Points.Add(pt);
            _preview = _freehandInProgress;
            InvalidateVisual();
            base.OnMouseMove(e);
            return;
        }

        _preview = _vm.ActiveTool switch
        {
            "arrow"     => new ArrowLayer { Start = _dragStart, End = pt },
            "rect"      => new RectangleLayer { Rect = MakeRect(_dragStart, pt), CornerRadius = 4f },
            "ellipse"   => new EllipseLayer { Rect = MakeRect(_dragStart, pt) },
            "highlight" => new HighlightLayer { Rect = MakeRect(_dragStart, pt) },
            "bubble"    => new RectangleLayer
            {
                Rect = MakeRect(_dragStart, pt),
                StrokeColor = new SKColor(0, 120, 215),
                CornerRadius = 10f,
            },
            _ => null,
        };

        InvalidateVisual();
        base.OnMouseMove(e);
    }

    protected override void OnMouseLeftButtonUp(MouseButtonEventArgs e)
    {
        if (!_isDragging || _vm is null) return;
        _isDragging = false;
        ReleaseMouseCapture();
        _preview = null;

        var pt = ToSk(e.GetPosition(this));
        var rect = MakeRect(_dragStart, pt);

        switch (_vm.ActiveTool)
        {
            case "arrow":
                if (SKPoint.Distance(_dragStart, pt) > 2)
                    Commit(new ArrowLayer { Start = _dragStart, End = pt });
                break;

            case "rect":
                if (rect.Width > 2 && rect.Height > 2)
                    Commit(new RectangleLayer { Rect = rect, CornerRadius = 4f });
                break;

            case "ellipse":
                if (rect.Width > 2 && rect.Height > 2)
                    Commit(new EllipseLayer { Rect = rect });
                break;

            case "highlight":
                if (rect.Width > 2 && rect.Height > 2)
                    Commit(new HighlightLayer { Rect = rect });
                break;

            case "freehand":
                if (_freehandInProgress is not null && _freehandInProgress.Points.Count >= 2)
                    Commit(_freehandInProgress);
                _freehandInProgress = null;
                break;

            case "bubble":
                if (rect.Width > 10 && rect.Height > 10)
                {
                    _pendingBubbleRect = rect;
                    _waitingForBubbleTail = true;
                    _vm.StatusText = "Click to place the speech bubble tail";
                }
                break;
        }

        InvalidateVisual();
        base.OnMouseLeftButtonUp(e);
    }

    // ------------------------------------------------------------------
    // Tool helpers
    // ------------------------------------------------------------------

    private void ShowTextInput(SKPoint position)
    {
        var dialog = new TextInputDialog { Owner = Window.GetWindow(this) };
        if (dialog.ShowDialog() != true || string.IsNullOrEmpty(dialog.InputText)) return;
        Commit(new TextLayer { Position = position, Text = dialog.InputText });
        InvalidateVisual();
    }

    private void CommitBubble(SKPoint tailPoint)
    {
        var dialog = new TextInputDialog { Owner = Window.GetWindow(this) };
        string text = "";
        if (dialog.ShowDialog() == true)
            text = dialog.InputText ?? "";

        Commit(new BubbleLayer
        {
            BubbleRect = _pendingBubbleRect,
            TailPoint = tailPoint,
            Text = text,
        });
    }

    private void Commit(IAnnotationLayer layer)
    {
        _vm!.ExecuteCommand(new AddLayerCommand(_vm.LayerManager, layer));
        InvalidateVisual();
    }

    // ------------------------------------------------------------------
    // Utility
    // ------------------------------------------------------------------

    private void OnLayersChanged() => InvalidateVisual();

    private SKPoint ToSk(System.Windows.Point p)
    {
        double sx = CanvasSize.Width  / Math.Max(ActualWidth,  1);
        double sy = CanvasSize.Height / Math.Max(ActualHeight, 1);
        return new SKPoint((float)(p.X * sx), (float)(p.Y * sy));
    }

    private static SKRect MakeRect(SKPoint a, SKPoint b) =>
        new(Math.Min(a.X, b.X), Math.Min(a.Y, b.Y), Math.Max(a.X, b.X), Math.Max(a.Y, b.Y));
}
