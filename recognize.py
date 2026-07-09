import os
import cv2
import mysql.connector
from datetime import datetime
from deepface import DeepFace
import threading
import time

# ----------------------------
# Model Preloading
# ----------------------------
print("===================================")
print(" INITIALIZING FACE RECOGNITION MODEL")
print("===================================")
try:
    # Preload model to prevent latency on first capture
    DeepFace.build_model("Facenet512")
    print("Model loaded successfully!")
except Exception as e:
    print("Failed to preload model:", e)
print("===================================")

# ----------------------------
# Thread-safe State Variables
# ----------------------------
recognizing_thread = None
status_msg = ""
status_color = (0, 255, 0)
show_status_until = 0

def perform_recognition(frame_copy):
    global status_msg, status_color, show_status_until

    try:
        # Perform recognition directly on the in-memory frame
        result = DeepFace.find(
            img_path=frame_copy,
            db_path="dataset",
            model_name="Facenet512",
            detector_backend="opencv",
            distance_metric="cosine",
            enforce_detection=False,
            silent=True
        )

        if len(result) == 0 or result[0].empty:
            status_msg = "Unknown Student"
            status_color = (0, 0, 255) # Red
            show_status_until = time.time() + 3.0
            print("Unknown Student")
            return

        # Get Roll Number
        matched_path = result[0].iloc[0]["identity"]
        roll = os.path.basename(os.path.dirname(matched_path))

        # Open thread-local MySQL Connection
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="swarangi@12",
            database="attendance_system"
        )
        cursor = db.cursor()

        # Get Student Name
        cursor.execute(
            "SELECT name FROM students WHERE roll_no=%s",
            (roll,)
        )
        student = cursor.fetchone()

        if student is None:
            status_msg = f"Roll {roll} not in DB"
            status_color = (0, 0, 255) # Red
            show_status_until = time.time() + 3.0
            print(f"Student roll {roll} not found in database")
            db.close()
            return

        name = student[0]
        today = datetime.now().date()
        current_time = datetime.now().time()

        # Duplicate Check
        cursor.execute("""
            SELECT *
            FROM attendance
            WHERE roll_no=%s
            AND date=%s
        """, (roll, today))
        already = cursor.fetchone()

        if already:
            message = "Already Marked"
            status_color = (0, 255, 255) # Yellow/Cyan
        else:
            cursor.execute("""
                INSERT INTO attendance
                (roll_no, name, date, time, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (roll, name, today, current_time, "Present"))
            db.commit()
            message = "Attendance Marked"
            status_color = (0, 255, 0) # Green

        status_msg = f"{name}: {message}"
        show_status_until = time.time() + 3.5
        print(f"{name} - {message}")
        db.close()

    except Exception as e:
        print("Error during recognition thread:", e)
        status_msg = "Recognition Error"
        status_color = (0, 0, 255) # Red
        show_status_until = time.time() + 3.0


cap = cv2.VideoCapture(0)

print("\n===================================")
print(" CAMERA FEED ACTIVE")
print("===================================")
print("Press SPACE to recognize face")
print("Press Q to Quit")
print("===================================")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Add overlays onto display frame (working copy)
    display_frame = frame.copy()

    # Draw Status overlay
    if time.time() < show_status_until:
        cv2.putText(
            display_frame,
            status_msg,
            (30, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            status_color,
            2
        )
    elif recognizing_thread and recognizing_thread.is_alive():
        cv2.putText(
            display_frame,
            "Processing Face...",
            (30, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 165, 0), # Orange
            2
        )

    cv2.imshow("Attendance", display_frame)
    key = cv2.waitKey(1)

    if key == 32: # SPACE
        if recognizing_thread and recognizing_thread.is_alive():
            print("Already processing, please wait...")
            continue

        print("Capturing frame for recognition...")
        # Send copy of current frame to recognition thread
        frame_to_recognize = frame.copy()
        recognizing_thread = threading.Thread(
            target=perform_recognition,
            args=(frame_to_recognize,)
        )
        recognizing_thread.start()

    elif key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()