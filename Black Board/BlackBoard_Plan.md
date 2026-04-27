# Project: DataFlow Blackboard Architect

## 1. Overview
A specialized PyQt6 desktop application designed for database professionals to model ETL workflows, schema relationships, and application logic on an infinite canvas.

## 2. Core Features
* **Infinite Blackboard:** Zoomable/pannable canvas with a dark-themed grid.
* **Database-First Nodes:** Specialized blocks for Tables (including columns/types), Stored Procedures, and API Endpoints.
* **Dynamic Connectors:** Directed visual lines representing Data Flows or Foreign Key relationships (source port → target port).
* **4K Export Engine:** One-click rendering of the full scene to a $3840 \times 2160$ PNG file using `QPainter` on a `QImage`.
* **Persistence:** Save and load your designs using local JSON files (.dflow).

## 3. Technical Requirements
* **Language:** Python 3.10+
* **Framework:** PyQt6
* **Graphics:** QGraphicsScene / QGraphicsView with OpenGL acceleration via `QOpenGLWidget` viewport (must be set explicitly — not automatic).
* **Compiler:** PyInstaller or Nuitka (for .exe generation).

## 4. Development Roadmap

### Phase 1: The Engine
- [x] Initialize `QGraphicsView` with `QOpenGLWidget` as the viewport for hardware acceleration.
- [x] Implement mouse-wheel zoom and middle-click pan.
- [x] Create a "Save to 4K" function using `QPainter` and `QImage` that renders the full scene (not just the visible viewport).

### Phase 2: The Nodes
- [x] Create a `BaseNode` class with drag-and-drop capabilities.
- [x] Add a `TableNode` subclass with a list-based UI for columns.
- [x] Implement "Connection Ports" on the left and right of each node (typed as `source` or `target`).
- [x] Support single-click selection and rubber-band (drag) multi-select via `QGraphicsScene`.
- [x] Wire in `QUndoStack` with a `QUndoCommand` base so all future actions (add, move, delete) are undoable.

### Phase 3: The Logic
- [x] Build a directed `ConnectionLine` class (source port → target port) that updates its path as nodes move.
- [x] Add Delete key and context-menu "Delete" action to remove selected nodes and their attached connections.
- [x] Add a context menu (Right-Click) to add nodes or change node colors.
- [x] Implement `json.dump` and `json.load` logic for saving the full canvas state (nodes, ports, connections, zoom level).

### Phase 4: The Build
- [ ] Finalize asset paths (icons, themes).
- [ ] Run PyInstaller script to bundle into a single `DataFlowArchitect.exe`.

## 5. Deployment Commands
```bash
# Install dependencies
pip install PyQt6 pyinstaller

# Build the executable
pyinstaller --noconsole --onefile --name "DataFlowArchitect" main.py
```
