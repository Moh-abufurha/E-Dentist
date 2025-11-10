import sqlite3
from datetime import datetime
import random

DB_NAME = "clinic.db"

def normalize_inputs(full_name=None, phone=None, doctor_name=None):
    if full_name:
        full_name = full_name.strip().lower()
    if phone:
        phone = phone.strip()
    if doctor_name:
        doctor_name = doctor_name.strip().lower()
        if not doctor_name.startswith("dr."):
            doctor_name = "dr. " + doctor_name.replace("dr. ", "")
    return full_name, phone, doctor_name

def normalize_date(date_str: str) -> str:
    try:
        if "/" in date_str:
            return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        elif "-" in date_str:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        pass
    return date_str

def log_action(event: str, detail: str, action_by: str = None):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO audit_logs (event, detail, action_by) VALUES (?, ?, ?)",
                (event, detail, action_by),
            )
            conn.commit()
    except Exception as e:
        print("Log error:", e)

def ensure_patient_tool(full_name: str, phone: str):
    full_name, phone, _ = normalize_inputs(full_name, phone)
    if not full_name or not phone:
        return {"success": False, "message": "Missing full name or phone.", "data": None}
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM patients WHERE phone=?", (phone,))
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
        return {"success": True, "message": msg, "data": {"patient_id": patient_id}}
    except Exception as e:
        log_action("ensure_patient_error", str(e))
        return {"success": False, "message": f"Error: {e}", "data": None}

def verify_patient_tool(phone: str):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM patients WHERE phone=? AND verified=1;",
                (phone.strip(),),
            )
            row = cur.fetchone()
            if row:
                log_action("verify_patient", f"Patient {phone} verified.", phone)
                return {"success": True, "message": "Patient verified.", "data": {"patient_id": row[0]}}
            else:
                return {"success": False, "message": "No verified patient found.", "data": None}
    except Exception as e:
        log_action("verify_patient_error", str(e))
        return {"success": False, "message": f"Error verifying patient: {e}", "data": None}

def get_services_tool():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name, doctor_name, date, time FROM services;")
            rows = cur.fetchall()
            services = [
                {"id": i, "name": n, "doctor_name": d, "date": dt, "time": tm}
                for (i, n, d, dt, tm) in rows
            ]
            return {"success": True, "message": "Services fetched successfully.", "data": services}
    except Exception as e:
        log_action("get_services_error", str(e))
        return {"success": False, "message": f"Error fetching services: {e}", "data": None}

def book_appointment_tool(patient_id: int, service_id: int, date: str = None, time: str = None):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            if not date or not time:
                cur.execute("SELECT date, time FROM services WHERE id=?", (service_id,))
                row = cur.fetchone()
                if not row:
                    return {"success": False, "message": "Service not found.", "data": None}
                date, time = row
            date = normalize_date(date)
            cur.execute("""
                SELECT COUNT(*) FROM appointments a
                JOIN services s ON a.service_id = s.id
                WHERE s.doctor_name = (SELECT doctor_name FROM services WHERE id=?)
                  AND a.date = ?
                  AND a.time = ?
                  AND a.status != 'cancelled';
            """, (service_id, date, time))
            (count,) = cur.fetchone()
            if count > 0:
                return {"success": False, "message": "Doctor already has an appointment at this time.", "data": None}
            verification_code = str(random.randint(1000, 9999))
            cur.execute("""
                INSERT INTO appointments (patient_id, service_id, date, time, status, verification_code)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (patient_id, service_id, date, time.strip(), "confirmed", verification_code))
            conn.commit()
        log_action("book_appointment", f"Patient {patient_id} booked service {service_id}.", str(patient_id))
        return {
            "success": True,
            "message": f"Appointment booked for {date} at {time}.",
            "data": {"verification_code": verification_code, "date": date, "time": time},
        }
    except Exception as e:
        log_action("book_appointment_error", str(e))
        return {"success": False, "message": f"Error booking appointment: {e}", "data": None}

def cancel_appointment_tool(phone: str, verification_code: str):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT a.id FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE p.phone = ? AND a.verification_code = ? AND a.status != 'cancelled';
            """, (phone.strip(), verification_code.strip()))
            row = cur.fetchone()
            if not row:
                return {"success": False, "message": "No active appointment found.", "data": None}
            appointment_id = row[0]
            cur.execute("""
                UPDATE appointments
                SET status='cancelled', updated_at=datetime('now')
                WHERE id=?;
            """, (appointment_id,))
            conn.commit()
        log_action("cancel_appointment", f"Appointment {appointment_id} cancelled.", phone)
        return {"success": True, "message": "Appointment cancelled successfully.", "data": {"appointment_id": appointment_id}}
    except Exception as e:
        log_action("cancel_appointment_error", str(e))
        return {"success": False, "message": f"Error cancelling appointment: {e}", "data": None}

def reschedule_appointment_tool(phone: str, verification_code: str, new_date: str, new_time: str):
    try:
        new_date = normalize_date(new_date)
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT a.id FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE p.phone = ? AND a.verification_code = ? AND a.status != 'cancelled';
            """, (phone.strip(), verification_code.strip()))
            row = cur.fetchone()
            if not row:
                return {"success": False, "message": "No active appointment found.", "data": None}
            appointment_id = row[0]
            cur.execute("""
                UPDATE appointments
                SET date=?, time=?, updated_at=datetime('now')
                WHERE id=?;
            """, (new_date.strip(), new_time.strip(), appointment_id))
            conn.commit()
        log_action("reschedule_appointment", f"Appointment {appointment_id} rescheduled to {new_date} {new_time}", phone)
        return {
            "success": True,
            "message": "Appointment rescheduled successfully.",
            "data": {"appointment_id": appointment_id, "new_date": new_date, "new_time": new_time},
        }
    except Exception as e:
        log_action("reschedule_appointment_error", str(e))
        return {"success": False, "message": f"Error rescheduling: {e}", "data": None}
