"""Main window UI for FaceFinder application"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Callable, List, Optional
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import freeze_support
import logging
from datetime import datetime

import face_recognition
import numpy as np
from PIL import Image

from config import ConfigManager
from ui.styles import ThemeManager
from ui.results_viewer import ResultsViewer

# Set up logging to file
log_file = Path(__file__).parent.parent / f"facefinder_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # Also output to console
    ]
)
logger = logging.getLogger(__name__)

# Suppress verbose debug output from PIL/Pillow
logging.getLogger('PIL').setLevel(logging.WARNING)


def _load_image_as_rgb_standalone(image_path: str, max_size: int = 1500) -> np.ndarray:
    """
    Load an image and convert to 8-bit RGB format for face_recognition.
    Standalone function for multiprocessing compatibility.
    """
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    arr = np.array(img, dtype=np.uint8)
    if not arr.flags['C_CONTIGUOUS']:
        arr = np.ascontiguousarray(arr)
    return arr


def _process_single_image_standalone(args) -> Optional[str]:
    """
    Process a single image and check for face match.
    Standalone function for multiprocessing compatibility.

    Args:
        args: Tuple of (file_path_str, ref_encoding, tolerance)

    Returns:
        File path string if match found, None otherwise
    """
    file_path_str, ref_encoding, tolerance = args
    try:
        image = _load_image_as_rgb_standalone(file_path_str)
        encodings = face_recognition.face_encodings(image)

        for enc in encodings:
            if face_recognition.compare_faces([ref_encoding], enc, tolerance=tolerance)[0]:
                return file_path_str
    except Exception as e:
        # Log errors but don't crash the worker
        pass
    return None


class MainWindow:
    """Main application window"""

    SUPPORTED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp')

    def __init__(self, root: tk.Tk, config_manager: ConfigManager, version: str):
        """
        Initialize main window

        Args:
            root: Tkinter root window
            config_manager: Configuration manager instance
            version: Application version string
        """
        self.root = root
        self.config = config_manager
        self.version = version

        # Search state
        self._search_cancelled = False
        self._search_thread: Optional[threading.Thread] = None
        self._explorer_process = None  # Track Explorer window for reuse

        # Set up window
        self.root.title(f"FaceFinder (V-{self.version})")
        self.root.geometry("700x600")
        self.root.configure(bg='#1a1a1a')
        self.root.minsize(700, 600)

        # Initialize theme
        self.style = ttk.Style()
        self.theme = ThemeManager(self.style, 'yellow_black')
        self.colors = self.theme.get_all_colors()
        self.fonts = self.theme.get_all_fonts()

        # UI Variables
        self.ref_path_var = tk.StringVar(value=self.config.get("default_reference_image", ""))
        self.folder_var = tk.StringVar(value=self.config.get("default_search_folder", ""))
        self.tolerance_var = tk.DoubleVar(value=self.config.get("tolerance", 0.6))
        self.recursive_var = tk.BooleanVar(value=self.config.get("recursive_search", True))

        # Build UI
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the main UI components"""
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill='both', expand=True, padx=15, pady=10)

        # Title
        self._create_title(main_frame)

        # Reference image input
        self._create_reference_input(main_frame)

        # Search folder input
        self._create_folder_input(main_frame)

        # Search options
        self._create_search_options(main_frame)

        # Buttons
        self._create_buttons(main_frame)

        # Progress bar
        self._create_progress_section(main_frame)

        # Results listbox
        self._create_results_listbox(main_frame)

    def _create_title(self, parent: ttk.Frame) -> None:
        """Create title label"""
        title_frame = ttk.Frame(parent, style='Dark.TFrame')
        title_frame.pack(fill='x', pady=(0, 15))

        ttk.Label(
            title_frame,
            text="FaceFinder",
            style='Dark.TLabel',
            font=self.fonts['title']
        ).pack(anchor='center')

        ttk.Label(
            title_frame,
            text="Search for matching faces in your image collection",
            style='Dark.TLabel',
            font=self.fonts['italic']
        ).pack(anchor='center')

    def _create_reference_input(self, parent: ttk.Frame) -> None:
        """Create reference image input"""
        frame = ttk.Frame(parent, style='Dark.TFrame')
        frame.pack(fill='x', pady=(0, 10))

        ttk.Label(frame, text="Reference Image:", style='Dark.TLabel').pack(anchor='w')

        input_frame = tk.Frame(frame, bg=self.colors['background'])
        input_frame.pack(fill='x', pady=(2, 0))

        entry = tk.Entry(
            input_frame,
            textvariable=self.ref_path_var,
            width=80,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['insert_cursor'],
            bd=1,
            relief='solid'
        )
        entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

        browse_btn = tk.Button(
            input_frame,
            text="...",
            command=self._browse_reference,
            bg=self.colors['button_bg'],
            fg=self.colors['button_fg'],
            relief='raised',
            bd=2,
            width=3,
            font=self.fonts['button'],
            activebackground=self.colors['button_active'],
            activeforeground=self.colors['button_fg']
        )
        browse_btn.pack(side='right')

    def _create_folder_input(self, parent: ttk.Frame) -> None:
        """Create search folder input"""
        frame = ttk.Frame(parent, style='Dark.TFrame')
        frame.pack(fill='x', pady=(0, 10))

        ttk.Label(frame, text="Search Folder:", style='Dark.TLabel').pack(anchor='w')

        input_frame = tk.Frame(frame, bg=self.colors['background'])
        input_frame.pack(fill='x', pady=(2, 0))

        entry = tk.Entry(
            input_frame,
            textvariable=self.folder_var,
            width=80,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['insert_cursor'],
            bd=1,
            relief='solid'
        )
        entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

        browse_btn = tk.Button(
            input_frame,
            text="...",
            command=self._browse_folder,
            bg=self.colors['button_bg'],
            fg=self.colors['button_fg'],
            relief='raised',
            bd=2,
            width=3,
            font=self.fonts['button'],
            activebackground=self.colors['button_active'],
            activeforeground=self.colors['button_fg']
        )
        browse_btn.pack(side='right')

    def _create_search_options(self, parent: ttk.Frame) -> None:
        """Create search options section"""
        section_frame = ttk.Frame(parent, style='Dark.TFrame')
        section_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(
            section_frame,
            text="Search Options",
            style='Dark.TLabel',
            font=self.fonts['bold']
        ).pack(anchor='w', pady=(0, 5))

        # Recursive search checkbox
        recursive_check = tk.Checkbutton(
            section_frame,
            text="Search subfolders recursively",
            variable=self.recursive_var,
            bg=self.colors['background'],
            fg=self.colors['foreground'],
            selectcolor=self.colors['input_bg'],
            activebackground=self.colors['background'],
            activeforeground=self.colors['foreground'],
            font=self.fonts['default']
        )
        recursive_check.pack(anchor='w', pady=(0, 5))

        # Tolerance slider
        tolerance_frame = ttk.Frame(section_frame, style='Dark.TFrame')
        tolerance_frame.pack(fill='x', pady=(5, 0))

        ttk.Label(
            tolerance_frame,
            text="Face Match Tolerance:",
            style='Dark.TLabel'
        ).pack(side='left')

        self.tolerance_label = ttk.Label(
            tolerance_frame,
            text=f"{self.tolerance_var.get():.2f}",
            style='Dark.TLabel',
            width=5
        )
        self.tolerance_label.pack(side='right')

        tolerance_scale = tk.Scale(
            section_frame,
            from_=0.1,
            to=1.0,
            resolution=0.05,
            orient='horizontal',
            variable=self.tolerance_var,
            command=self._on_tolerance_changed,
            bg=self.colors['background'],
            fg=self.colors['foreground'],
            highlightbackground=self.colors['background'],
            troughcolor='#333333',
            activebackground=self.colors['button_active'],
            length=300
        )
        tolerance_scale.pack(fill='x', pady=(2, 0))

        ttk.Label(
            section_frame,
            text="Lower = stricter matching, Higher = more lenient",
            style='Dark.TLabel',
            font=self.fonts['italic']
        ).pack(anchor='w')

    def _create_buttons(self, parent: ttk.Frame) -> None:
        """Create action buttons"""
        button_frame = ttk.Frame(parent, style='Dark.TFrame')
        button_frame.pack(fill='x', pady=(5, 10))

        # Search button
        self.search_button = tk.Button(
            button_frame,
            text="Search",
            command=self._start_search,
            bg=self.colors['button_bg'],
            fg=self.colors['button_fg'],
            font=self.fonts['button'],
            relief='raised',
            bd=2,
            padx=20,
            pady=10
        )
        self.search_button.pack(side='left', padx=(0, 10))

        # Cancel button
        self.cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel_search,
            bg='#666666',
            fg='#FFFFFF',
            font=self.fonts['button'],
            relief='raised',
            bd=2,
            padx=20,
            pady=10,
            state='disabled'
        )
        self.cancel_button.pack(side='left')

    def _create_progress_section(self, parent: ttk.Frame) -> None:
        """Create progress bar section"""
        progress_frame = ttk.Frame(parent, style='Dark.TFrame')
        progress_frame.pack(fill='x', pady=(5, 10))

        ttk.Label(
            progress_frame,
            text="Progress:",
            style='Dark.TLabel'
        ).pack(anchor='w')

        self.progress = ttk.Progressbar(
            progress_frame,
            orient='horizontal',
            mode='determinate',
            length=100,
            style='Yellow.Horizontal.TProgressbar'
        )
        self.progress.pack(fill='x', pady=(5, 0))

        self.progress_label = ttk.Label(
            progress_frame,
            text="Ready",
            style='Dark.TLabel',
            font=self.fonts['italic']
        )
        self.progress_label.pack(anchor='w', pady=(2, 0))

    def _create_results_listbox(self, parent: ttk.Frame) -> None:
        """Create results listbox with scrollbar"""
        results_frame = ttk.Frame(parent, style='Dark.TFrame')
        results_frame.pack(fill='both', expand=True)

        ttk.Label(results_frame, text="Results:", style='Dark.TLabel').pack(anchor='w')

        listbox_frame = ttk.Frame(results_frame, style='Dark.TFrame')
        listbox_frame.pack(fill='both', expand=True, pady=(5, 0))

        self.results_listbox = tk.Listbox(
            listbox_frame,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            selectbackground=self.colors['select_bg'],
            selectforeground=self.colors['select_fg'],
            bd=1,
            relief='solid',
            height=10
        )
        self.results_listbox.pack(side='left', fill='both', expand=True)

        scrollbar = tk.Scrollbar(
            listbox_frame,
            bg=self.colors['scrollbar_bg'],
            troughcolor=self.colors['scrollbar_trough']
        )
        scrollbar.pack(side='right', fill='y')

        self.results_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.results_listbox.yview)

        # Double-click to open file location
        self.results_listbox.bind('<Double-1>', self._on_result_double_click)

        # Initial message
        self._add_result("Ready to search...")

    def _browse_reference(self) -> None:
        """Handle reference image browse button"""
        initial_dir = ""
        current_path = self.ref_path_var.get()
        if current_path:
            initial_dir = str(Path(current_path).parent)

        file_path = filedialog.askopenfilename(
            title="Select Reference Image",
            initialdir=initial_dir if initial_dir else None,
            filetypes=[("Images", "*.jpg *.jpeg *.png"), ("All files", "*.*")]
        )
        if file_path:
            self.ref_path_var.set(file_path)
            self.config.set("default_reference_image", file_path)
            self.config.save()
            self._add_result(f"Reference image: {Path(file_path).name}")

    def _browse_folder(self) -> None:
        """Handle search folder browse button"""
        initial_dir = self.folder_var.get() or self.config.get("default_search_folder", "")
        folder = filedialog.askdirectory(
            title="Select Search Folder",
            initialdir=initial_dir if initial_dir else None
        )
        if folder:
            self.folder_var.set(folder)
            self.config.set("default_search_folder", folder)
            self.config.save()
            self._add_result(f"Search folder: {folder}")

    def _on_tolerance_changed(self, value: str) -> None:
        """Handle tolerance slider change"""
        self.tolerance_label.config(text=f"{float(value):.2f}")

    def _start_search(self) -> None:
        """Start the face search operation"""
        ref_path = self.ref_path_var.get().strip()
        folder = self.folder_var.get().strip()

        # Validation
        if not ref_path:
            messagebox.showerror("Error", "Please select a reference image")
            return

        if not folder:
            messagebox.showerror("Error", "Please select a search folder")
            return

        if not Path(ref_path).exists():
            messagebox.showerror("Error", "Reference image not found")
            return

        if not Path(folder).exists():
            messagebox.showerror("Error", "Search folder not found")
            return

        # Save settings
        self.config.set("tolerance", self.tolerance_var.get())
        self.config.set("recursive_search", self.recursive_var.get())
        self.config.save()

        # Reset UI
        self.results_listbox.delete(0, tk.END)
        self.progress['value'] = 0
        self._search_cancelled = False

        # Update button states
        self.search_button.config(state='disabled')
        self.cancel_button.config(state='normal')

        # Start search in background thread
        self._search_thread = threading.Thread(
            target=self._perform_search,
            args=(ref_path, folder),
            daemon=True
        )
        self._search_thread.start()

    def _cancel_search(self) -> None:
        """Cancel the current search operation"""
        self._search_cancelled = True
        self._add_result("Cancelling search...")

    def _load_image_as_rgb(self, image_path: str, max_size: int = 1500) -> np.ndarray:
        """
        Load an image and convert to 8-bit RGB format for face_recognition.

        Handles RGBA (PNG with transparency), CMYK, 16-bit, progressive JPEGs, and other formats.
        Resizes large images to improve performance.

        Args:
            image_path: Path to the image file
            max_size: Maximum dimension (width or height) for the image

        Returns:
            numpy array in 8-bit RGB format (contiguous memory layout)
        """
        img = Image.open(image_path)
        # Convert to RGB (handles RGBA, CMYK, L, P, etc.)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        # Resize if too large (improves performance significantly)
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        # Convert to numpy array and ensure 8-bit with contiguous memory
        # This also fixes issues with progressive JPEGs
        arr = np.array(img, dtype=np.uint8)
        # Ensure contiguous memory layout (fixes dlib compatibility issues)
        if not arr.flags['C_CONTIGUOUS']:
            arr = np.ascontiguousarray(arr)
        return arr

    # Number of worker processes for parallel processing
    NUM_WORKERS = 10

    def _perform_search(self, ref_path: str, folder: str) -> None:
        """
        Perform the face search operation using parallel processing.

        Args:
            ref_path: Path to reference image
            folder: Path to search folder
        """
        try:
            logger.info(f"=== Starting search ===")
            logger.info(f"Reference image: {ref_path}")
            logger.info(f"Search folder: {folder}")

            # Load reference image
            self._update_progress(0, 1, "Loading reference image...")
            self._add_result(f"Loading reference image: {ref_path}")

            logger.info("Loading reference image...")
            ref_image = self._load_image_as_rgb(ref_path)
            logger.info(f"Reference image loaded: shape={ref_image.shape}, dtype={ref_image.dtype}")

            self._add_result("Detecting face in reference image...")
            logger.info("Detecting face in reference image...")
            ref_encodings = face_recognition.face_encodings(ref_image)
            logger.info(f"Found {len(ref_encodings)} face(s) in reference image")

            if not ref_encodings:
                logger.warning("No face found in reference image")
                self._search_complete([], "No face found in reference image")
                return

            self._add_result(f"Found {len(ref_encodings)} face(s) in reference image")
            ref_encoding = ref_encodings[0]

            # Collect image files
            self._update_progress(0, 1, "Scanning for images...")
            self._add_result("Collecting image files...")
            logger.info("Collecting image files...")
            image_files = self._collect_image_files(folder)

            if not image_files:
                logger.warning("No images found in folder")
                self._search_complete([], "No images found in folder")
                return

            total = len(image_files)
            logger.info(f"Found {total} images to scan using {self.NUM_WORKERS} processes")
            self._add_result(f"Found {total} images to scan using {self.NUM_WORKERS} processes")

            # Search for matches using process pool (separate processes for dlib compatibility)
            matches: List[str] = []
            tolerance = self.tolerance_var.get()
            processed = 0
            logger.info(f"Starting parallel search with tolerance={tolerance}")

            # Prepare arguments for worker processes
            work_items = [(str(fp), ref_encoding, tolerance) for fp in image_files]

            with ProcessPoolExecutor(max_workers=self.NUM_WORKERS) as executor:
                # Submit all tasks
                logger.info("Submitting tasks to process pool...")
                futures = {executor.submit(_process_single_image_standalone, item): item[0] for item in work_items}
                logger.info(f"Submitted {len(futures)} tasks")

                # Process results as they complete
                logger.info("Processing results...")
                for future in as_completed(futures):
                    if self._search_cancelled:
                        logger.info("Search cancelled during processing")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

                    file_path = futures[future]
                    try:
                        result = future.result(timeout=60)  # 60 second timeout per image
                        processed += 1
                        if processed % 100 == 0:
                            logger.info(f"Progress: {processed}/{total}")
                        self._update_progress(processed, total, f"Scanned: {processed}/{total}")

                        if result:
                            matches.append(result)
                            self._add_result(f"MATCH: {result}")
                    except Exception as e:
                        logger.error(f"Error getting result for {file_path}: {e}")
                        processed += 1
                        self._update_progress(processed, total, f"Scanned: {processed}/{total}")

            if self._search_cancelled:
                logger.info(f"Search cancelled. Found {len(matches)} matches before cancellation")
                self._search_complete(matches, "Search cancelled")
                return

            logger.info(f"=== Search complete. Found {len(matches)} matches ===")
            self._search_complete(matches, None)

        except Exception as e:
            logger.exception(f"Search failed with error: {e}")
            self._search_complete([], f"Error: {e}")

    def _collect_image_files(self, folder: str) -> List[Path]:
        """
        Collect all image files from folder

        Args:
            folder: Path to search folder

        Returns:
            List of image file paths
        """
        folder_path = Path(folder)
        files: List[Path] = []

        if self.recursive_var.get():
            for ext in self.SUPPORTED_EXTENSIONS:
                files.extend(folder_path.rglob(f"*{ext}"))
                files.extend(folder_path.rglob(f"*{ext.upper()}"))
        else:
            for ext in self.SUPPORTED_EXTENSIONS:
                files.extend(folder_path.glob(f"*{ext}"))
                files.extend(folder_path.glob(f"*{ext.upper()}"))

        return files

    def _update_progress(self, current: int, total: int, message: str) -> None:
        """Update progress bar and label (thread-safe)"""
        def update():
            if total > 0:
                self.progress['value'] = (current / total) * 100
            self.progress_label.config(text=f"{current}/{total} - {message}")

        self.root.after(0, update)

    def _add_result(self, message: str) -> None:
        """Add a result message to the listbox (thread-safe)"""
        def update():
            self.results_listbox.insert(tk.END, message)
            self.results_listbox.see(tk.END)

        self.root.after(0, update)

    def _search_complete(self, matches: List[str], error: Optional[str]) -> None:
        """Handle search completion (thread-safe)"""
        def update():
            self.search_button.config(state='normal')
            self.cancel_button.config(state='disabled')
            self.progress['value'] = 100

            if error:
                self.progress_label.config(text=error)
                if not self._search_cancelled:
                    messagebox.showerror("Search Error", error)
            else:
                self.progress_label.config(text=f"Complete - Found {len(matches)} matches")
                self._add_result(f"\n--- Found {len(matches)} matches ---")

                if matches:
                    # Show results viewer with thumbnails
                    ResultsViewer(self.root, matches, self.colors)
                else:
                    messagebox.showinfo("Search Complete", "No matching faces found")

        self.root.after(0, update)

    def _on_result_double_click(self, event) -> None:
        """Handle double-click on result to open file location"""
        selection = self.results_listbox.curselection()
        if not selection:
            return

        item = self.results_listbox.get(selection[0])

        # Check if it's a match result
        if item.startswith("MATCH: "):
            file_path = item[7:]  # Remove "MATCH: " prefix
            path = Path(file_path)
            if path.exists():
                import subprocess
                # Close previous Explorer window if open
                if self._explorer_process is not None:
                    try:
                        self._explorer_process.terminate()
                    except Exception:
                        pass
                # Open folder and select file (Windows)
                self._explorer_process = subprocess.Popen(['explorer', '/select,', str(path)])
