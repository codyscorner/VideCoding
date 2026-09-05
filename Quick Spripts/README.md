# Quick Scripts

Small standalone PowerShell scripts for one-off Windows housekeeping tasks — not full apps, just utilities kept here so they don't get lost.

## Scripts

### `Clear-RecentItems.ps1`

Clears Windows 11's "Recent" items (File Explorer Quick Access recents, and the Recent list in Open/Save dialogs) **without** losing pinned Quick Access folders.

Pinned folders and recent-item history live in the same jump-list files, so there's no way to selectively delete just the recents from inside them. This script snapshots which folders are currently pinned, clears everything, then re-pins those folders afterward.

```powershell
.\Clear-RecentItems.ps1
```

### `Get-QuickAccessPins.ps1`

Lists Quick Access entries and shows whether each is actually **pinned** versus just a "frequent folder" that shows up automatically. Detection works by checking whether the item exposes an "Unpin from Quick access" verb — only pinned items have it.

```powershell
.\Get-QuickAccessPins.ps1
```

## Notes

- Both scripts use the Shell.Application COM object to read Quick Access, so they only work on Windows.
- Deleting the `AutomaticDestinations`/`CustomDestinations` jump-list files directly (instead of using `Clear-RecentItems.ps1`) unpins Quick Access folders too — that's exactly what this script works around.
