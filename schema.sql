-- ============================================================
-- Cloud Attendance System - Database Schema (MySQL)
-- ============================================================
-- Run this against your cloud MySQL database before first use:
--
--   mysql -h <DB_HOST> -P <DB_PORT> -u <DB_USER> -p <DB_NAME> < schema.sql
--
-- Or paste the contents into your provider's SQL console
-- (PlanetScale, Aiven, Railway, etc.).
--
-- The table/column names below are derived directly from the
-- queries in app.py and must match exactly.
-- ============================================================

-- ------------------------------------------------------------
-- students
-- ------------------------------------------------------------
-- roll_no is the natural key used throughout the app
-- (register, edit, delete, attendance joins).
CREATE TABLE IF NOT EXISTS students (
    roll_no     VARCHAR(50)  NOT NULL,
    name        VARCHAR(120) NOT NULL,
    department  VARCHAR(120) NOT NULL,
    semester    VARCHAR(20)  NOT NULL,
    email       VARCHAR(160) NOT NULL,
    PRIMARY KEY (roll_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- attendance
-- ------------------------------------------------------------
-- attendance_id is auto-increment (app orders by it DESC).
-- One row is inserted per student per attendance run.
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INT          NOT NULL AUTO_INCREMENT,
    roll_no       VARCHAR(50)  NOT NULL,
    name          VARCHAR(120) NOT NULL,
    date          DATE         NOT NULL,
    time          TIME         NOT NULL,
    status        VARCHAR(20)  NOT NULL,
    PRIMARY KEY (attendance_id),
    KEY idx_attendance_date (date),
    KEY idx_attendance_roll (roll_no),
    CONSTRAINT fk_attendance_student
        FOREIGN KEY (roll_no) REFERENCES students (roll_no)
        ON UPDATE CASCADE
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Optional: seed a sample student to verify the setup.
-- Safe to remove.
-- ------------------------------------------------------------
-- INSERT INTO students (roll_no, name, department, semester, email)
-- VALUES ('CS001', 'Test Student', 'Computer Science', '1', 'test@example.com');
