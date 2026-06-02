$sourceFolder = "E:\For Remote processing"
$batchSize    = 15

$images = Get-ChildItem -Path $sourceFolder -File |
          Where-Object { $_.Extension -match '^\.(jpg|jpeg|png|webp|bmp|tiff|tif)$' } |
          Sort-Object Name

if ($images.Count -eq 0) {
    Write-Host "No image files found in $sourceFolder"
    exit
}

$batchNum = 1
$count    = 0

foreach ($file in $images) {
    if ($count % $batchSize -eq 0) {
        $batchFolder = Join-Path $sourceFolder ("batch_{0:D3}" -f $batchNum)
        New-Item -ItemType Directory -Path $batchFolder -Force | Out-Null
        Write-Host "Created $batchFolder"
        $batchNum++
    }
    Move-Item -Path $file.FullName -Destination $batchFolder
    $count++
}

Write-Host ""
Write-Host "Done — $count file(s) split into $($batchNum - 1) batch folder(s)."
