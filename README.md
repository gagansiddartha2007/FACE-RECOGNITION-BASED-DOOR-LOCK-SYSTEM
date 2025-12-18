# Anti-Spoofing Face Recognition Based Door Lock

This project is a smart door lock system that uses face recognition and anti-spoofing to allow only real, authorized people to unlock a door. It uses Python for face detection/recognition and an Arduino + servo motor to control the physical lock, with email alerts for unknown visitors.

## Features

- Face recognition with `face_recognition` and OpenCV  
- Anti-spoofing using:
  - Eye blink detection (Eye Aspect Ratio)  
  - Head/nose motion detection  
  - Texture quality (Laplacian variance)  
  - Color saturation and screen glare checks  
  - Screen playback / frame-difference checks  
- Arduino-controlled servo lock (open/close)  
- Email alert with photo when an unknown person stays at the door for more than 2 seconds  

## Project Structure

- `FACE_RECOGNITION.py` – main real-time door lock + anti-spoofing + Arduino + email script  
- `train_faces.py` – script to generate face encodings from known faces  
- `known_faces/Person1`, `known_faces/Person2`, ... – folders where you put training images for each person  
- `ARDUINO_CODE/ARDUINO_CODE.ino` – Arduino sketch that receives `"open"` / `"close"` over serial and drives the servo

## Requirements

- Python 3  
- Libraries: `face_recognition`, `opencv-python`, `dlib`, `numpy`, `scipy`, `pyserial`  
- Internet access for sending email (via SMTP)  
- Arduino (e.g., UNO) + servo motor  
- Webcam  

Install Python packages:
      
      pip install face_recognition opencv-python dlib numpy scipy pyserial
      

## Setup

1. **Download landmark model**  
   Download `shape_predictor_68_face_landmarks.dat` from the [dlib model download page](http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2) and place it in the project folder (same level as `FACE_RECOGNITION.py`).

2. **Add known faces**  
   - Inside `known_faces`, create a folder for each person (for example, `Person1`, `Person2`).  
   - Put that person's face images inside their folder (front-facing, clear images).  

3. **Train encodings**

        python train_faces.py

   
This creates `encodings.pickle` with face encodings for all people in `known_faces/`.

4. **Configure email**

Open `FACE_RECOGNITION.py` and set:

- `SENDER_EMAIL` – the email address used to send alerts  
- `RECIPIENT_EMAIL` – the email address that receives alerts  
- `SENDER_PASS` – app password for the sender email (for Gmail, use an [App Password](https://support.google.com/accounts/answer/185833))

5. **Connect Arduino**

- Open `ARDUINO_CODE/ARDUINO_CODE.ino` in the Arduino IDE and upload it to the Arduino board.  
- Make sure the serial baud rate in the Arduino sketch matches `BAUD_RATE` in `FACE_RECOGNITION.py`.  
- Set the correct `SERIAL_PORT` in `FACE_RECOGNITION.py` (for example, `COM3` on Windows).  

## Run the System

    python FACE_RECOGNITION.py

    
- When a live, authorized face is detected and passes anti-spoofing checks, the system sends an `"open"` command to Arduino and unlocks the door for a short time.  
- When an unknown person is detected and stays for more than 2 seconds, the system captures their face image and sends it by email to the configured recipient.
