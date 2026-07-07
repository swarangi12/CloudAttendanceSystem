import os
import cv2
import mysql.connector
from datetime import datetime
from deepface import DeepFace

# ----------------------------
# MySQL Connection
# ----------------------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="swarangi@12",
    database="attendance_system"
)

cursor = db.cursor()

cap = cv2.VideoCapture(0)

print("===================================")
print(" FACE ATTENDANCE SYSTEM")
print("===================================")
print("Press SPACE to recognize")
print("Press Q to Quit")
print("===================================")

while True:

    ret, frame = cap.read()

    if not ret:
        break

    cv2.imshow("Attendance", frame)

    key = cv2.waitKey(1)

    if key == 32:

        cv2.imwrite("temp.jpg", frame)

        try:

            result = DeepFace.find(
                img_path="temp.jpg",
                db_path="dataset",
                model_name="Facenet512",
                detector_backend="opencv",
                distance_metric="cosine",
                enforce_detection=False,
                silent=True
            )

            if len(result) == 0 or result[0].empty:

                print("Unknown Student")

                cv2.putText(frame,
                            "Unknown Student",
                            (30,40),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1,
                            (0,0,255),
                            2)

                cv2.imshow("Attendance", frame)
                cv2.waitKey(2000)
                continue

            # ------------------------
            # Get Roll Number
            # ------------------------

            matched_path = result[0].iloc[0]["identity"]

            roll = os.path.basename(os.path.dirname(matched_path))

            # ------------------------
            # Get Student Name
            # ------------------------

            cursor.execute(
                "SELECT name FROM students WHERE roll_no=%s",
                (roll,)
            )

            student = cursor.fetchone()

            if student is None:
                print("Student not found")
                continue

            name = student[0]

            today = datetime.now().date()
            current_time = datetime.now().time()

            # ------------------------
            # Duplicate Check
            # ------------------------

            cursor.execute("""
            SELECT *
            FROM attendance
            WHERE roll_no=%s
            AND date=%s
            """,(roll,today))

            already = cursor.fetchone()

            if already:

                message = "Already Marked"

            else:

                cursor.execute("""
                INSERT INTO attendance
                (roll_no,name,date,time,status)
                VALUES(%s,%s,%s,%s,%s)
                """,
                (
                    roll,
                    name,
                    today,
                    current_time,
                    "Present"
                ))

                db.commit()

                message = "Attendance Marked"

            # ------------------------
            # Display on Screen
            # ------------------------

            cv2.putText(frame,
                        name,
                        (30,40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0,255,0),
                        2)

            cv2.putText(frame,
                        message,
                        (30,80),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (255,0,0),
                        2)

            cv2.imshow("Attendance", frame)

            print(name, "-", message)

            cv2.waitKey(2500)

        except Exception as e:

            print(e)

    elif key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
db.close()