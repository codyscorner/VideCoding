# Clears Windows 11 "Recent" items (File Explorer Quick Access recents,
# and the Recent list shown in Open/Save dialogs) WITHOUT losing pinned
# Quick Access folders.
#
# Pinned folders and recent-item history live in the same jump-list files,
# so there's no way to selectively delete just the recents from inside them.
# Instead: snapshot which folders are currently pinned, clear everything,
# then re-pin those folders afterward.

$ErrorActionPreference = 'SilentlyContinue'

# --- 1. Capture currently pinned Quick Access folders ---
$shellApp = New-Object -ComObject Shell.Application
$quickAccess = $shellApp.Namespace('shell:::{679f85cb-0220-4080-b29b-5540cc05aab6}')

$pinnedPaths = @(
    foreach ($item in $quickAccess.Items()) {
        $verbNames = $item.Verbs() | ForEach-Object { $_.Name -replace '&', '' }
        if ($verbNames -contains 'Unpin from Quick access') {
            $item.Path
        }
    }
)

[System.Runtime.Interopservices.Marshal]::ReleaseComObject($quickAccess) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($shellApp) | Out-Null

Write-Host "Preserving $($pinnedPaths.Count) pinned folder(s):" -ForegroundColor Cyan
$pinnedPaths | ForEach-Object { Write-Host "  $_" }

# --- 2. Clear recent items ---
$recentPath = Join-Path $env:APPDATA 'Microsoft\Windows\Recent'
Get-ChildItem -Path $recentPath -File | Remove-Item -Force -Confirm:$false
Get-ChildItem -Path (Join-Path $recentPath 'AutomaticDestinations') -File | Remove-Item -Force -Confirm:$false
Get-ChildItem -Path (Join-Path $recentPath 'CustomDestinations') -File | Remove-Item -Force -Confirm:$false
Remove-Item -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs' -Recurse -Force -Confirm:$false

# --- 3. Restart Explorer so the jump-list changes take effect ---
Stop-Process -Name explorer -Force
Start-Process explorer.exe
Start-Sleep -Seconds 3   # give Explorer/shell COM time to come back up

# --- 4. Re-pin the folders that were pinned before ---
$shellApp = New-Object -ComObject Shell.Application
foreach ($path in $pinnedPaths) {
    if (Test-Path $path) {
        $parent = Split-Path $path -Parent
        $leaf = Split-Path $path -Leaf
        $folderItem = $shellApp.Namespace($parent).ParseName($leaf)
        if ($folderItem) {
            $pinVerb = $folderItem.Verbs() | Where-Object { ($_.Name -replace '&', '') -eq 'Pin to Quick access' }
            if ($pinVerb) { $pinVerb.DoIt() }
        }
    }
}
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($shellApp) | Out-Null

Write-Host "Recent items cleared; pinned folders restored." -ForegroundColor Green
