import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os

class PngToIcoConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("PNG to ICO Converter")
        self.root.geometry("600x500")

        self.selected_file = None
        self.preview_image = None

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        ttk.Label(main_frame, text="Select PNG File:").grid(row=0, column=0, sticky=tk.W, pady=5)

        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        file_frame.columnconfigure(0, weight=1)

        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, state="readonly")
        self.file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        self.browse_button = ttk.Button(file_frame, text="Browse", command=self.browse_file)
        self.browse_button.grid(row=0, column=1)

        ttk.Label(main_frame, text="Preview:").grid(row=1, column=0, sticky=(tk.W, tk.N), pady=5)

        preview_frame = ttk.Frame(main_frame, relief="sunken", borderwidth=2)
        preview_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.preview_label = ttk.Label(preview_frame, text="No image selected", anchor="center")
        self.preview_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        self.convert_button = ttk.Button(button_frame, text="Convert to ICO",
                                       command=self.convert_to_ico, state="disabled")
        self.convert_button.pack()

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select PNG Image",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )

        if file_path:
            self.selected_file = file_path
            self.file_path_var.set(file_path)
            self.load_preview()
            self.convert_button.config(state="normal")

    def load_preview(self):
        try:
            image = Image.open(self.selected_file)

            max_size = (300, 300)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)

            photo = ImageTk.PhotoImage(image)
            self.preview_image = photo

            self.preview_label.config(image=photo, text="")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")
            self.preview_label.config(image="", text="Failed to load image")

    def convert_to_ico(self):
        if not self.selected_file:
            messagebox.showwarning("Warning", "Please select a PNG file first.")
            return

        try:
            output_path = filedialog.asksaveasfilename(
                title="Save ICO file as",
                defaultextension=".ico",
                filetypes=[("ICO files", "*.ico"), ("All files", "*.*")],
                initialname=os.path.splitext(os.path.basename(self.selected_file))[0] + ".ico"
            )

            if output_path:
                image = Image.open(self.selected_file)

                if image.mode != 'RGBA':
                    image = image.convert('RGBA')

                sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
                images = []

                for size in sizes:
                    resized = image.resize(size, Image.Resampling.LANCZOS)
                    images.append(resized)

                images[0].save(output_path, format='ICO', sizes=[img.size for img in images])

                messagebox.showinfo("Success", f"ICO file saved successfully!\n{output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to convert image: {str(e)}")

def main():
    root = tk.Tk()
    app = PngToIcoConverter(root)
    root.mainloop()

if __name__ == "__main__":
    main()