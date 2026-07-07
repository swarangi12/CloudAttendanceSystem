import cv2
import os

# Load face detector
face_detector = cv2.CascadeClassifier(
    "haarcascade_frontalface_default.xml"
)

def capture_student(roll):

    folder = os.path.join("dataset", str(roll))
    os.makedirs(folder, exist_ok=True)

    camera = cv2.VideoCapture(0)

    count = 0

    while True:

        success, frame = camera.read()

        if not success:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_detector.detectMultiScale(
            gray,
            scaleFactor=1.3,
            minNeighbors=5
        )

        for (x, y, w, h) in faces:

            face = frame[y:y+h, x:x+w]

            count += 1

            filename = os.path.join(
                folder,
                f"{count}.jpg"
            )

            cv2.imwrite(filename, face)

            cv2.rectangle(
                frame,
                (x, y),
                (x+w, y+h),
                (0,255,0),
                2
            )

        cv2.imshow("Capture Face", frame)

        if cv2.waitKey(1) == ord('q'):
            break

        if count >= 30:
            break

    camera.release()
    cv2.destroyAllWindows()

    return True