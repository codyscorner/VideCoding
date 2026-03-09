Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Global variables
$script:isConnected = $true
$script:dailyUploadBytes = 0
$script:dailyDownloadBytes = 0
$script:lastUploadBytes = 0
$script:lastDownloadBytes = 0
$script:adapterName = $null
$script:hourlyUploadBytes = 0
$script:hourlyDownloadBytes = 0
$script:hourlySeconds = 0
$script:lastLogHour = -1
$script:lastKnownConnected = $null  # tracks external adapter state changes

# Resolve log folder next to the EXE (works for both compiled EXE and raw PS1)
$script:exeDir = [System.AppDomain]::CurrentDomain.BaseDirectory.TrimEnd('\')
$script:logDir = Join-Path $script:exeDir "Logs"

# Get the active network adapter
function Get-ActiveAdapter {
    $adapters = Get-NetAdapter | Where-Object {$_.Status -eq "Up" -and $_.InterfaceDescription -notlike "*Virtual*" -and $_.InterfaceDescription -notlike "*Bluetooth*"}
    if ($adapters) {
        return $adapters[0].Name
    }
    return $null
}

# Toggle network connection
function Set-NetworkAdapterState {
    param([string]$adapterName, [bool]$enable)
    
    try {
        if ($enable) {
            Enable-NetAdapter -Name $adapterName -Confirm:$false
        } else {
            Disable-NetAdapter -Name $adapterName -Confirm:$false
        }
        return $true
    } catch {
        [System.Windows.Forms.MessageBox]::Show("Error: Run PowerShell as Administrator", "Permission Required")
        return $false
    }
}

# Get network statistics
function Get-NetworkStats {
    param([string]$adapterName)
    
    if (-not $adapterName) { return @{Upload=0; Download=0} }
    
    try {
        $stats = Get-NetAdapterStatistics -Name $adapterName -ErrorAction SilentlyContinue
        if ($stats) {
            return @{
                Upload = $stats.SentBytes
                Download = $stats.ReceivedBytes
            }
        }
    } catch {}
    
    return @{Upload=0; Download=0}
}

# Ensure the Logs folder and today's log file exist
function Initialize-LogFile {
    if (-not (Test-Path $script:logDir)) {
        New-Item -ItemType Directory -Path $script:logDir -Force | Out-Null
    }
    $date    = Get-Date
    $logFile = Join-Path $script:logDir ("network_{0}.log" -f $date.ToString("yyyy-MM-dd"))
    if (-not (Test-Path $logFile)) {
        $header = "=== Network Control Log - {0} ===" -f $date.ToString("yyyy-MM-dd")
        Add-Content -Path $logFile -Value $header -Encoding UTF8
        Add-Content -Path $logFile -Value ""      -Encoding UTF8
    }
    return $logFile
}

# Append a single line to today's log
function Write-LogLine {
    param([string]$line)
    $logFile = Join-Path $script:logDir ("network_{0}.log" -f (Get-Date).ToString("yyyy-MM-dd"))
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

# Write an hourly stats line to the daily log file
function Write-HourlyLog {
    param(
        [long]$uploadBytes,
        [long]$downloadBytes,
        [int]$seconds,
        [string]$adapter
    )

    $date    = Get-Date
    $hour    = $date.ToString("HH:00")
    $upMB    = "{0:F3}" -f ($uploadBytes   / 1MB)
    $downMB  = "{0:F3}" -f ($downloadBytes / 1MB)

    if ($seconds -gt 0) {
        $avgUpKBs = "{0:F1}" -f ($uploadBytes   / 1KB / $seconds)
        $avgDnKBs = "{0:F1}" -f ($downloadBytes / 1KB / $seconds)
    } else {
        $avgUpKBs = "0.0"
        $avgDnKBs = "0.0"
    }

    $totalUpMB   = "{0:F3}" -f ($script:dailyUploadBytes   / 1MB)
    $totalDownMB = "{0:F3}" -f ($script:dailyDownloadBytes / 1MB)

    $hourLine  = "  [HOUR]  {0}  Hour={1}  Adapter={2}  Upload={3} MB  Download={4} MB  AvgUp={5} KB/s  AvgDown={6} KB/s" `
                 -f $date.ToString("yyyy-MM-dd HH:mm:ss"), $hour, $adapter, $upMB, $downMB, $avgUpKBs, $avgDnKBs
    $totalLine = "  [TOTAL] {0}  DayTotal  Adapter={1}  Upload={2} MB  Download={3} MB" `
                 -f $date.ToString("yyyy-MM-dd HH:mm:ss"), $adapter, $totalUpMB, $totalDownMB

    Write-LogLine $hourLine
    Write-LogLine $totalLine
    Write-LogLine ""
}

# Create the form
$form = New-Object System.Windows.Forms.Form
$form.Text = "Network Control v1.2"
$form.Size = New-Object System.Drawing.Size(512, 512)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedSingle"
$form.MaximizeBox = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(15, 23, 42)

# Title Label
$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Location = New-Object System.Drawing.Point(0, 30)
$titleLabel.Size = New-Object System.Drawing.Size(512, 40)
$titleLabel.Text = "Network Control"
$titleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 18, [System.Drawing.FontStyle]::Bold)
$titleLabel.ForeColor = [System.Drawing.Color]::FromArgb(226, 232, 240)
$titleLabel.TextAlign = "MiddleCenter"
$form.Controls.Add($titleLabel)

# Adapter Name Label
$adapterLabel = New-Object System.Windows.Forms.Label
$adapterLabel.Location = New-Object System.Drawing.Point(0, 72)
$adapterLabel.Size = New-Object System.Drawing.Size(512, 20)
$adapterLabel.Text = "Adapter: detecting..."
$adapterLabel.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$adapterLabel.ForeColor = [System.Drawing.Color]::FromArgb(100, 116, 139)
$adapterLabel.TextAlign = "MiddleCenter"
$form.Controls.Add($adapterLabel)

# Toggle Button
$toggleButton = New-Object System.Windows.Forms.Button
$toggleButton.Location = New-Object System.Drawing.Point(156, 100)
$toggleButton.Size = New-Object System.Drawing.Size(200, 200)
$toggleButton.Text = "ON"
$toggleButton.Font = New-Object System.Drawing.Font("Segoe UI", 32, [System.Drawing.FontStyle]::Bold)
$toggleButton.ForeColor = [System.Drawing.Color]::White
$toggleButton.BackColor = [System.Drawing.Color]::FromArgb(16, 185, 129)
$toggleButton.FlatStyle = "Flat"
$toggleButton.FlatAppearance.BorderSize = 0
$toggleButton.Cursor = [System.Windows.Forms.Cursors]::Hand

# Make button circular
$path = New-Object System.Drawing.Drawing2D.GraphicsPath
$path.AddEllipse(0, 0, 200, 200)
$toggleButton.Region = New-Object System.Drawing.Region($path)

$form.Controls.Add($toggleButton)

# Stats Panel
$statsY = 320

# Upload Speed
$uploadLabel = New-Object System.Windows.Forms.Label
$uploadLabel.Location = New-Object System.Drawing.Point(40, $statsY)
$uploadLabel.Size = New-Object System.Drawing.Size(200, 20)
$uploadLabel.Text = "Upload Speed"
$uploadLabel.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$uploadLabel.ForeColor = [System.Drawing.Color]::FromArgb(148, 163, 184)
$form.Controls.Add($uploadLabel)

$uploadValue = New-Object System.Windows.Forms.Label
$uploadValue.Location = New-Object System.Drawing.Point(280, $statsY)
$uploadValue.Size = New-Object System.Drawing.Size(192, 20)
$uploadValue.Text = "0.0000 MB/s"
$uploadValue.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$uploadValue.ForeColor = [System.Drawing.Color]::FromArgb(16, 185, 129)
$uploadValue.TextAlign = "MiddleRight"
$form.Controls.Add($uploadValue)

# Download Speed
$downloadLabel = New-Object System.Windows.Forms.Label
$downloadLabel.Location = New-Object System.Drawing.Point(40, ($statsY + 35))
$downloadLabel.Size = New-Object System.Drawing.Size(200, 20)
$downloadLabel.Text = "Download Speed"
$downloadLabel.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$downloadLabel.ForeColor = [System.Drawing.Color]::FromArgb(148, 163, 184)
$form.Controls.Add($downloadLabel)

$downloadValue = New-Object System.Windows.Forms.Label
$downloadValue.Location = New-Object System.Drawing.Point(280, ($statsY + 35))
$downloadValue.Size = New-Object System.Drawing.Size(192, 20)
$downloadValue.Text = "0.0000 MB/s"
$downloadValue.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$downloadValue.ForeColor = [System.Drawing.Color]::FromArgb(59, 130, 246)
$downloadValue.TextAlign = "MiddleRight"
$form.Controls.Add($downloadValue)

# Daily Upload
$dailyUploadLabel = New-Object System.Windows.Forms.Label
$dailyUploadLabel.Location = New-Object System.Drawing.Point(40, ($statsY + 70))
$dailyUploadLabel.Size = New-Object System.Drawing.Size(200, 20)
$dailyUploadLabel.Text = "Daily Upload"
$dailyUploadLabel.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$dailyUploadLabel.ForeColor = [System.Drawing.Color]::FromArgb(148, 163, 184)
$form.Controls.Add($dailyUploadLabel)

$dailyUploadValue = New-Object System.Windows.Forms.Label
$dailyUploadValue.Location = New-Object System.Drawing.Point(280, ($statsY + 70))
$dailyUploadValue.Size = New-Object System.Drawing.Size(192, 20)
$dailyUploadValue.Text = "0 MB"
$dailyUploadValue.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$dailyUploadValue.ForeColor = [System.Drawing.Color]::FromArgb(226, 232, 240)
$dailyUploadValue.TextAlign = "MiddleRight"
$form.Controls.Add($dailyUploadValue)

# Daily Download
$dailyDownloadLabel = New-Object System.Windows.Forms.Label
$dailyDownloadLabel.Location = New-Object System.Drawing.Point(40, ($statsY + 105))
$dailyDownloadLabel.Size = New-Object System.Drawing.Size(200, 20)
$dailyDownloadLabel.Text = "Daily Download"
$dailyDownloadLabel.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$dailyDownloadLabel.ForeColor = [System.Drawing.Color]::FromArgb(148, 163, 184)
$form.Controls.Add($dailyDownloadLabel)

$dailyDownloadValue = New-Object System.Windows.Forms.Label
$dailyDownloadValue.Location = New-Object System.Drawing.Point(280, ($statsY + 105))
$dailyDownloadValue.Size = New-Object System.Drawing.Size(192, 20)
$dailyDownloadValue.Text = "0 MB"
$dailyDownloadValue.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$dailyDownloadValue.ForeColor = [System.Drawing.Color]::FromArgb(226, 232, 240)
$dailyDownloadValue.TextAlign = "MiddleRight"
$form.Controls.Add($dailyDownloadValue)

# Button click event
$toggleButton.Add_Click({
    if (-not $script:adapterName) {
        [System.Windows.Forms.MessageBox]::Show("No active network adapter found", "Error")
        return
    }
    
    $script:isConnected = -not $script:isConnected
    
    if (Set-NetworkAdapterState -adapterName $script:adapterName -enable $script:isConnected) {
        if ($script:isConnected) {
            $toggleButton.Text = "ON"
            $toggleButton.BackColor = [System.Drawing.Color]::FromArgb(16, 185, 129)
            # Reset counters so the first tick after re-enable doesn't compute a bogus spike
            $script:lastUploadBytes   = 0
            $script:lastDownloadBytes = 0
        } else {
            $toggleButton.Text = "OFF"
            $toggleButton.BackColor = [System.Drawing.Color]::FromArgb(239, 68, 68)
        }
        $statusStr = if ($script:isConnected) { "Connected" } else { "Disconnected" }
        Write-LogLine ("  [STATUS] {0}  Adapter={1}  Status={2}  Source=UserToggle" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"), $script:adapterName, $statusStr)
        Write-LogLine ""
    } else {
        $script:isConnected = -not $script:isConnected  # Revert on failure
    }
})

# Timer for updating stats
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 1000  # 1 second

$timer.Add_Tick({
    $now  = Get-Date
    $hour = $now.Hour

    # Flush hourly log when the hour rolls over
    if ($script:lastLogHour -ge 0 -and $hour -ne $script:lastLogHour) {
        $adapterArg = if ($script:adapterName) { $script:adapterName } else { "unknown" }
        Write-HourlyLog `
            -uploadBytes   $script:hourlyUploadBytes `
            -downloadBytes $script:hourlyDownloadBytes `
            -seconds       $script:hourlySeconds `
            -adapter       $adapterArg
        $script:hourlyUploadBytes   = 0
        $script:hourlyDownloadBytes = 0
        $script:hourlySeconds       = 0

        # Reset daily totals at midnight
        if ($hour -eq 0) {
            $script:dailyUploadBytes   = 0
            $script:dailyDownloadBytes = 0
            $dailyUploadValue.Text   = "0.00 MB"
            $dailyDownloadValue.Text = "0.00 MB"
        }
    }
    $script:lastLogHour = $hour

    # Detect external adapter state changes (e.g., Windows re-enabling overnight)
    if ($script:adapterName) {
        $actualStatus = (Get-NetAdapter -Name $script:adapterName -ErrorAction SilentlyContinue).Status
        $actuallyUp   = ($actualStatus -eq "Up")
        if ($script:lastKnownConnected -ne $null -and $actuallyUp -ne $script:lastKnownConnected) {
            $script:isConnected = $actuallyUp
            if ($actuallyUp) {
                $toggleButton.Text     = "ON"
                $toggleButton.BackColor = [System.Drawing.Color]::FromArgb(16, 185, 129)
                $script:lastUploadBytes   = 0
                $script:lastDownloadBytes = 0
            } else {
                $toggleButton.Text     = "OFF"
                $toggleButton.BackColor = [System.Drawing.Color]::FromArgb(239, 68, 68)
            }
            $statusStr = if ($actuallyUp) { "Connected" } else { "Disconnected" }
            Write-LogLine ("  [STATUS] {0}  Adapter={1}  Status={2}  Source=ExternalChange" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"), $script:adapterName, $statusStr)
            Write-LogLine ""
        }
        $script:lastKnownConnected = $actuallyUp
    }

    if ($script:isConnected) {
        $stats = Get-NetworkStats -adapterName $script:adapterName

        if ($script:lastUploadBytes -gt 0) {
            $uploadDelta   = [Math]::Max(0, $stats.Upload   - $script:lastUploadBytes)
            $downloadDelta = [Math]::Max(0, $stats.Download - $script:lastDownloadBytes)

            $uploadSpeed   = $uploadDelta   / 1MB
            $downloadSpeed = $downloadDelta / 1MB

            $uploadValue.Text   = "{0:F4} MB/s" -f $uploadSpeed
            $downloadValue.Text = "{0:F4} MB/s" -f $downloadSpeed

            $script:dailyUploadBytes   += $uploadDelta
            $script:dailyDownloadBytes += $downloadDelta

            $script:hourlyUploadBytes   += $uploadDelta
            $script:hourlyDownloadBytes += $downloadDelta

            $dailyUploadValue.Text   = "{0:F2} MB" -f ($script:dailyUploadBytes   / 1MB)
            $dailyDownloadValue.Text = "{0:F2} MB" -f ($script:dailyDownloadBytes / 1MB)
        }

        $script:lastUploadBytes   = $stats.Upload
        $script:lastDownloadBytes = $stats.Download
        $script:hourlySeconds++
    } else {
        $uploadValue.Text   = "0.0000 MB/s"
        $downloadValue.Text = "0.0000 MB/s"
    }
})

# Initialize
$script:adapterName = Get-ActiveAdapter

if ($script:adapterName) {
    $adapterLabel.Text = "Adapter: $script:adapterName"
    # Detect actual current state rather than assuming connected
    $adapterStatus = (Get-NetAdapter -Name $script:adapterName -ErrorAction SilentlyContinue).Status
    $script:isConnected = ($adapterStatus -eq "Up")
    if ($script:isConnected) {
        $toggleButton.Text = "ON"
        $toggleButton.BackColor = [System.Drawing.Color]::FromArgb(16, 185, 129)
    } else {
        $toggleButton.Text = "OFF"
        $toggleButton.BackColor = [System.Drawing.Color]::FromArgb(239, 68, 68)
    }
} else {
    $adapterLabel.Text = "No adapter detected"
    [System.Windows.Forms.MessageBox]::Show("No active network adapter found. Some features may not work.", "Warning")
}

# Create log folder/file and write session start entry
Initialize-LogFile | Out-Null
$startAdapter = if ($script:adapterName) { $script:adapterName } else { "unknown" }
$startStatus = if ($script:isConnected) { "Connected" } else { "Disconnected" }
$startLine = "[START] {0}  Adapter={1}  Status={2}" `
             -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"), $startAdapter, $startStatus
Write-LogLine $startLine
Write-LogLine ""

# Start timer and show form
$timer.Start()
$form.Add_Shown({$form.Activate()})
[void]$form.ShowDialog()
$timer.Stop()

# Flush final partial-hour log on exit
$adapterArg = if ($script:adapterName) { $script:adapterName } else { "unknown" }
if ($script:lastLogHour -ge 0) {
    Write-HourlyLog `
        -uploadBytes   $script:hourlyUploadBytes `
        -downloadBytes $script:hourlyDownloadBytes `
        -seconds       $script:hourlySeconds `
        -adapter       $adapterArg
}
$stopLine = "[STOP]  {0}  Adapter={1}  SessionUpload={2} MB  SessionDownload={3} MB" `
            -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"), $adapterArg, `
               ("{0:F3}" -f ($script:dailyUploadBytes / 1MB)), `
               ("{0:F3}" -f ($script:dailyDownloadBytes / 1MB))
Write-LogLine $stopLine
Write-LogLine ""