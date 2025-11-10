import sqlite3

DB_NAME = "clinic.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()


    cur.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        verified INTEGER DEFAULT 0
    );
    """)



    cur.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        doctor_name TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL
    );
    """)


    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        service_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        status TEXT NOT NULL,
        verification_code TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (patient_id) REFERENCES patients(id),
        FOREIGN KEY (service_id) REFERENCES services(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event TEXT NOT NULL,
        detail TEXT,
        action_by TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS conversation_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_phone TEXT,
        role TEXT,
        message TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone);")


    conn.commit()
    conn.close()
    print("✅ Database initialized successfully.")


def seed_db():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        confirm=input(" ⚠️ -YOU WANT TO DELETE ALL OF DATABASES-IF WANTED PRESS Y ⚠️ ?")
        if confirm == "y"or confirm == "Y":
            cur.execute("DELETE FROM patients;")
            cur.execute("DELETE FROM services;")
            cur.execute("DELETE FROM appointments;")

        services = [
            ("Teeth Check", "Dr. SAMMER ", "2025-11-23", "11:30 AM"),
            ("Teeth Cleaning", "Dr. JOHN ", "2025-11-23", "05:15 PM"),
            ("Dental Filling", "Dr. SARA", "2025-11-23", "01:30 AM"),
            ("Tooth Extraction", "Dr. FARAH", "2025-11-23", "11:30 AM"),
        ]

        cur.executemany(
            "INSERT INTO services (name, doctor_name, date, time) VALUES (?, ?, ?, ?);",
            services,
        )
        conn.commit()
        print(" data added successfully.")


if __name__ == "__main__":
    init_db()
    seed_db()
