import face_recognition
import cv2
import pickle
import serial
import time
import numpy as np
import dlib
from scipy.spatial import distance as dist
from collections import deque
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os

ENCODING_FILE = 'encodings.pickle'
TOLERANCE = 0.45
MODEL = 'hog'
SERIAL_PORT = os.getenv("ARDUINO_PORT", "COM3")
BAUD_RATE = 9600
SEND_DELAY = 10
LANDMARK_MODEL = 'shape_predictor_68_face_landmarks.dat'

EYE_AR_THRESH = 0.25
TEXTURE_VARIANCE_THRESH = 150
MOTION_FRAMES = 30
FRAME_DIFF_THRESHOLD = 5

LEFT_EYE = list(range(36, 42))
RIGHT_EYE = list(range(42, 48))

RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASS = os.getenv("SENDER_PASS")

def eye_aspect_ratio(eye):
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

def send_mail_with_img(img_path):
    subject = "Alert: Unknown person detected at door"
    body = "An unknown person tried to access the door. See the attached photo."
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    part = MIMEBase('application', 'octet-stream')
    with open(img_path, 'rb') as attachment:
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(img_path)}')
    msg.attach(part)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASS)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        server.quit()
        print(f"📧 Email alert sent to {RECIPIENT_EMAIL}")
        os.remove(img_path)
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def check_texture_quality(frame, face_location):
    top, right, bottom, left = face_location
    face_region = frame[top:bottom, left:right]
    if face_region.size == 0:
        return 0
    gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray_face, cv2.CV_64F).var()
    return laplacian_var

def detect_screen_playback(prev_frame, curr_frame, face_location):
    if prev_frame is None:
        return False
    top, right, bottom, left = face_location
    prev_face = prev_frame[top:bottom, left:right]
    curr_face = curr_frame[top:bottom, left:right]
    if prev_face.size == 0 or curr_face.size == 0:
        return False
    diff = cv2.absdiff(prev_face, curr_face)
    avg_diff = np.mean(diff)
    if avg_diff < FRAME_DIFF_THRESHOLD:
        print(f"  ⚠️ Screen detected! Frame diff too low: {avg_diff:.2f}")
        return True
    return False

