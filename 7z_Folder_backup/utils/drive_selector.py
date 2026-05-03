import ctypes
import string


def get_available_drives():
    result = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drive = f"{letter}:\\"
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
            if drive_type in (2, 3, 4):  # Removable, Fixed, Network
                label = _get_label(drive)
                free_gb = _get_free_gb(drive)
                result.append((drive, label, free_gb))
        bitmask >>= 1
    return result


def _get_label(drive):
    buf = ctypes.create_unicode_buffer(256)
    try:
        ctypes.windll.kernel32.GetVolumeInformationW(
            drive, buf, 256, None, None, None, None, 0
        )
    except Exception:
        pass
    return buf.value or "Local Disk"


def _get_free_gb(drive):
    free_bytes = ctypes.c_ulonglong(0)
    try:
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            drive, ctypes.byref(free_bytes), None, None
        )
        return round(free_bytes.value / (1024 ** 3), 1)
    except Exception:
        return 0.0
