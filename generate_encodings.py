import face_recognition
import os
import pickle

DATASET_PATH = "dataset"

known_encodings = []
known_names = []

for student_folder in os.listdir(DATASET_PATH):

    student_path = os.path.join(DATASET_PATH, student_folder)

    if not os.path.isdir(student_path):
        continue

    print(f"Processing Student: {student_folder}")

    for image_name in os.listdir(student_path):

        image_path = os.path.join(student_path, image_name)

        image = face_recognition.load_image_file(image_path)

        encodings = face_recognition.face_encodings(image)

        if len(encodings) > 0:

            known_encodings.append(encodings[0])
            known_names.append(student_folder)

print("Saving Encodings...")

with open("encodings.pkl", "wb") as file:
    pickle.dump(
        {
            "encodings": known_encodings,
            "names": known_names
        },
        file
    )

print("Done!")
print(f"Total Faces Encoded: {len(known_names)}")