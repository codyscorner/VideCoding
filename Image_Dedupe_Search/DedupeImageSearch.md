# Image Similarity Dedupe Tool — Project Specification (Medium Scope)

## 1. Overview

A desktop application built with Python + PySide6 that scans a directory of images, computes visual similarity embeddings, and identifies duplicates or near-duplicates. The app provides a Windows-friendly GUI for browsing, reviewing, and managing similar images.

The backend uses CLIP embeddings and cosine similarity to detect visually similar images, even when resized, cropped, or slightly modified.

---

## 2. Core Features

### Image Similarity Engine
- Compute CLIP embeddings for each image
- Cache embeddings to avoid recomputation
- Compare images using cosine similarity
- Adjustable similarity threshold
- Batch scanning of folders

### GUI (PySide6)
- Folder picker
- Thumbnail grid view
- "Find Similar Images" workflow
- Side-by-side comparison viewer
- Progress bar + status updates
- Non-blocking UI via worker threads

### File Management
- Mark images as duplicates
- Move duplicates to a target folder
- Delete duplicates (optional)
- Export similarity report (JSON)

### Configuration
- Embedding model selection (CLIP variants)
- Similarity threshold
- Minimum resolution filter
- Excluded folders

---

## 3. Architecture

### 3.1 High-Level Diagram

```
+------------------+       +------------------------+
|     PySide6 UI   | <---> |   Controller Layer     |
+------------------+       +------------------------+
         |                           |
         v                           v
+------------------+       +------------------------+
| Worker Threads   | --->  |  Image Similarity Core |
+------------------+       +------------------------+
                                 |
                                 v
                      +------------------------+
                      | Embedding Cache (DB)   |
                      +------------------------+
```

---

## 4. Folder Structure

```
image_dedupe_tool/
│
├── app/
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── thumbnail_view.py
│   │   ├── image_compare_dialog.py
│   │   └── resources.qrc
│   │
│   ├── workers/
│   │   ├── scan_worker.py
│   │   ├── embed_worker.py
│   │   └── similarity_worker.py
│   │
│   ├── core/
│   │   ├── embeddings.py
│   │   ├── similarity.py
│   │   ├── cache.py
│   │   └── image_utils.py
│   │
│   ├── config/
│   │   └── settings.py
│   │
│   ├── controller.py
│   └── app.py
│
├── models/
│   └── clip/  (downloaded automatically)
│
├── data/
│   └── cache.sqlite
│
├── tests/
│
└── README.md
```

---

## 5. Backend Components

### 5.1 Embedding Engine (`embeddings.py`)
- Loads CLIP model
- Converts images to embeddings
- Normalizes vectors
- Saves embeddings to SQLite cache

### 5.2 Similarity Engine (`similarity.py`)
- Computes cosine similarity
- Finds nearest neighbors
- Supports batch comparisons
- Threshold-based duplicate detection

### 5.3 Cache Layer (`cache.py`)
- SQLite database with:
  - image path
  - last modified timestamp
  - embedding vector
- Auto-invalidates stale entries

### 5.4 Image Utilities (`image_utils.py`)
- Safe image loading
- Thumbnail generation
- Resolution filtering

---

## 6. GUI Components

### 6.1 Main Window
- Folder picker
- Scan button
- Similarity threshold slider
- Thumbnail grid
- Status bar

### 6.2 Thumbnail Grid (`thumbnail_view.py`)
- Scrollable grid
- Lazy-loaded thumbnails
- Multi-select support

### 6.3 Compare Dialog (`image_compare_dialog.py`)
- Side-by-side view
- Similarity score display
- Move/Delete actions

---

## 7. Worker Threads

### 7.1 Scan Worker
- Walks directory
- Filters valid images
- Emits progress updates

### 7.2 Embedding Worker
- Computes embeddings
- Writes to cache
- Emits completion signals

### 7.3 Similarity Worker
- Loads embeddings
- Computes similarity matrix
- Emits duplicate groups

---

## 8. Configuration (`settings.py`)

| Setting | Default Value |
|---------|---------------|
| `similarity_threshold` | `0.92` |
| `min_resolution` | `(256, 256)` |
| `model_name` | `"ViT-B/32"` |
| `cache_path` | `"./data/cache.sqlite"` |
| `excluded_dirs` | `[]` |

---

## 9. Future Enhancements

- GPU acceleration toggle
- DINOv2 embedding option
- FAISS index for large datasets
- Drag-and-drop folder support
- Auto-grouping of duplicates
- Sidecar metadata export
