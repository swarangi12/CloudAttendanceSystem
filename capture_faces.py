import cv2
import os

def capture_student():
    roll = input("Enter Student Roll Number: ")

    folder = os.path.join("dataset", roll)
    os.makedirs(folder, exist_ok=True)




    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Cannot open camera")
        return

    count = 0

    print("Capturing Images...")

    while count < 30:
        success, frame = camera.read()

        if not success:
            break

        cv2.imshow("Capture Face", frame)

        image_path = os.path.join(folder, f"{count+1}.jpg")
        cv2.imwrite(image_path, frame)

        count += 1

        if cv2.waitKey(300) & 0xFF == ord('q'):
            break

    camera.release()
    cv2.destroyAllWindows()

    print("30 Images Saved Successfully!")