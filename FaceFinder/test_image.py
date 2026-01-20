"""Quick test to debug face_recognition image loading"""
import face_recognition
import numpy as np
from PIL import Image

image_path = "X:/SearchImages/Laura_face_GS.jpg"

print(f"Testing image: {image_path}")

# Check dlib version
import dlib
print(f"dlib version: {dlib.__version__}")
print(f"face_recognition version: {face_recognition.__version__}")

# Test with a synthetic image first
print("\n--- Test with synthetic image ---")
try:
    # Create a simple test array
    test_arr = np.zeros((100, 100, 3), dtype=np.uint8)
    test_arr[:, :] = [128, 128, 128]  # Gray
    print(f"Synthetic: shape={test_arr.shape}, dtype={test_arr.dtype}")
    encodings = face_recognition.face_encodings(test_arr)
    print(f"Synthetic worked! (no faces expected): {len(encodings)}")
except Exception as e:
    print(f"Even synthetic failed: {e}")

# Method 5: Force copy to new array
print("\n--- Method 5: Force copy to fresh array ---")
try:
    pil_img = Image.open(image_path)
    print(f"PIL mode: {pil_img.mode}, size: {pil_img.size}")
    if pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')
        print(f"Converted to RGB")
    # Create a fresh array by copying
    arr = np.array(pil_img, dtype=np.uint8).copy()
    print(f"Shape: {arr.shape}, dtype: {arr.dtype}, contiguous: {arr.flags['C_CONTIGUOUS']}")
    encodings = face_recognition.face_encodings(arr)
    print(f"SUCCESS! Faces found: {len(encodings)}")
except Exception as e:
    print(f"Error: {e}")

# Method 6: Create blank array and fill it
print("\n--- Method 6: Manual array creation ---")
try:
    pil_img = Image.open(image_path)
    if pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')
    w, h = pil_img.size
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    arr[:] = np.array(pil_img)
    print(f"Shape: {arr.shape}, dtype: {arr.dtype}")
    encodings = face_recognition.face_encodings(arr)
    print(f"SUCCESS! Faces found: {len(encodings)}")
except Exception as e:
    print(f"Error: {e}")

# Method 7: Use face_recognition with a known working image format
print("\n--- Method 7: Save as BMP and reload ---")
try:
    import io
    pil_img = Image.open(image_path)
    if pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')
    # Save to bytes as BMP (uncompressed)
    buf = io.BytesIO()
    pil_img.save(buf, format='BMP')
    buf.seek(0)
    # Reload
    reloaded = Image.open(buf)
    arr = np.array(reloaded)
    print(f"Shape: {arr.shape}, dtype: {arr.dtype}")
    encodings = face_recognition.face_encodings(arr)
    print(f"SUCCESS! Faces found: {len(encodings)}")
except Exception as e:
    print(f"Error: {e}")
