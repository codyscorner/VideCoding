# Network Control

A Windows PowerShell GUI application for controlling network connectivity with real-time statistics monitoring and usage logging.

## Version 1.2.0

A lightweight network management tool that provides one-click network adapter control with comprehensive bandwidth monitoring and automatic hourly logging.

## Features

### Core Features
- **One-Click Network Toggle**: Instantly enable/disable network adapters
- **Real-time Statistics**: Monitor upload/download speeds in KB/s
- **Daily Usage Tracking**: Cumulative daily upload and download totals
- **Automatic Logging**: Hourly statistics saved to timestamped log files
- **Status Change Logging**: Records every network state change with source (user toggle or external)
- **Modern Dark UI**: Clean, minimalist interface with circular toggle button
- **Auto-Detection**: Automatically finds active network adapter
- **Session Persistence**: Tracks usage even when toggling connection
- **Daily Reset**: Daily totals reset to zero at midnight

### Monitoring Features
- **Upload Speed**: Real-time upload speed in KB/s (green indicator)
- **Download Speed**: Real-time download speed in KB/s (blue indicator)
- **Daily Upload**: Total uploaded data in MB for current day
- **Daily Download**: Total downloaded data in MB for current day
- **Hourly Logging**: Automatic logs with hourly averages and totals
- **Session Summary**: Total usage logged when application closes

## How It Works

1. **Adapter Detection**: Automatically detects active physical network adapter (excludes virtual and Bluetooth adapters)
2. **State Detection**: Detects current connection state (ON/OFF) on startup
3. **Real-time Monitoring**: Updates statistics every second using `Get-NetAdapterStatistics`
4. **External Change Detection**: Timer checks actual adapter state each second and logs any changes made outside the app (e.g., Windows re-enabling the adapter overnight)
5. **Hourly Logging**: Writes comprehensive statistics to log file at the top of each hour
6. **Midnight Reset**: Daily totals and UI counters reset to zero when the day rolls over
7. **Session Tracking**: Maintains accurate counters even when toggling connection

## UI Components

- **Circular Toggle Button**: Large 200x200px button showing ON (green) or OFF (red) state
- **Adapter Display**: Shows the name of the active network adapter
- **Live Statistics Panel**:
  - Upload Speed (KB/s)
  - Download Speed (KB/s)
  - Daily Upload (MB)
  - Daily Download (MB)
- **Dark Theme**: Professional slate blue background with color-coded stats

## Log Files

Logs are automatically saved to `Logs/` folder next to the executable.

### Log File Naming
```
Logs/network_YYYY-MM-DD.log
```

### Log Entry Types

#### Session Start
```
[START] 2026-02-28 14:30:00  Adapter=Ethernet  Status=Connected
```

#### Hourly Statistics
```
[HOUR]  2026-02-28 15:00:00  Hour=15:00  Adapter=Ethernet  Upload=42.567 MB  Download=156.234 MB  AvgUp=12.3 KB/s  AvgDown=45.6 KB/s
[TOTAL] 2026-02-28 15:00:00  DayTotal  Adapter=Ethernet  Upload=156.789 MB  Download=512.345 MB
```

#### Network Status Change
```
[STATUS] 2026-03-09 07:34:12  Adapter=Ethernet  Status=Connected  Source=ExternalChange
[STATUS] 2026-03-09 23:15:00  Adapter=Ethernet  Status=Disconnected  Source=UserToggle
```

#### Session End
```
[STOP]  2026-02-28 16:45:00  Adapter=Ethernet  SessionUpload=85.234 MB  SessionDownload=289.456 MB
```

## Project Structure

```
NetworkToggleStatus/
├── Network_toggle_status.ps1   # Main PowerShell script
├── NetworkControl.exe           # Compiled executable (PS2EXE)
├── Logs/                        # Auto-generated log directory
│   └── network_YYYY-MM-DD.log  # Daily log files
└── README.md                    # This file
```

## Usage

### Running the Application

#### Option 1: Compiled Executable (Recommended)
```powershell
# Requires Administrator privileges for network control
NetworkControl.exe
```

#### Option 2: PowerShell Script
```powershell
# Run as Administrator
powershell -ExecutionPolicy Bypass -File Network_toggle_status.ps1
```

### Basic Workflow

