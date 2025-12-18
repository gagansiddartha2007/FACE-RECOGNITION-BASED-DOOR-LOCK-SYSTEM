## Known Faces Directory

This directory stores images of **authorized persons** used for face recognition.

The script `train_faces.py` automatically scans all subfolders inside this directory and generates face encodings for each person.

---

### How to Add Authorized Users

1. **Create a folder for each person**
   - Folder name should be the person’s name (used as their label)

2. **Add photos of the person**
   - Place **3–10 clear, front-facing photos** inside their folder
   - Use:
     - Good lighting
     - No glasses or sunglasses
     - Minimal background
   - Supported formats:
     - `.jpg`
     - `.png`

---

