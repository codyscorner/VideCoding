"""
Image Resizer - Modern GUI Application
A tool to batch resize images with preset dimensions and quality options.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
from tkinter import colorchooser
import os
import threading


# Color scheme - Blue theme
COLORS = {
    "primary": "#1a73e8",
    "primary_hover": "#1557b0",
    "secondary": "#4285f4",
    "background": "#1a1a2e",
    "surface": "#16213e",
    "surface_light": "#1f3460",
    "text": "#ffffff",
    "text_secondary": "#a0a0a0",
    "success": "#34a853",
    "error": "#ea4335",
    "border": "#2d4a7c"
}

# Dimension presets (width x height) - Aspect ratio based
DIMENSION_PRESETS = {
    "Custom": None,
    "Square (1:1)": (1024, 1024),
    "Widescreen (16:9)": (1920, 1080),
    "Art Print (5:4)": (1280, 1024),
    "Classic (4:3)": (1600, 1200),
    "Photo (3:2)": (1800, 1200),
    "Book (2:3)": (800, 1200),
    "Portrait (3:4)": (900, 1200),
    "Vertical (4:5)": (960, 1200),
    "Mobile (9:16)": (1080, 1920),
    "Ultrawide (21:9)": (2560, 1080),
}

# Output format options
OUTPUT_FORMATS = ["Original", "PNG", "JPEG", "WEBP", "BMP"]

# Padding color presets
PADDING_COLORS = {
    "Black": "#000000",
    "White": "#FFFFFF",
    "Gray": "#808080",
    "Transparent": None,  # Only works with PNG/WEBP
    "Custom...": "custom"
}


class ImageResizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("Image Resizer")
        self.geometry("700x600")
        self.minsize(600, 500)

        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.configure(fg_color=COLORS["background"])

        # Processing flag
        self.is_processing = False

        # Custom padding color (default black)
        self.custom_padding_color = "#000000"

        # Build UI
        self._create_ui()

    def _create_ui(self):
        """Create the main user interface."""
        # Main container with padding
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Image Resizer",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["primary"]
        )
        self.title_label.pack(pady=(0, 20))

        # Settings frame
        self.settings_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["surface"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"]
        )
        self.settings_frame.pack(fill="x", pady=(0, 15))

        # --- Folder Selection ---
        self._create_folder_section()

        # --- Dimensions Section ---
        self._create_dimensions_section()

        # --- Format and Quality Section ---
        self._create_format_quality_section()

        # --- Start Button ---
        self.start_button = ctk.CTkButton(
            self.main_frame,
            text="Start Resizing",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            command=self._start_resize
        )
        self.start_button.pack(fill="x", pady=(5, 15))

        # --- Progress Bar ---
        self.progress_bar = ctk.CTkProgressBar(
            self.main_frame,
            progress_color=COLORS["secondary"],
            fg_color=COLORS["surface"]
        )
        self.progress_bar.pack(fill="x", pady=(0, 10))
        self.progress_bar.set(0)

        # --- Feedback List ---
        self._create_feedback_section()

    def _create_folder_section(self):
        """Create folder selection section."""
        folder_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        folder_frame.pack(fill="x", padx=15, pady=15)

        folder_label = ctk.CTkLabel(
            folder_frame,
            text="Source Folder:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text"]
        )
        folder_label.pack(anchor="w")

        input_frame = ctk.CTkFrame(folder_frame, fg_color="transparent")
        input_frame.pack(fill="x", pady=(5, 0))

        self.folder_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Select a folder containing images...",
            height=38,
            fg_color=COLORS["surface_light"],
            border_color=COLORS["border"],
            text_color=COLORS["text"]
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_button = ctk.CTkButton(
            input_frame,
            text="Browse",
            width=100,
            height=38,
            fg_color=COLORS["secondary"],
            hover_color=COLORS["primary"],
            command=self._browse_folder
        )
        browse_button.pack(side="right")

    def _create_dimensions_section(self):
        """Create dimensions selection section."""
        dim_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        dim_frame.pack(fill="x", padx=15, pady=(0, 15))

        dim_label = ctk.CTkLabel(
            dim_frame,
            text="Output Dimensions:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text"]
        )
        dim_label.pack(anchor="w")

        # Preset dropdown and custom inputs row
        controls_frame = ctk.CTkFrame(dim_frame, fg_color="transparent")
        controls_frame.pack(fill="x", pady=(5, 0))

        # Preset dropdown
        self.preset_var = ctk.StringVar(value="512 x 512 (Square)")
        self.preset_dropdown = ctk.CTkComboBox(
            controls_frame,
            values=list(DIMENSION_PRESETS.keys()),
            variable=self.preset_var,
            width=200,
            height=38,
            fg_color=COLORS["surface_light"],
            border_color=COLORS["border"],
            button_color=COLORS["secondary"],
            button_hover_color=COLORS["primary"],
            dropdown_fg_color=COLORS["surface"],
            command=self._on_preset_change
        )
        self.preset_dropdown.pack(side="left", padx=(0, 15))

        # Width input
        width_label = ctk.CTkLabel(
            controls_frame,
            text="W:",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"]
        )
        width_label.pack(side="left", padx=(0, 5))

        self.width_entry = ctk.CTkEntry(
            controls_frame,
            width=80,
            height=38,
            fg_color=COLORS["surface_light"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            justify="center"
        )
        self.width_entry.pack(side="left", padx=(0, 10))
        self.width_entry.insert(0, "512")

        # Height input
        height_label = ctk.CTkLabel(
            controls_frame,
            text="H:",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"]
        )
        height_label.pack(side="left", padx=(0, 5))

        self.height_entry = ctk.CTkEntry(
            controls_frame,
            width=80,
            height=38,
            fg_color=COLORS["surface_light"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            justify="center"
        )
        self.height_entry.pack(side="left")
        self.height_entry.insert(0, "512")

        # --- Resize Mode Section ---
        mode_frame = ctk.CTkFrame(dim_frame, fg_color="transparent")
        mode_frame.pack(fill="x", pady=(10, 0))

        mode_label = ctk.CTkLabel(
            mode_frame,
            text="Resize Mode:",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"]
        )
        mode_label.pack(side="left", padx=(0, 10))

        # Resize mode segmented button
        self.resize_mode_var = ctk.StringVar(value="Stretch")
        self.resize_mode = ctk.CTkSegmentedButton(
            mode_frame,
            values=["Stretch", "Fit", "Fit + Pad"],
            variable=self.resize_mode_var,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["surface_light"],
            selected_color=COLORS["primary"],
            selected_hover_color=COLORS["primary_hover"],
            unselected_color=COLORS["surface_light"],
            unselected_hover_color=COLORS["surface"],
            command=self._on_resize_mode_change
        )
        self.resize_mode.pack(side="left", padx=(0, 15))

        # Padding color section (initially hidden)
        self.padding_frame = ctk.CTkFrame(mode_frame, fg_color="transparent")

        padding_label = ctk.CTkLabel(
            self.padding_frame,
            text="Pad Color:",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"]
        )
        padding_label.pack(side="left", padx=(0, 5))

        self.padding_color_var = ctk.StringVar(value="Black")
        self.padding_dropdown = ctk.CTkComboBox(
            self.padding_frame,
            values=list(PADDING_COLORS.keys()),
            variable=self.padding_color_var,
            width=120,
            height=32,
            fg_color=COLORS["surface_light"],
            border_color=COLORS["border"],
            button_color=COLORS["secondary"],
            button_hover_color=COLORS["primary"],
            dropdown_fg_color=COLORS["surface"],
            command=self._on_padding_color_change
        )
        self.padding_dropdown.pack(side="left", padx=(0, 5))

        # Color preview swatch
        self.color_swatch = ctk.CTkButton(
            self.padding_frame,
            text="",
            width=32,
            height=32,
            fg_color="#000000",
            hover_color="#000000",
            border_width=2,
            border_color=COLORS["border"],
            command=self._pick_custom_color
        )
        self.color_swatch.pack(side="left")

    def _create_format_quality_section(self):
        """Create format and quality section."""
        fq_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        fq_frame.pack(fill="x", padx=15, pady=(0, 15))

        # Two columns
        left_frame = ctk.CTkFrame(fq_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="x", expand=True)

        right_frame = ctk.CTkFrame(fq_frame, fg_color="transparent")
        right_frame.pack(side="right", fill="x", expand=True)

        # Output format
        format_label = ctk.CTkLabel(
            left_frame,
            text="Output Format:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text"]
        )
        format_label.pack(anchor="w")

        self.format_var = ctk.StringVar(value="Original")
        self.format_dropdown = ctk.CTkComboBox(
            left_frame,
            values=OUTPUT_FORMATS,
            variable=self.format_var,
            width=150,
            height=38,
            fg_color=COLORS["surface_light"],
            border_color=COLORS["border"],
            button_color=COLORS["secondary"],
            button_hover_color=COLORS["primary"],
            dropdown_fg_color=COLORS["surface"]
        )
        self.format_dropdown.pack(anchor="w", pady=(5, 0))

        # Quality slider
        quality_label = ctk.CTkLabel(
            right_frame,
            text="Quality:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text"]
        )
        quality_label.pack(anchor="w")

        quality_control = ctk.CTkFrame(right_frame, fg_color="transparent")
        quality_control.pack(fill="x", pady=(5, 0))

        self.quality_slider = ctk.CTkSlider(
            quality_control,
            from_=10,
            to=100,
            number_of_steps=90,
            progress_color=COLORS["primary"],
            button_color=COLORS["secondary"],
            button_hover_color=COLORS["primary"],
            command=self._on_quality_change
        )
        self.quality_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.quality_slider.set(85)

        self.quality_label = ctk.CTkLabel(
            quality_control,
            text="85%",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
            width=40
        )
        self.quality_label.pack(side="right")

    def _create_feedback_section(self):
        """Create feedback/log section."""
        feedback_label = ctk.CTkLabel(
            self.main_frame,
            text="Processing Log:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text"]
        )
        feedback_label.pack(anchor="w", pady=(0, 5))

        # Feedback text box (using textbox for better scrolling)
        self.feedback_text = ctk.CTkTextbox(
            self.main_frame,
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=12)
        )
        self.feedback_text.pack(fill="both", expand=True)
        self.feedback_text.configure(state="disabled")

    def _browse_folder(self):
        """Open folder browser dialog."""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)

    def _on_preset_change(self, selection):
        """Handle preset dropdown change."""
        preset = DIMENSION_PRESETS.get(selection)
        if preset:
            self.width_entry.delete(0, "end")
            self.width_entry.insert(0, str(preset[0]))
            self.height_entry.delete(0, "end")
            self.height_entry.insert(0, str(preset[1]))

    def _on_resize_mode_change(self, mode):
        """Show/hide padding options based on resize mode."""
        if mode == "Fit + Pad":
            self.padding_frame.pack(side="left")
        else:
            self.padding_frame.pack_forget()

    def _on_padding_color_change(self, selection):
        """Handle padding color dropdown change."""
        if selection == "Custom...":
            self._pick_custom_color()
        elif selection == "Transparent":
            self.color_swatch.configure(fg_color=COLORS["surface"], hover_color=COLORS["surface"])
        else:
            color = PADDING_COLORS.get(selection, "#000000")
            self.custom_padding_color = color
            self.color_swatch.configure(fg_color=color, hover_color=color)

    def _pick_custom_color(self):
        """Open color picker dialog."""
        color = colorchooser.askcolor(
            initialcolor=self.custom_padding_color,
            title="Choose Padding Color"
        )
        if color[1]:  # color[1] is the hex string
            self.custom_padding_color = color[1]
            self.color_swatch.configure(fg_color=color[1], hover_color=color[1])
            self.padding_color_var.set("Custom...")

    def _get_padding_color(self):
        """Get the current padding color as RGB tuple or None for transparent."""
        selection = self.padding_color_var.get()
        if selection == "Transparent":
            return None
        elif selection == "Custom...":
            hex_color = self.custom_padding_color
        else:
            hex_color = PADDING_COLORS.get(selection, "#000000")

        # Convert hex to RGB tuple
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _on_quality_change(self, value):
        """Update quality label when slider changes."""
        self.quality_label.configure(text=f"{int(value)}%")

    def _log(self, message, clear=False):
        """Add message to feedback log."""
        self.feedback_text.configure(state="normal")
        if clear:
            self.feedback_text.delete("1.0", "end")
        self.feedback_text.insert("end", message + "\n")
        self.feedback_text.see("end")
        self.feedback_text.configure(state="disabled")

    def _start_resize(self):
        """Start the resize operation in a separate thread."""
        if self.is_processing:
            return

        folder_path = self.folder_entry.get().strip()
        if not folder_path:
            messagebox.showerror("Error", "Please select a folder.")
            return

        if not os.path.isdir(folder_path):
            messagebox.showerror("Error", "Selected folder does not exist.")
            return

        # Validate dimensions
        try:
            width = int(self.width_entry.get())
            height = int(self.height_entry.get())
            if width <= 0 or height <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid dimensions (positive integers).")
            return

        # Start processing in thread
        self.is_processing = True
        self.start_button.configure(state="disabled", text="Processing...")

        thread = threading.Thread(
            target=self._resize_images,
            args=(folder_path, width, height),
            daemon=True
        )
        thread.start()

    def _resize_images(self, folder_path, width, height):
        """Resize images in the selected folder."""
        try:
            output_folder = os.path.join(folder_path, "resized_images")
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            resize_mode = self.resize_mode_var.get()
            self.after(0, lambda: self._log(f"Output folder: {output_folder}", clear=True))
            self.after(0, lambda: self._log(f"Target size: {width} x {height} | Mode: {resize_mode}"))
            if resize_mode == "Fit + Pad":
                pad_color_name = self.padding_color_var.get()
                self.after(0, lambda: self._log(f"Padding color: {pad_color_name}"))
            self.after(0, lambda: self._log("-" * 50))

            # Get image files
            supported_formats = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff')
            image_files = [f for f in os.listdir(folder_path)
                          if f.lower().endswith(supported_formats)]

            if not image_files:
                self.after(0, lambda: self._log("No images found in the selected folder."))
                self.after(0, self._processing_complete)
                return

            total = len(image_files)
            self.after(0, lambda: self._log(f"Found {total} image(s) to process.\n"))

            quality = int(self.quality_slider.get())
            output_format = self.format_var.get()
            padding_color = self._get_padding_color()

            processed = 0
            errors = 0

            for i, filename in enumerate(image_files):
                try:
                    img_path = os.path.join(folder_path, filename)
                    img = Image.open(img_path)

                    # Calculate dimensions based on resize mode
                    if resize_mode == "Stretch":
                        # Simple stretch to exact dimensions
                        img_resized = img.resize((width, height), Image.Resampling.LANCZOS)

                    elif resize_mode == "Fit":
                        # Fit within dimensions, maintain aspect ratio (may be smaller)
                        img.thumbnail((width, height), Image.Resampling.LANCZOS)
                        img_resized = img

                    elif resize_mode == "Fit + Pad":
                        # Fit within dimensions, then pad to exact size
                        img_copy = img.copy()
                        img_copy.thumbnail((width, height), Image.Resampling.LANCZOS)

                        # Create new image with padding
                        if padding_color is None:
                            # Transparent padding - use RGBA
                            img_resized = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                        else:
                            # Solid color padding
                            if img_copy.mode == 'RGBA':
                                img_resized = Image.new('RGBA', (width, height), padding_color + (255,))
                            else:
                                img_resized = Image.new('RGB', (width, height), padding_color)

                        # Calculate position to center the image
                        x_offset = (width - img_copy.width) // 2
                        y_offset = (height - img_copy.height) // 2

                        # Paste the resized image onto the padded canvas
                        if img_copy.mode == 'RGBA':
                            img_resized.paste(img_copy, (x_offset, y_offset), img_copy)
                        else:
                            img_resized.paste(img_copy, (x_offset, y_offset))
                    else:
                        img_resized = img.resize((width, height), Image.Resampling.LANCZOS)

                    # Determine output filename and format
                    name, ext = os.path.splitext(filename)
                    if output_format == "Original":
                        save_ext = ext
                    else:
                        save_ext = f".{output_format.lower()}"

                    save_filename = f"{name}{save_ext}"
                    save_path = os.path.join(output_folder, save_filename)

                    # Handle format-specific saving
                    if save_ext.lower() in ['.jpg', '.jpeg']:
                        # Convert to RGB for JPEG (no alpha)
                        if img_resized.mode in ('RGBA', 'P'):
                            img_resized = img_resized.convert('RGB')
                        img_resized.save(save_path, quality=quality, optimize=True)
                    elif save_ext.lower() == '.webp':
                        img_resized.save(save_path, quality=quality)
                    elif save_ext.lower() == '.png':
                        img_resized.save(save_path, optimize=True)
                    else:
                        img_resized.save(save_path)

                    processed += 1
                    msg = f"✓ {filename}"
                    self.after(0, lambda m=msg: self._log(m))

                except Exception as e:
                    errors += 1
                    msg = f"✗ {filename}: {str(e)}"
                    self.after(0, lambda m=msg: self._log(m))

                # Update progress
                progress = (i + 1) / total
                self.after(0, lambda p=progress: self.progress_bar.set(p))

            # Summary
            self.after(0, lambda: self._log("\n" + "-" * 50))
            self.after(0, lambda: self._log(f"Complete! Processed: {processed}, Errors: {errors}"))

        except Exception as e:
            self.after(0, lambda: self._log(f"\nError: {str(e)}"))

        finally:
            self.after(0, self._processing_complete)

    def _processing_complete(self):
        """Reset UI after processing completes."""
        self.is_processing = False
        self.start_button.configure(state="normal", text="Start Resizing")


def main():
    app = ImageResizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
