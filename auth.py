import sqlite3
from tools import log_action

DB_NAME = "clinic.db"


def verify_patient(phone: str, verification_code: str):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()

            # --- Brute Force Protection ---
            cur.execute("""
                SELECT COUNT(*) FROM audit_logs 
                WHERE event='verify_patient_fail' 
                AND action_by=? 
                AND created_at > datetime('now','-10 minutes');
            """, (phone,))
            attempts = cur.fetchone()[0]

            if attempts >= 3:
                return {
                    "success": False,
                    "message": "Too many failed attempts. Please try again later.",
                    "data": None
                }

            # --- Verify patient using code ---
            cur.execute("""
                SELECT a.id, p.id 
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE p.phone=? AND a.verification_code=?;
            """, (phone, verification_code))
            row = cur.fetchone()

            if not row:
                log_action("verify_patient_fail", f"Failed verification attempt for {phone}", phone)
                return {"success": False, "message": "Invalid verification code.", "data": None}

            # --- Update verified=1 on success ---
            cur.execute("UPDATE patients SET verified=1 WHERE phone=?;", (phone,))
            conn.commit()

            # --- Log successful verification ---
            log_action("verify_patient", f"Patient {phone} verified successfully", phone)

            return {
                "success": True,
                "message": "Verification successful.",
                "data": {"phone": phone}
            }

    except Exception as e:
        log_action("verify_patient_error", f"Error verifying {phone}: {e}", phone)
        return {
            "success": False,
            "message": f"Error verifying patient: {e}",
            "data": None
        }
