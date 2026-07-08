import hashlib
from db.database import connect_db


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_tables():
    conn = connect_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            email    TEXT    UNIQUE NOT NULL,
            password TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS batches (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            timing     TEXT NOT NULL,
            instructor TEXT,
            seats      INTEGER DEFAULT 30
        );

        CREATE TABLE IF NOT EXISTS students (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name  TEXT NOT NULL,
            phone      TEXT,
            email      TEXT,
            course     TEXT,
            batch_id   INTEGER REFERENCES batches(id),
            address    TEXT,
            joined_date TEXT DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS billing (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            total_fee   REAL NOT NULL DEFAULT 0,
            paid_amount REAL NOT NULL DEFAULT 0,
            due_amount  REAL GENERATED ALWAYS AS (total_fee - paid_amount) VIRTUAL
        );

        CREATE TABLE IF NOT EXISTS payments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            billing_id INTEGER NOT NULL REFERENCES billing(id) ON DELETE CASCADE,
            amount     REAL NOT NULL,
            note       TEXT,
            paid_date  TEXT DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS enrollment_details (
            student_id       INTEGER PRIMARY KEY REFERENCES students(id) ON DELETE CASCADE,
            date_of_birth    TEXT,
            education        TEXT,
            university       TEXT,
            professional_exp TEXT,
            company_name     TEXT,
            guardian_name    TEXT,
            guardian_phone   TEXT,
            valid_id         TEXT,
            mode_of_payment  TEXT,
            gst              TEXT,
            transaction_id   TEXT,
            receipt_no       TEXT,
            receipt_date     TEXT,
            inst1_date TEXT, inst1_due REAL, inst1_paid REAL,
            inst2_date TEXT, inst2_due REAL, inst2_paid REAL,
            inst3_date TEXT, inst3_due REAL, inst3_paid REAL
        );
    """)

    # enrollment_details predates these columns — CREATE TABLE IF NOT EXISTS
    # won't add them to an already-existing table, so add them explicitly.
    existing_cols = {row[1] for row in cur.execute("PRAGMA table_info(enrollment_details)")}
    for col in ("ref", "course_fee", "remarks"):
        if col not in existing_cols:
            cur.execute(f"ALTER TABLE enrollment_details ADD COLUMN {col} TEXT")

    # payments predates these columns too — needed for the Fee Receipt slip.
    payment_cols = {row[1] for row in cur.execute("PRAGMA table_info(payments)")}
    for col in ("mode_of_payment", "transaction_id", "instalment_no", "receipt_path"):
        if col not in payment_cols:
            cur.execute(f"ALTER TABLE payments ADD COLUMN {col} TEXT")

    # Seed default admin user if no users exist
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            ("Admin", "admin@school.com", hash_password("admin123"))
        )

    conn.commit()
    conn.close()
