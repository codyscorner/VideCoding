from tkinter import *
from tkinter import filedialog, Text, ttk
import face_recognition
import os

class FaceSearchApp:
    def __init__(self):
        self.root = Tk()
        self.root.title("Face Search")

        self.ref_path = StringVar()
        Label(self.root, text="Reference Image:").pack()
        Entry(self.root, textvariable=self.ref_path, width=50).pack()
        Button(self.root, text="Browse", command=self.browse_ref).pack()

        self.folder = StringVar()
        Label(self.root, text="Search Folder:").pack()
        Entry(self.root, textvariable=self.folder, width=50).pack()
        Button(self.root, text="Browse", command=self.browse_folder).pack()

        Button(self.root, text="Search", command=self.search).pack(pady=10)

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=5)

        self.result = Text(self.root, height=10, width=60)
        self.result.pack(pady=5)

        self.root.mainloop()

    def browse_ref(self):
        self.ref_path.set(filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")]))

    def browse_folder(self):
        self.folder.set(filedialog.askdirectory())

    def search(self):
        self.result.delete(1.0, END)
        self.progress['value'] = 0
        ref_path = self.ref_path.get()
        folder = self.folder.get()
        if not ref_path or not folder:
            self.result.insert(END, "Select image and folder.")
            return

        try:
            ref_image = face_recognition.load_image_file(ref_path)
            ref_encodings = face_recognition.face_encodings(ref_image)
            if not ref_encodings:
                self.result.insert(END, "No face found in reference.")
                return
            ref_encoding = ref_encodings[0]
        except Exception as e:
            self.result.insert(END, f"Error loading reference: {e}")
            return

        # Count total images first for progress
        total_images = 0
        for root_dir, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    total_images += 1

        if total_images == 0:
            self.result.insert(END, "No images found in folder.")
            return

        self.progress['maximum'] = total_images
        processed = 0
        matches = []

        for root_dir, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    path = os.path.join(root_dir, file)
                    try:
                        image = face_recognition.load_image_file(path)
                        encodings = face_recognition.face_encodings(image)
                        for enc in encodings:
                            if face_recognition.compare_faces([ref_encoding], enc, tolerance=0.6)[0]:
                                matches.append(path)
                                break
                    except:
                        pass

                    processed += 1
                    self.progress['value'] = processed
                    self.root.update_idletasks()  # Update GUI

        self.result.insert(END, f"Found {len(matches)} matches:\n")
        for match in matches:
            self.result.insert(END, f"{match}\n")

if __name__ == "__main__":
    app = FaceSearchApp()