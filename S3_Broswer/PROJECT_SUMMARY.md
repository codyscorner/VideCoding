# S3 Browser

PyQt6 file-explorer-style browser for RunPod's S3-compatible network-volume storage. Browse, upload, download, and delete objects on a RunPod volume without the RunPod web console.

## Features

- File-explorer UI: breadcrumb navigation, sortable columns (name / size / type / last modified), folder and file icons
- Upload and download files or whole folders, with progress
- Transfers retry with exponential backoff (6 attempts, 1s→16s) — works around RunPod's transient `403 Forbidden` on the SDK's internal `HeadObject` call
- Credentials stored in the standard AWS credentials file (`~/.aws/credentials`) under their own profile — never in the app config or repo

## RunPod S3 API quirks (learned the hard way)

- RunPod's S3 endpoint can return a transient `403` on `HeadObject` for an object that's perfectly accessible on retry — hence the backoff retries on every transfer
- Endpoint and region follow the datacenter of the network volume (e.g. `https://s3api-eur-is-1.runpod.io`)

## Layout

| File | Purpose |
|------|---------|
| `run.py` | Entry point |
| `s3_browser/main_window.py` | Explorer UI |
| `s3_browser/s3_client.py` | boto3 wrapper with retry/backoff |
| `s3_browser/workers.py` | Background transfer threads |
| `s3_browser/settings_dialog.py` | Endpoint/credentials setup |
| `s3_browser/config.py` | Config + AWS credentials-file handling |

## Building the EXE

```
pyinstaller S3Browser.spec
```

Deployed EXE: `P:\Apps\VibeCoded\S3 Browser\`

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.