1. **Launch Application**: Run as Administrator
2. **Check Adapter**: Verify correct adapter is detected in the UI
3. **Monitor Stats**: View real-time upload/download speeds
4. **Toggle Network**: Click the circular button to enable/disable connection
   - Green = ON (Connected)
   - Red = OFF (Disconnected)
5. **Review Logs**: Check `Logs/` folder for historical usage data

## Requirements

### For Compiled Executable
- Windows 10 or later
- Administrator privileges (required for enabling/disabling adapters)
- .NET Framework (included with Windows)

### For PowerShell Script
- Windows PowerShell 5.1+
- Administrator privileges
- No additional modules required (uses built-in cmdlets)

### For Compiling Executable
- PS2EXE module
```powershell
Install-Module -Name ps2exe
Invoke-ps2exe .\Network_toggle_status.ps1 .\NetworkControl.exe -noConsole -requireAdmin
```

## Technical Details

### Network Adapter Selection
The application automatically selects the first active physical adapter using:
```powershell
Get-NetAdapter | Where-Object {
    $_.Status -eq "Up" -and
    $_.InterfaceDescription -notlike "*Virtual*" -and
    $_.InterfaceDescription -notlike "*Bluetooth*"
}
```

### Statistics Calculation
- **Speed**: Calculated as delta bytes per second: `(current_bytes - previous_bytes) / 1024`
- **Daily Totals**: Cumulative sum of all deltas since application start
- **Hourly Averages**: Total hourly bytes divided by seconds in that hour

### Color Scheme
- Background: `#0F172A` (Slate 900)
- Title Text: `#E2E8F0` (Slate 200)
- Upload Speed: `#10B981` (Emerald 500)
- Download Speed: `#3B82F6` (Blue 500)
- ON Button: `#10B981` (Emerald 500)
- OFF Button: `#EF4444` (Red 500)

## Use Cases

- **Bandwidth Monitoring**: Track daily and hourly network usage
- **Connection Control**: Quickly disable/enable network for troubleshooting
- **Data Usage Tracking**: Monitor upload/download patterns
- **Network Troubleshooting**: Test connectivity by toggling adapter state
- **Parental Controls**: Manual control over network access
- **Usage Auditing**: Comprehensive logs for bandwidth analysis

## Limitations

- Requires Administrator privileges to toggle network adapters
- Only controls the first detected active physical adapter
- Statistics reset when application is closed
- Daily totals reset at midnight automatically
- Does not block specific applications or ports

## Future Enhancements

- [ ] Multi-adapter support with dropdown selection
- [ ] Persistent daily statistics across sessions
- [ ] Bandwidth usage graphs/charts
- [ ] Alert notifications for high usage
- [ ] Scheduled auto-toggle (e.g., disable at night)
- [ ] Per-application bandwidth monitoring
- [ ] Export usage reports to CSV
- [ ] Dark/light theme toggle
- [ ] System tray minimization
- [ ] Customizable logging intervals

## Troubleshooting

### "Permission Required" Error
- **Solution**: Run as Administrator (right-click → Run as Administrator)

### "No active network adapter found"
- **Solution**: Ensure a physical network adapter is connected and enabled
- Check that it's not a virtual or Bluetooth adapter

### Statistics Not Updating
- **Solution**: Ensure network connection is active (ON state)
- Verify adapter name is correctly displayed in UI

### Log Files Not Created
- **Solution**: Ensure write permissions in application directory
- Check Windows permissions for creating `Logs/` folder

## License

MIT License

## Author

**Cody's Corner** - [@codyscorner](https://github.com/codyscorner)

## Contributing

Contributions with AI assistance by Claude (Anthropic)

## Version History

### v1.2.0 (March 2026)
- Fix: Daily totals now correctly reset to zero at midnight
- Add: `[STATUS]` log entries on every network state change
- Add: Detection of external adapter state changes (e.g., Windows re-enabling overnight) with `Source=ExternalChange`
- Add: User-initiated toggles logged with `Source=UserToggle`

### v1.0.0 (February 2026)
- Initial release
- One-click network adapter toggle
- Real-time bandwidth monitoring
- Automatic hourly logging
- Dark theme UI with circular toggle
- Session tracking and statistics
- Auto-detection of active network adapter
