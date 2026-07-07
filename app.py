from flask import Flask, render_template, request, redirect
import mysql.connector
from datetime import datetime
from camera import capture_student
from openpyxl import Workbook
from flask import send_file
import subprocess
from flask import redirect
import sys
import os

app = Flask(__name__)

# ----------------------------
# MySQL Connection
# ----------------------------
db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    port=int(os.getenv("DB_PORT", 3306))
)

cursor = db.cursor()

print("Database Connected Successfully!")

# ===================================================
# HOME
# ===================================================

@app.route("/")
def home():
    return render_template("index.html")


# ===================================================
# LOGIN
# ===================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            return redirect("/dashboard")

        else:
            return render_template(
                "login.html",
                error="Invalid Username or Password"
            )

    return render_template("login.html")


# ===================================================
# DASHBOARD
# ===================================================

@app.route("/dashboard")
def dashboard():

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    today = datetime.now().date()

    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE date=%s
        AND status='Present'
    """, (today,))

    present = cursor.fetchone()[0]

    absent = total_students - present

    return render_template(
        "dashboard.html",
        total_students=total_students,
        present=present,
        absent=absent,
        today=today
    )


# ===================================================
# REGISTER STUDENT
# ===================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        roll = request.form["roll"]
        name = request.form["name"]
        department = request.form["department"]
        semester = request.form["semester"]
        email = request.form["email"]

        cursor.execute("""
        INSERT INTO students
        (roll_no,name,department,semester,email)

        VALUES(%s,%s,%s,%s,%s)
        """,

        (
            roll,
            name,
            department,
            semester,
            email
        ))

        db.commit()

        return redirect("/students")

    return render_template("register.html")


# ===================================================
# VIEW STUDENTS
# ===================================================

@app.route("/students")
def students():

    search = request.args.get("search")

    if search:

        cursor.execute("""
        SELECT roll_no,name,department,semester,email

        FROM students

        WHERE roll_no LIKE %s
        OR name LIKE %s
        """,

        (
            "%" + search + "%",
            "%" + search + "%"
        ))

    else:

        cursor.execute("""
        SELECT roll_no,name,department,semester,email
        FROM students
        """)

    students = cursor.fetchall()

    return render_template(
        "students.html",
        students=students
    )


# ===================================================
# EDIT STUDENT
# ===================================================

@app.route("/edit/<roll>", methods=["GET", "POST"])
def edit_student(roll):

    if request.method == "POST":

        name = request.form["name"]
        department = request.form["department"]
        semester = request.form["semester"]
        email = request.form["email"]

        cursor.execute("""

        UPDATE students

        SET

        name=%s,
        department=%s,
        semester=%s,
        email=%s

        WHERE roll_no=%s

        """,

        (
            name,
            department,
            semester,
            email,
            roll
        ))

        db.commit()

        return redirect("/students")

    cursor.execute("""
    SELECT roll_no,name,department,semester,email

    FROM students

    WHERE roll_no=%s
    """,(roll,))

    student = cursor.fetchone()

    return render_template(
        "edit_student.html",
        student=student
    )


# ===================================================
# DELETE STUDENT
# ===================================================

@app.route("/delete/<roll>")
def delete_student(roll):

    cursor.execute(
        "DELETE FROM students WHERE roll_no=%s",
        (roll,)
    )

    db.commit()

    return redirect("/students")


# ===================================================
# CAPTURE FACE
# ===================================================

@app.route("/capture/<roll>")
def capture_face(roll):

    capture_student(roll)

    return """
    <h2>Face Captured Successfully!</h2>

    <a href='/students'>
    Back to Students
    </a>
    """


# ===================================================
# ATTENDANCE PAGE
# ===================================================

@app.route("/attendance")
def attendance():

    cursor.execute("""
        SELECT *
        FROM attendance
        ORDER BY attendance_id DESC
    """)

    records = cursor.fetchall()

    return render_template(
        "attendance.html",
        records=records
    )
@app.route("/start_attendance")
def start_attendance():
    print("Flask Python:", sys.executable)

    subprocess.run([sys.executable, "recognize.py"])

    return redirect("/attendance")


# ===================================================
# SAVE ATTENDANCE
# ===================================================

@app.route("/save_attendance", methods=["POST"])
def save_attendance():

    present_students = request.form.getlist("present")

    cursor.execute("""
    SELECT roll_no,name
    FROM students
    """)

    students = cursor.fetchall()

    today = datetime.now().date()

    current_time = datetime.now().time()

    for student in students:

        roll = student[0]
        name = student[1]

        if roll in present_students:
            status = "Present"
        else:
            status = "Absent"

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
            status
        ))

    db.commit()

    return redirect("/report")


# ===================================================
# REPORT
# ===================================================

@app.route("/report")
def report():

    cursor.execute("""

    SELECT

    date,
    roll_no,
    name,
    status

    FROM attendance

    ORDER BY date DESC

    """)

    records = cursor.fetchall()

    return render_template(
        "report.html",
        records=records
    )
@app.route("/export_excel")
def export_excel():

    wb = Workbook()

    ws = wb.active

    ws.title = "Attendance Report"

    # Heading
    ws.append([
        "Date",
        "Roll No",
        "Name",
        "Status"
    ])

    cursor.execute("""
        SELECT date,
               roll_no,
               name,
               status
        FROM attendance
        ORDER BY date DESC
    """)

    records = cursor.fetchall()

    for row in records:
        ws.append(row)

    file_name = "Attendance_Report.xlsx"

    wb.save(file_name)

    return send_file(
        file_name,
        as_attachment=True
    )


# ===================================================
# RUN
# ===================================================

if __name__ == "__main__":
    app.run(debug=True)