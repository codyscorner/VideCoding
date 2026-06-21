# IMDB Photo Downloader

Downloads all gallery photos from any IMDB title or actor/actress page into organized named subfolders.

## Features

- Supports both title pages (`/title/tt...`) and actor/actress pages (`/name/nm...`)
- Auto-names the download subfolder from the title/person name
- Files named `<Title>_0001.jpg` to avoid conflicts when copying across folders
- Scrolls gallery to load all lazy-loaded images (bypasses the ~72 image limit)
- Skips already-downloaded files on re-run
- Persistent root folder setting saved between sessions
- Clickable folder link opens Explorer when download completes

## Requirements

```
pip install PyQt6 playwright requests beautifulsoup4
python -m playwright install chromium
```

## Usage

**Run from source:**
```
python imdb_downloader.py
```

**Or use the batch launcher:**
```
IMDB_Photo_Downloader.bat
```

1. Set your **Root Folder** — all downloads go into named subfolders here
2. Paste any IMDB URL (title or actor/actress)
3. Hit **Download**

## Examples

```
https://www.imdb.com/title/tt0111161/        ← movie
https://www.imdb.com/title/tt2543796/        ← TV show
https://www.imdb.com/name/nm1760388/         ← actor/actress
```

## Output Structure

```
Root Folder/
  Girl Meets World (TV Series 2014-2017)/
    Girl_Meets_World__TV_Series_2014_2017__0001.jpg
    Girl_Meets_World__TV_Series_2014_2017__0002.jpg
    ...
  America Olivo/
    America_Olivo_0001.jpg
    ...
```

## Changelog

### v1.0.0
- Initial release
- Title and actor/actress URL support
- Lazy-load scrolling to get all images past the 72-image limit
- Persistent root folder setting
- Named subfolders with conflict-safe filenames
- Clickable Explorer link on completion
