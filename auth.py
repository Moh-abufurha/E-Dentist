import sqlite3

DB_NAME = "clinic.db"

def verify_patient(phone: str, verification_code: str):

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT a.id
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE p.phone = ? 
                  AND a.verification_code = ?
                  AND a.status != 'cancelled';
            """, (phone.strip(), verification_code.strip()))
            result = cur.fetchone()

        if result:
            return {
                "success": True,
                "message": "✅ Verification successful.",
                "appointment_id": result[0],
            }
        else:
            return {
                "success": False,
                "message": "❌ Invalid phone number or verification code."
            }

    except Exception as e:
        return {"success": False, "message": f"⚠️ Error verifying patient: {e}"}
