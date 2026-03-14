"""
Video Frame Extractor GUI Application
Extracts specified frames from video files and saves them as PNG images.
"""

import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import cv2  # type: ignore
import os
from pathlib import Path
from datetime import datetime
import sys

# Ensure local imports work correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui.styles import ThemeManager  # type: ignore


class FrameExtractorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Video Frame Extractor v1.2")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        self.root.configure(bg='#1a1a1a')

        # Initialize theme
        self.style = ttk.Style()
        self.theme = ThemeManager(self.style, 'orange_black')
        self.colors = self.theme.get_all_colors()
        self.fonts = self.theme.get_all_fonts()

        # Variables
        self.source_dir = tk.StringVar()
        self.dest_dir = tk.StringVar()
        self.frame_number = tk.StringVar(value="1")
        self.video_extension = tk.StringVar(value=".mp4")
        self.status_listbox: tk.Listbox = None  # type: ignore

        self.setup_ui()

    def setup_ui(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10", style='Dark.TFrame')
        main_frame.grid(row=0, column=0, sticky=tk.NSEW)

        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="Frame Extractor",
                                font=self.fonts['title'], style='Dark.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Source Directory
        ttk.Label(main_frame, text="Source Directory:",
                  font=self.fonts['default'], style='Dark.TLabel').grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.source_dir,
                  width=50, style='Dark.TEntry').grid(row=1, column=1, sticky=tk.EW, pady=5, padx=5)
        
        tk.Button(main_frame, text="Browse...",
                   command=self.browse_source, bg=self.colors['button_bg'], fg=self.colors['button_fg'], font=self.fonts['button']).grid(row=1, column=2, pady=5)

        # Destination Directory
        ttk.Label(main_frame, text="Destination Directory:",
                  font=self.fonts['default'], style='Dark.TLabel').grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.dest_dir,
                  width=50, style='Dark.TEntry').grid(row=2, column=1, sticky=tk.EW, pady=5, padx=5)
        tk.Button(main_frame, text="Browse...",
                   command=self.browse_destination, bg=self.colors['button_bg'], fg=self.colors['button_fg'], font=self.fonts['button']).grid(row=2, column=2, pady=5)

        # Frame Number Selection
        ttk.Label(main_frame, text="Frame Number:",
                  font=self.fonts['default'], style='Dark.TLabel').grid(row=3, column=0, sticky=tk.W, pady=5)
        
        # Build frame options including "Last Frame"
        frame_values = ["Last Frame"] + [str(i) for i in range(1, 21)]
        frame_combo = ttk.Combobox(main_frame, textvariable=self.frame_number,
                                   values=frame_values, state="readonly", width=12, style='Dark.TCombobox')
        frame_combo.grid(row=3, column=1, sticky=tk.W, pady=5, padx=5)
        frame_combo.current(0)

        # Video Extension Filter
        ttk.Label(main_frame, text="Video Extension:",
                  font=self.fonts['default'], style='Dark.TLabel').grid(row=4, column=0, sticky=tk.W, pady=5)
        extension_combo = ttk.Combobox(main_frame, textvariable=self.video_extension,
                                       values=[".mp4", ".avi", ".mov", ".mkv", ".wmv",
                                              ".flv", ".webm", ".m4v"],
                                       state="readonly", width=10, style='Dark.TCombobox')
        extension_combo.grid(row=4, column=1, sticky=tk.W, pady=5, padx=5)
        extension_combo.current(0)

        # Process Button
        process_btn = tk.Button(main_frame, text="Extract Frames",
                                command=self.process_videos, bg=self.colors['button_bg'], fg=self.colors['button_fg'], font=self.fonts['button'])
        process_btn.grid(row=5, column=0, columnspan=3, pady=20)

        # Status Label
        ttk.Label(main_frame, text="Status Log:",
                  font=self.fonts['bold'], style='Dark.TLabel').grid(row=6, column=0, sticky=tk.W, pady=(10, 5))

        # Status Listbox with Scrollbar
        listbox_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        listbox_frame.grid(row=7, column=0, columnspan=3, sticky=tk.NSEW, pady=5)
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)

        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, style='Dark.Vertical.TScrollbar')
        self.status_listbox = tk.Listbox(listbox_frame, height=12,
                                         yscrollcommand=scrollbar.set,
                                         bg=self.colors['input_bg'], fg=self.colors['input_fg'],
                                         selectbackground=self.colors['select_bg'], selectforeground=self.colors['select_fg'],
                                         font=("Courier", 10))  # type: ignore
        scrollbar.config(command=self.status_listbox.yview)  # type: ignore

        self.status_listbox.grid(row=0, column=0, sticky=tk.NSEW)  # type: ignore
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        # Initial status message
        self.add_status("Application started. Please select directories.")

    def browse_source(self):
        """Open dialog to select source directory"""
        directory = filedialog.askdirectory(title="Select Source Directory")
        if directory:
            self.source_dir.set(directory)
            self.add_status(f"Source directory set: {directory}")

    def browse_destination(self):
        """Open dialog to select destination directory"""
        directory = filedialog.askdirectory(title="Select Destination Directory")
        if directory:
            self.dest_dir.set(directory)
            self.add_status(f"Destination directory set: {directory}")

    def add_status(self, message):
        """Add a status message to the listbox"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.status_listbox.insert(tk.END, formatted_message)  # type: ignore
        self.status_listbox.see(tk.END)  # type: ignore
        self.root.update_idletasks()

    def extract_frame(self, video_path, frame_num, output_path):
        """
        Extract a specific frame from a video file

        Args:
            video_path: Path to the video file
            frame_num: Frame number to extract (1-based)
            output_path: Path where the frame image will be saved

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                self.add_status(f"ERROR: Could not open video: {os.path.basename(video_path)}")
                return False

            # Get total frames
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            target_frame: int = 0
            if str(frame_num) == "Last Frame":
                # Some videos misreport total_frames by 1, target the last valid index
                target_frame = max(0, total_frames - 1)
            else:
                try:
                    target_frame = int(frame_num) - 1
                except ValueError:
                    target_frame = 0  # Fallback
            
            if target_frame >= total_frames and total_frames > 0:
                self.add_status(f"WARNING: Frame {target_frame + 1} exceeds total frames ({total_frames}) in {os.path.basename(video_path)}")
                cap.release()
                return False

            # Set frame position (0-based)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

            # Read the frame with fallback for last frame
            ret, frame = cap.read()
            
            # Fallback if the very last frame couldn't be read for some reason
            if not ret and str(frame_num) == "Last Frame" and target_frame > 0:
                # Try reading previous frames
                for i in range(1, min(5, int(target_frame) + 1)):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, int(target_frame) - i)
                    ret, frame = cap.read()
                    if ret:
                        self.add_status(f"Note: Had to decrement target frame by {i} to find valid last frame")
                        break
                        
            if ret:
                cv2.imwrite(output_path, frame)
                frame_label = "Last" if str(frame_num) == "Last Frame" else str(target_frame + 1)
                self.add_status(f"SUCCESS: Extracted frame {frame_label} from {os.path.basename(video_path)}")
                cap.release()
                return True
            else:
                frame_label = "Last" if str(frame_num) == "Last Frame" else str(target_frame + 1)
                self.add_status(f"ERROR: Could not read frame {frame_label} from {os.path.basename(video_path)}")
                cap.release()
                return False

        except Exception as e:
            self.add_status(f"ERROR: {str(e)}")
            return False

    def process_videos(self):
        """Process all video files in the source directory"""
        source = self.source_dir.get()
        dest = self.dest_dir.get()
        frame_num = self.frame_number.get()
        extension = self.video_extension.get()

        # Validate inputs
        if not source or not os.path.isdir(source):
            messagebox.showerror("Error", "Please select a valid source directory")
            self.add_status("ERROR: Invalid source directory")
            return

        if not dest:
            messagebox.showerror("Error", "Please select a destination directory")
            self.add_status("ERROR: No destination directory specified")
            return

        # Create destination directory if it doesn't exist
        if not os.path.isdir(dest):
            try:
                os.makedirs(dest, exist_ok=True)
                self.add_status(f"Created destination directory: {dest}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not create destination directory: {str(e)}")
                self.add_status(f"ERROR: Could not create destination directory: {str(e)}")
                return

        self.add_status("=" * 60)
        self.add_status(f"Starting batch processing...")
        self.add_status(f"Source: {source}")
        self.add_status(f"Destination: {dest}")
        self.add_status(f"Frame number: {frame_num}")
        self.add_status(f"Extension filter: {extension}")
        self.add_status("=" * 60)

        # Find all video files with the selected extension
        video_files = [f for f in os.listdir(source)
                      if f.lower().endswith(extension.lower())]

        if not video_files:
            self.add_status(f"WARNING: No {extension} files found in source directory")
            messagebox.showwarning("No Files", f"No {extension} files found in the source directory")
            return

        self.add_status(f"Found {len(video_files)} video file(s)")

        # Process each video file
        success_count = 0
        fail_count = 0

        for video_file in video_files:
            video_path = os.path.join(source, video_file)

            # Create output filename
            base_name = os.path.splitext(video_file)[0]
            if str(frame_num) == "Last Frame":
                output_filename = f"{base_name}_LastFrame.png"
            else:
                output_filename = f"{base_name}_frame_{frame_num}.png"
                
            output_path = os.path.join(dest, output_filename)

            self.add_status(f"Processing: {video_file}")

            if self.extract_frame(video_path, frame_num, output_path):
                success_count += 1
            else:
                fail_count += 1

        # Summary
        self.add_status("=" * 60)
        self.add_status(f"Processing complete!")
        self.add_status(f"Successful: {success_count} | Failed: {fail_count}")
        self.add_status("=" * 60)

        messagebox.showinfo("Complete",
                          f"Processing complete!\nSuccessful: {success_count}\nFailed: {fail_count}")


def main():
    root = tk.Tk()
    app = FrameExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
