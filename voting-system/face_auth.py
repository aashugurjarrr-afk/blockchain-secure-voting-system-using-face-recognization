import cv2
import os
import numpy as np

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

recognizer = cv2.face.LBPHFaceRecognizer_create()
names = {}
trained = False
current_frame = None


def train_model():
    global trained

    faces = []
    labels = []
    names.clear()

    if not os.path.exists('faces'):
        return

    i = 0

    for file in os.listdir('faces'):
        path = os.path.join('faces', file)

        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)

        if img is None:
            continue

        detected = face_cascade.detectMultiScale(img, 1.3, 5)

        for (x, y, w, h) in detected:
            face = img[y:y+h, x:x+w]
            face = cv2.resize(face, (200, 200))

            faces.append(face)
            labels.append(i)

            name = file.split('_')[0]
            names[i] = name
            i += 1

    if len(faces) > 0:
        recognizer.train(faces, np.array(labels))
        trained = True
        print("Model trained on", len(faces), "faces")


def initialize_model():
    train_model()


def generate_frames():
    global current_frame

    camera = cv2.VideoCapture(0)

    while True:
        success, frame = camera.read()
        if not success:
            break

        current_frame = frame.copy()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            face = gray[y:y+h, x:x+w]
            face = cv2.resize(face, (200, 200))

            label = "Unknown"

            if trained:
                id_, conf = recognizer.predict(face)

                if conf < 60:   # balanced threshold
                    label = names.get(id_, "Unknown")

            cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)
            cv2.putText(frame, label, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def recognize_user():
    global current_frame

    if not trained or current_frame is None:
        return None, None

    gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        face = gray[y:y+h, x:x+w]
        face = cv2.resize(face, (200, 200))

        id_, conf = recognizer.predict(face)
        name = names.get(id_, "Unknown")

        print(f"{name} | Confidence: {conf}")

        if conf < 60:
            return name, conf

    return None, None