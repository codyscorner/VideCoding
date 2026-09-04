# Lists Quick Access entries and shows whether each is actually PINNED
# (vs. just a "frequent folder" that shows up automatically).
# Detection works by checking whether the item exposes an "Unpin from Quick access"
# verb -- only pinned items have it.

$shellApp = New-Object -ComObject Shell.Application
$quickAccess = $shellApp.Namespace('shell:::{679f85cb-0220-4080-b29b-5540cc05aab6}')

$results = foreach ($item in $quickAccess.Items()) {
    $verbNames = $item.Verbs() | ForEach-Object { $_.Name -replace '&', '' }
    $isPinned = $verbNames -contains 'Unpin from Quick access'

    [PSCustomObject]@{
        Name   = $item.Name
        Path   = $item.Path
        Pinned = $isPinned
    }
}

$results | Sort-Object Pinned -Descending | Format-Table -AutoSize
