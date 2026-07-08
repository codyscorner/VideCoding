# Changelog

All notable changes to Folder Backup Archiver are documented in this file.

## 2026-07-07

### Added
- **Incremental mode** — optional checkbox to skip the backup entirely if the source folder is unchanged since the last successful run for that same source. Detected via a cheap size+mtime manifest hash (no full content re-read), stored per source folder in `settings.json` (`source_manifests`).
- **Backup rotation** — optional "Keep last N backups" spinbox; after a successful run, older archives (and `.sha256` sidecars) sharing the same prefix in the destination folder are deleted automatically, keeping only the N most recent.
- **Tray notifications** — optional Windows notification (via `QSystemTrayIcon`) on backup complete, skipped, or failed, in addition to the existing in-app dialog.

### Notes
- Scheduled/silent CLI mode was considered but intentionally left out — this stays a manual, on-demand backup tool triggered by the user after making changes.
