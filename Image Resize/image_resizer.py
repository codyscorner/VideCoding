import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import os

def resize_images():
    folder_path = folder_entry.get()
    if not folder_path:
        messagebox.showerror("Error", "Please select a folder.")
        return

    output_folder = os.path.join(folder_path, "resized_images")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    feedback_listbox.delete(0, tk.END)
    feedback_listbox.insert(tk.END, f"Output folder: {output_folder}")

    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if not image_files:
        feedback_listbox.insert(tk.END, "No images found in the selected folder.")
        return

    for filename in image_files:
        try:
            img_path = os.path.join(folder_path, filename)
            img = Image.open(img_path)
            img_resized = img.resize((512, 512))
            save_path = os.path.join(output_folder, filename)
            img_resized.save(save_path)
            feedback_listbox.insert(tk.END, f"Resized and saved: {filename}")
        except Exception as e:
            feedback_listbox.insert(tk.END, f"Error resizing {filename}: {e}")

    feedback_listbox.insert(tk.END, "--- Process Complete ---")

def browse_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        folder_entry.delete(0, tk.END)
        folder_entry.insert(0, folder_selected)

# --- GUI Setup ---
root = tk.Tk()
root.title("Image Resizer")

# Folder selection frame
folder_frame = tk.Frame(root, padx=10, pady=10)
folder_frame.pack(fill=tk.X)

folder_label = tk.Label(folder_frame, text="Folder:")
folder_label.pack(side=tk.LEFT)

folder_entry = tk.Entry(folder_frame, width=150)
folder_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

browse_button = tk.Button(folder_frame, text="Browse...", command=browse_folder)
browse_button.pack(side=tk.LEFT)

# Feedback listbox
feedback_frame = tk.Frame(root, padx=10, pady=5)
feedback_frame.pack(fill=tk.BOTH, expand=True)

feedback_listbox = tk.Listbox(feedback_frame)
feedback_listbox.pack(fill=tk.BOTH, expand=True)

# Start button
start_button = tk.Button(root, text="Start Resizing", command=resize_images, padx=10, pady=10)
start_button.pack(pady=10)

# Check for Pillow installation
try:
    from PIL import Image
except ImportError:
    messagebox.showinfo("Info", "Pillow library not found. Please install it using: pip install Pillow")
    # You might want to disable the start button here if Pillow is not installed
    start_button.config(state=tk.DISABLED)


root.mainloop()
