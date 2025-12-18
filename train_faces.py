import face_recognition
import cv2
import os
import pickle

DATASET_DIR = 'known_faces'
ENCODING_FILE = 'encodings.pickle'

known_encodings = []
known_names = []

print("📂 Loading images from dataset...")

for person_name in os.listdir(DATASET_DIR):
    person_dir = os.path.join(DATASET_DIR, person_name)
    if not os.path.isdir(person_dir):
        continue

    print(f"🧠 Encoding faces for: {person_name}")

    for image_file in os.listdir(person_dir):
        if not image_file.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue

        image_path = os.path.join(person_dir, image_file)
        image = cv2.imread(image_path)
        if image is None:
            print(f"⚠️ Skipping invalid file: {image_path}")
            continue

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        boxes = face_recognition.face_locations(rgb, model='hog')
        encodings = face_recognition.face_encodings(rgb, boxes)

        for encoding in encodings:
            known_encodings.append(encoding)
            known_names.append(person_name)

data = {'encodings': known_encodings, 'names': known_names}
with open(ENCODING_FILE, 'wb') as f:
    pickle.dump(data, f)

print(f"✅ Training complete! Encodings saved to '{ENCODING_FILE}'.")
print(f"📊 Total People: {len(set(known_names))}, Total Faces: {len(known_names)}")