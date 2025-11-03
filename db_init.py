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
        doctor_name TEXT NOT NULL
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

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully.")


def seed_db():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()

        cur.execute("DELETE FROM patients;")
        cur.execute("DELETE FROM services;")
        cur.execute("DELETE FROM appointments;")

        patients = [
            ("Moh Ahmed", "0790000001", 1),
            ("Sara Hussain", "0790000002", 1),
        ]
        cur.executemany(
            "INSERT INTO patients (full_name, phone, verified) VALUES (?, ?, ?);",
            patients,
        )

        services = [
            ("Teeth Check", "Dr. Mahdi"),
            ("Teeth Cleaning", "Dr. Ahmed"),
            ("Dental Filling", "Dr. Sara"),
        ]
        cur.executemany(
            "INSERT INTO services (name, doctor_name) VALUES (?, ?);",
            services,
        )

        cur.execute("""
            INSERT INTO appointments 
            (patient_id, service_id, date, time, status, verification_code)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (1, 1, "2025-11-10", "10:00", "confirmed", "1234"))

        conn.commit()
        print("🌱 Seed data added successfully.")


if __name__ == "__main__":
    init_db()
    seed_db()
