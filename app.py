import os
import sys
import subprocess
from datetime import datetime

from flask import Flask, render_template, request, redirect, send_file
import mysql.connector
from openpyxl import Workbook
from dotenv import load_dotenv

# Load variables from a local .env file when present (no-op in production
# if the platform injects env vars directly).
load_dotenv()

app = Flask(__name__)


# ----------------------------
# MySQL Connection (env-based)
# ----------------------------
# Credentials are read from environment variables so the app never ships
# hardcoded secrets and can point at any cloud MySQL host at deploy time.
def _db_config():
    config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "attendance_system"),
        "port": int(os.getenv("DB_PORT", "3306")),
    }

    # Many managed MySQL providers (Aiven, PlanetScale, etc.) require SSL.
    # Set DB_SSL=true to enable it; optionally point DB_SSL_CA at a CA file.
    if os.getenv("DB_SSL", "").lower() in ("1", "true", "yes"):
        ca = os.getenv("DB_SSL_CA")
        if ca:
            config["ssl_ca"] = ca
        else:
            config["ssl_disabled"] = False

    return config


def get_db():
    """Return a live MySQL connection, reconnecting if needed.

    Using a fresh/validated connection per request avoids the classic
    "MySQL server has gone away" errors that happen with a single global
    connection on serverless / idle-heavy hosts.
    """
    global _db
    try:
        if _db is None or not _db.is_connected():
            _db = mysql.connector.connect(**_db_config())
    except (NameError, mysql.connector.Error):
        _db = mysql.connector.connect(**_db_config())
    return _db


_db = None


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

        admin_user = os.getenv("ADMIN_USERNAME", "admin")
        admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")

        if username == admin_user and password == admin_pass:
            return redirect("/dashboard")

        return render_template(
            "login.html",
            error="Invalid Username or Password",
        )

    return render_template("login.html")


# ===================================================
# DASHBOARD
# ===================================================
@app.route("/dashboard")
def dashboard():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    today = datetime.now().date()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM attendance
        WHERE date=%s
        AND status='Present'
        """,
        (today,),
    )

    present = cursor.fetchone()[0]
    absent = total_students - present

    return render_template(
        "dashboard.html",
        total_students=total_students,
        present=present,
        absent=absent,
        today=today,
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

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO students
            (roll_no,name,department,semester,email)
            VALUES(%s,%s,%s,%s,%s)
            """,
            (roll, name, department, semester, email),
        )

        db.commit()

        return redirect("/students")

    return render_template("register.html")


# ===================================================
# VIEW STUDENTS
# ===================================================
@app.route("/students")
def students():
    search = request.args.get("search")

    db = get_db()
    cursor = db.cursor()

    if search:
        cursor.execute(
            """
            SELECT roll_no,name,department,semester,email
            FROM students
            WHERE roll_no LIKE %s
            OR name LIKE %s
            """,
            ("%" + search + "%", "%" + search + "%"),
        )
    else:
        cursor.execute(
            """
            SELECT roll_no,name,department,semester,email
            FROM students
            """
        )

    student_rows = cursor.fetchall()

    return render_template("students.html", students=student_rows)


# ===================================================
# EDIT STUDENT
# ===================================================
@app.route("/edit/<roll>", methods=["GET", "POST"])
def edit_student(roll):
    db = get_db()
    cursor = db.cursor()

    if request.method == "POST":
        name = request.form["name"]
        department = request.form["department"]
        semester = request.form["semester"]
        email = request.form["email"]

        cursor.execute(
            """
            UPDATE students
            SET
            name=%s,
            department=%s,
            semester=%s,
            email=%s
            WHERE roll_no=%s
            """,
            (name, department, semester, email, roll),
        )

        db.commit()

        return redirect("/students")

    cursor.execute(
        """
        SELECT roll_no,name,department,semester,email
        FROM students
        WHERE roll_no=%s
        """,
        (roll,),
    )

    student = cursor.fetchone()

    return render_template("edit_student.html", student=student)


# ===================================================
# DELETE STUDENT
# ===================================================
@app.route("/delete/<roll>")
def delete_student(roll):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM students WHERE roll_no=%s", (roll,))

    db.commit()

    return redirect("/students")


# ===================================================
# CAPTURE FACE
# ===================================================
@app.route("/capture")
def capture():
    # The camera pipeline relies on OpenCV and a physical webcam, which are
    # not available on a cloud host. Import lazily and fail gracefully so the
    # rest of the app stays deployable.
    roll = request.args.get("roll")

    try:
        from camera import capture_student

        capture_student(roll)
        message = "<h2>Face Captured Successfully!</h2>"
    except Exception as exc:  # noqa: BLE001
        message = (
            "<h2>Face capture is unavailable on this server.</h2>"
            "<p>Capture requires a local machine with a webcam and OpenCV. "
            f"Details: {exc}</p>"
        )

    return message + "<a href='/students'>Back to Students</a>"


# ===================================================
# ATTENDANCE PAGE
# ===================================================
@app.route("/attendance")
def attendance():
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT *
        FROM attendance
        ORDER BY attendance_id DESC
        """
    )

    records = cursor.fetchall()

    return render_template("attendance.html", records=records)


@app.route("/start_attendance")
def start_attendance():
    # Live recognition needs a webcam + display and cannot run on a cloud
    # server. Guard it so the deployed app does not crash.
    try:
        subprocess.run([sys.executable, "recognize.py"], check=True)
    except Exception as exc:  # noqa: BLE001
        print("Recognition unavailable:", exc)

    return redirect("/attendance")


# ===================================================
# SAVE ATTENDANCE
# ===================================================
@app.route("/save_attendance", methods=["POST"])
def save_attendance():
    present_students = request.form.getlist("present")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT roll_no,name FROM students")
    student_rows = cursor.fetchall()

    today = datetime.now().date()
    current_time = datetime.now().time()

    for student in student_rows:
        roll = student[0]
        name = student[1]

        status = "Present" if roll in present_students else "Absent"

        cursor.execute(
            """
            INSERT INTO attendance
            (roll_no,name,date,time,status)
            VALUES(%s,%s,%s,%s,%s)
            """,
            (roll, name, today, current_time, status),
        )

    db.commit()

    return redirect("/report")


# ===================================================
# REPORT
# ===================================================
@app.route("/report")
def report():
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT
        date,
        roll_no,
        name,
        status
        FROM attendance
        ORDER BY date DESC
        """
    )

    records = cursor.fetchall()

    return render_template("report.html", records=records)


@app.route("/export_excel")
def export_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance Report"

    ws.append(["Date", "Roll No", "Name", "Status"])

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT date,
               roll_no,
               name,
               status
        FROM attendance
        ORDER BY date DESC
        """
    )

    records = cursor.fetchall()

    for row in records:
        ws.append(row)

    file_name = "Attendance_Report.xlsx"
    wb.save(file_name)

    return send_file(file_name, as_attachment=True)


# ===================================================
# RUN
# ===================================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
