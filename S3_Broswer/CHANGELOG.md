# S3 Browser — Changelog

## v1.0.3 (2026-08-07)
- Transfer retries bumped from 3 attempts (flat 1s delay) to 6 attempts with exponential backoff (1s/2s/4s/8s/16s) — RunPod's transient 403 on `HeadObject` during downloads was still outlasting the old fixed 1s retry window on some days

## v1.0.2 (2026-08-06)
- Fixed Size/Type/Last Modified columns being stuck at their initial width — Qt's default `stretchLastSection` was locking the last column, now all three are freely drag-resizable with sensible starting widths
- Window title now shows the app version (`S3 Browser v1.0.2`)

## v1.0.1 (2026-08-06)
- Upload/download of individual files now retries up to 3 times (1s apart) before reporting a failure — RunPod's endpoint was seen returning a transient `403 Forbidden` on the SDK's internal `HeadObject` call during folder downloads even though the object was perfectly accessible on retry

## v1.0.0 (2026-08-06)
- Initial release: PyQt6 file-explorer-style browser for RunPod's S3-compatible storage
- Breadcrumb navigation, sortable table (name/size/type/modified) with folder/file icons
- Upload files or whole folders (drag-and-drop from Explorer, or toolbar dialogs), preserving nested folder structure
- Download files or folders (recursive) to a chosen local destination, with a byte-accurate progress dialog
- New folder, rename (copy+delete, works on files and folders), delete (multi-select, confirmation prompt)
- Right-click context menu; F2 rename, Delete key, F5 refresh shortcuts
- Settings dialog to change bucket/region/endpoint/profile and update AWS credentials without leaving the app
- Credentials are stored only in the local AWS credentials file (`~/.aws/credentials`), never duplicated into the app's own config
- Connected to bucket `zyg8x1wtwr` on RunPod datacenter `us-ca-2` (`https://s3api-us-ca-2.runpod.io`)

### RunPod S3 compatibility fixes found during testing
- RunPod's endpoint rejects the bulk `DeleteObjects` API with `307 Temporary Redirect` — the client deletes objects one at a time (`delete_object`) instead
- RunPod's backend leaves empty "ghost" directory nodes behind after all files inside are deleted (`DeleteObject` on the folder key fails with `InvalidArgument: directory not empty` even when `ListObjectsV2` shows it as empty) — folder deletes now also walk and delete every nested directory path bottom-up as a best-effort cleanup so no empty folders are left behind
