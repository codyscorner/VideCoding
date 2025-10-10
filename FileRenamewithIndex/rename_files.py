import os
import sys

def rename_files_in_folder(folder_path):
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist.")
        return
    
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    
    if not files:
        print("No files found in the folder.")
        return
    
    files.sort()
    
    for index, filename in enumerate(files, start=1):
        file_path = os.path.join(folder_path, filename)

        name, ext = os.path.splitext(filename)

        new_filename = f"ComfyUI_Video_{index:05d}{ext}"
        new_file_path = os.path.join(folder_path, new_filename)

        if filename == new_filename:
            continue

        try:
            os.rename(file_path, new_file_path)
            print(f"Renamed: {filename} -> {new_filename}")
        except OSError as e:
            print(f"Error renaming {filename}: {e}")

if __name__ == "__main__":
    folder_path = r"P:\AI\Cumfyui\output\video\Archive"
    
    print(f"Renaming files in: {folder_path}")
    print("Files will be renamed to format: ComfyUI_Video_#####.extension")
        
    rename_files_in_folder(folder_path)
    print("Renaming complete!")
    