def check_color_saturation(frame, face_location):
    top, right, bottom, left = face_location
    face_region = frame[top:bottom, left:right]
    if face_region.size == 0:
        return True
    hsv = cv2.cvtColor(face_region, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    avg_saturation = np.mean(saturation)
    if avg_saturation < 60:
        print(f"  ⚠️ Low saturation detected: {avg_saturation:.1f} (video/photo?)")
        return True
    return False

def check_frequency_artifacts(frame, face_location):
    top, right, bottom, left = face_location
    face_region = frame[top:bottom, left:right]
    if face_region.size == 0:
        return False
    gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    corners = laplacian[-10:, -10:]
    high_freq = np.sum(np.abs(corners))
    if high_freq > 10000:
        print(f"  ⚠️ Screen artifacts detected: {high_freq:.1f}")
        return True
    return False

def check_reflection_glare(frame, face_location):
    top, right, bottom, left = face_location
    face_region = frame[top:bottom, left:right]
    if face_region.size == 0:
        return False
    hsv = cv2.cvtColor(face_region, cv2.COLOR_BGR2HSV)
    brightness = hsv[:, :, 2]
    glare_pixels = np.sum(brightness > 250)
    total_pixels = brightness.size
    glare_ratio = glare_pixels / total_pixels
    if glare_ratio > 0.05: 
        print(f"  ⚠️ Screen glare detected: {glare_ratio*100:.1f}% bright pixels")
        return True
    return False

print("📦 Loading face encodings...")
with open(ENCODING_FILE, 'rb') as f:
    data = pickle.load(f)

print("⚙️ Connecting to Arduino...")
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print(f"✅ Arduino connected")
except Exception as e:
    ser = None
    print(f"⚠️ Arduino not available: {e}")

video = cv2.VideoCapture(0)
if not video.isOpened():
    print("❌ Webcam not found")
    exit()

print("🔐 ADVANCED Anti-Spoofing Door Lock System")
print("=" * 60)
print("✅ Real faces ONLY - Videos/Photos REJECTED")
print("=" * 60)

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(LANDMARK_MODEL)

blink_count = 0
prev_ear = None
prev_frame = None
pose_history = deque(maxlen=MOTION_FRAMES)
face_detected_frames = 0
unlock_time = None
door_open = False
last_command_time = time.time()
spoof_detected_frames = 0

unknown_start_time = None
unknown_detected = False

while True:
    ret, frame = video.read()
    if not ret:
        continue

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_small_frame, model=MODEL)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
    current_time = time.time()

    if door_open and (current_time - unlock_time) >= 5:
        if ser is not None:
            ser.write(b"close\n")
        print("🔐 Door CLOSED automatically")
        door_open = False
        blink_count = 0
        face_detected_frames = 0
        pose_history.clear()
        spoof_detected_frames = 0

    if len(face_locations) > 0:
        face_detected_frames += 1
        recognized_face_present = False

        for face_encoding, face_location in zip(face_encodings, face_locations):
            results = face_recognition.compare_faces(data['encodings'], face_encoding, tolerance=TOLERANCE)
            top, right, bottom, left = [v * 4 for v in face_location]

            if True not in results:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.putText(frame, "UNKNOWN", (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                unknown_img = frame[top:bottom, left:right]

                if not unknown_detected:
                    unknown_start_time = current_time
                    unknown_detected = True
                else:
                    elapsed = current_time - unknown_start_time
                    if elapsed >= 2:
                        img_filename = f"temp/unknown_{int(current_time)}.jpg"
                        cv2.imwrite(img_filename, unknown_img)
                        send_mail_with_img(img_filename)
                        unknown_detected = False  

                continue

            recognized_face_present = True
            unknown_detected = False
            unknown_start_time = None

            match_index = results.index(True)
            name = data['names'][match_index]
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

            texture_var = check_texture_quality(frame, (top, right, bottom, left))
            cv2.putText(frame, f"Texture: {texture_var:.1f}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)

            if texture_var < TEXTURE_VARIANCE_THRESH:
                spoof_detected_frames += 1
                cv2.putText(frame, f"❌ LOW TEXTURE (video/photo): {texture_var:.1f}", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                continue
            else:
                spoof_detected_frames = 0

            if check_color_saturation(frame, (top, right, bottom, left)):
                spoof_detected_frames += 1
                cv2.putText(frame, "❌ SPOOF: Color saturation abnormal", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                continue

            if check_reflection_glare(frame, (top, right, bottom, left)):
                spoof_detected_frames += 1
                cv2.putText(frame, "❌ SPOOF: Screen glare detected", (50, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                continue

            if check_frequency_artifacts(frame, (top, right, bottom, left)):
                spoof_detected_frames += 1
                cv2.putText(frame, "❌ SPOOF: Screen artifacts detected", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                continue

            if prev_frame is not None:
                if detect_screen_playback(prev_frame, gray, (top, right, bottom, left)):
                    spoof_detected_frames += 1
                    cv2.putText(frame, "❌ SPOOF: Screen playback detected", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    continue
                else:
                    spoof_detected_frames = 0

            rects = detector(gray, 0)
            if not rects:
                continue
            rect = rects[0]
            shape = predictor(gray, rect)
            shape_np = np.array([[p.x, p.y] for p in shape.parts()])

            left_eye = shape_np[LEFT_EYE]
            right_eye = shape_np[RIGHT_EYE]
            left_ear = eye_aspect_ratio(left_eye)
            right_ear = eye_aspect_ratio(right_eye)
            ear = (left_ear + right_ear) / 2.0

            if prev_ear is not None and prev_ear < EYE_AR_THRESH and ear >= EYE_AR_THRESH:
                blink_count += 1
                print(f"✅ Blink detected! Count: {blink_count}")
            prev_ear = ear

            nose_x = shape_np[30][0]
            nose_y = shape_np[30][1]
            pose_history.append(np.array([nose_x, nose_y]))
            has_motion = False
            if len(pose_history) >= 5:
                pose_array = np.array(pose_history)
                nose_variance = np.var(pose_array[:, 0])
                has_motion = nose_variance > 8
                motion_text = f"Motion: {nose_variance:.1f}"
            else:
                motion_text = f"Checking motion... {len(pose_history)}/5"
            cv2.putText(frame, motion_text, (50, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

            if (blink_count >= 1 and 
                has_motion and 
                texture_var > TEXTURE_VARIANCE_THRESH and 
                face_detected_frames > 20 and 
                spoof_detected_frames == 0):
                cv2.putText(frame, "✅ REAL FACE VERIFIED - UNLOCKING!", (50, 270), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                print("\n" + "="*60)
                print("🔓 REAL FACE DETECTED - DOOR UNLOCKING!")
                print(f"  ✅ Texture: {texture_var:.1f} (HIGH)")
                print(f"  ✅ Blinks: {blink_count}")
                print(f"  ✅ Motion: Detected")
                print(f"  ✅ No spoofing detected")
                print("="*60 + "\n")
                if ser is not None and (current_time - last_command_time) > SEND_DELAY:
                    ser.write(b"open\n")
                    unlock_time = current_time
                    door_open = True
                    last_command_time = current_time
                    blink_count = 0
                    face_detected_frames = 0
                    pose_history.clear()
                    spoof_detected_frames = 0

        if recognized_face_present:
            unknown_detected = False
            unknown_start_time = None

    else:
        face_detected_frames = 0
        blink_count = 0
        prev_ear = None
        pose_history.clear()
        spoof_detected_frames = 0
        unknown_detected = False
        unknown_start_time = None
        cv2.putText(frame, "No face detected", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

    status_color = (0, 255, 0) if door_open else (0, 0, 255)
    door_status = "🟢 OPEN" if door_open else "🔴 LOCKED"
    cv2.putText(frame, door_status, (50, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, status_color, 2)
    cv2.imshow("🔐 Anti-Spoofing Door Lock - Real Faces Only", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    prev_frame = gray.copy()

video.release()
cv2.destroyAllWindows()
if ser is not None:
    ser.close()

print("✅ System stopped")
