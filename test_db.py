import sqlite3
DB_NAME = "clinic.db"

def show_table(table_name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table_name}")
    rows= cur.fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    print("Patients:", show_table("patients"))
    print("Services:", show_table("services"))
    print("Appointments:", show_table("appointments"))
