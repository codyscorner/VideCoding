import os

def list_video_files(folder: str) -> list[str]:
    """
    List video files in a given folder.
    Returns a sorted list of full file paths for .mp4, .mkv, .avi, and .mov files.
    """
    allowed_extensions = {".mp4", ".mkv", ".avi", ".mov"}
    video_files = []
    
    try:
        entries = os.listdir(folder)
    except OSError:
        return []

    for entry in entries:
        full_path = os.path.join(folder, entry)
        if os.path.isfile(full_path):
            ext = os.path.splitext(entry)[1].lower()
            if ext in allowed_extensions:
                video_files.append(full_path)
                
    return sorted(video_files)
