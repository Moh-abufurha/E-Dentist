import sqlite3
from datetime import datetime
import random

DB_NAME = "clinic.db"


# 🧠 توحيد طريقة التخزين والبحث (كلها lowercase)
def normalize_inputs(full_name=None, phone=None, doctor_name=None):
    """Normalize all text fields to lowercase for consistent storage/search."""
    if full_name:
        full_name = full_name.strip().lower()
    if phone:
        phone = phone.strip()
    if doctor_name:
        doctor_name = doctor_name.strip().lower()
        if not doctor_name.startswith("dr."):
            doctor_name = "dr. " + doctor_name.replace("dr. ", "")
    return full_name, phone, doctor_name


def log_action(event: str, detail: str, action_by: str = None):
    """Log actions safely into audit_logs (ignore if table missing)."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO audit_logs (event, detail, action_by) VALUES (?, ?, ?)",
                (event, detail, action_by),
            )
            conn.commit()
    except Exception:
        pass

def ensure_patient_tool(full_name: str, phone: str):
    full_name, phone, _ = normalize_inputs(full_name, phone)
    if not full_name or not phone:
        return {
            "success": False,
            "message": "Missing full name or phone.",
            "patient_id": None,
        }

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        # ✅ تحقق من وجود المريض مسبقًا
        cur.execute(
            "SELECT id FROM patients WHERE phone=?",
            (phone,),
        )
        row = cur.fetchone()

        if row:
            patient_id = row[0]
            msg = "Existing patient found."
        else:
            cur.execute(
                "INSERT INTO patients (full_name, phone, verified) VALUES (?, ?, 1)",
                (full_name, phone),
            )
            conn.commit()
            patient_id = cur.lastrowid
            msg = "New patient record created."

    log_action("ensure_patient", msg, full_name)
    return {"success": True, "message": msg, "patient_id": patient_id}


# 🩺 عرض الخدمات
def get_services_tool():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name, doctor_name FROM services;")
            rows = cur.fetchall()
            return {
                "success": True,
                "message": "Services fetched successfully.",
                "data": [{"id": i, "name": n, "doctor_name": d} for (i, n, d) in rows],
            }
    except Exception as e:
        return {"success": False, "message": str(e), "data": None}


# 🗓️ حجز موعد جديد
def book_appointment_tool(patient_id: int, service_id: int, date: str, time: str):
    try:
        if "/" in date:
            date = datetime.strptime(date, "%d/%m/%Y").strftime("%Y-%m-%d")

        verification_code = str(random.randint(1000, 9999))
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO appointments (patient_id, service_id, date, time, status, verification_code)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (patient_id, service_id, date, time.strip().lower(), "confirmed", verification_code),
            )
            conn.commit()

        log_action(
            "book_appointment",
            f"Patient {patient_id} booked service {service_id}.",
            str(patient_id),
        )
        return {
            "success": True,
            "message": f"Booked for {date} at {time}.",
            "verification_code": verification_code,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error booking: {e}",
            "verification_code": None,
        }
def cancel_appointment_tool(phone: str, verification_code: str):

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT a.id
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE p.phone = ? AND a.verification_code = ? AND a.status != 'cancelled';
            """, (phone.strip(), verification_code.strip()))
            row = cur.fetchone()

            if not row:
                return {"success": False, "message": "❌ No active appointment found for this phone and code."}

            appointment_id = row[0]
            cur.execute("""
                UPDATE appointments
                SET status='cancelled', updated_at=datetime('now')
                WHERE id=?;
            """, (appointment_id,))
            conn.commit()

        log_action("cancel_appointment", f"Appointment {appointment_id} cancelled via phone {phone}", phone)

        return {"success": True, "message": "✅ Appointment cancelled successfully."}

    except Exception as e:
        return {"success": False, "message": f"⚠️ Error cancelling appointment: {e}"}
def reschedule_appointment_tool(phone: str, verification_code: str, new_date: str, new_time: str):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()

            # 🔍 تحقق أن الموعد موجود لنفس رقم الهاتف والكود
            cur.execute("""
                SELECT a.id
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE p.phone = ? 
                  AND a.verification_code = ?
                  AND a.status != 'cancelled';
            """, (phone.strip(), verification_code.strip()))
            row = cur.fetchone()

            if not row:
                return {
                    "success": False,
                    "message": "❌ No active appointment found for this phone and code."
                }

            appointment_id = row[0]

            # 🕒 تحديث الموعد
            cur.execute("""
                UPDATE appointments
                SET date=?, time=?, updated_at=datetime('now')
                WHERE id=?;
            """, (new_date.strip(), new_time.strip(), appointment_id))
            conn.commit()

        log_action("reschedule_appointment", f"Rescheduled appointment {appointment_id} to {new_date} {new_time}", phone)

        return {"success": True, "message": f"✅ Appointment rescheduled to {new_date} at {new_time}."}

    except Exception as e:
        return {"success": False, "message": f"⚠️ Error while rescheduling: {e}"}
