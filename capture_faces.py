import cv2
import os

# Ask for student's roll number
roll = input("Enter Student Roll Number: ")

# Create folder path
folder = os.path.join("dataset", roll)

# Create folder if it doesn't exist
os.makedirs(folder, exist_ok=True)

# Open webcam
camera = cv2.VideoCapture(0)

count = 0

print("Capturing Images...")

while count < 30:

    success, frame = camera.read()

    if not success:
        break

    # Display camera
    cv2.imshow("Capture Face", frame)

    # Save image
    image_path = os.path.join(folder, f"{count+1}.jpg")
    cv2.imwrite(image_path, frame)

    count += 1

    print(f"Captured Image {count}")

    # Wait 300 milliseconds
    cv2.waitKey(300)

# Release camera
camera.release()

cv2.destroyAllWindows()

print("30 Images Saved Successfully!")