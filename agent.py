import os, json, asyncio
from typing import AsyncGenerator
from live_api_client import LiveAPISession
from tools import (
    get_services_tool, book_appointment_tool, ensure_patient_tool,
    cancel_appointment_tool, reschedule_appointment_tool,
)
from auth import verify_patient
from memory_manager import save_turn, load_recent
from google import genai
import os
os.environ["GEMINI_API_KEY"] = "AIzaSyDe0k7U0qhQqUCSvW82Eugw9-YqTlfTXU0"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
if not GOOGLE_API_KEY:
    raise RuntimeError("Set GOOGLE_API_KEY (or GEMINI_API_KEY) in environment for TTS.")

client = genai.Client(api_key=GOOGLE_API_KEY)


SYSTEM_PROMPT = """
You are a bilingual medical assistant that autonomously helps patients book, cancel, or reschedule appointments.
- Ask for missing details naturally (name, phone, service, date, time).
- Tools order: ensure_patient → get_services → book_appointment.
- Track patient_id and phone once known.
- Never claim booking success unless `book_appointment` returned verification_code.
- Reply in user's language.
"""

def make_tools_schema_for_live():
    return [
        {"name": "get_services", "description": "List available services and doctors.", "schema": {}},
        {"name": "book_appointment", "description": "Book appointment.", "schema": {
            "type": "object","properties":{
                "patient_id":{"type":"number"},"service_id":{"type":"number"},
                "date":{"type":"string"},"time":{"type":"string"}},
            "required":["patient_id","service_id","date","time"]}},
        {"name": "ensure_patient", "description": "Ensure or create patient.", "schema":{
            "type":"object","properties":{
                "full_name":{"type":"string"},"phone":{"type":"string"}},
            "required":["full_name","phone"]}},
        {"name":"cancel_appointment","description":"Cancel appointment.","schema":{
            "type":"object","properties":{
                "phone":{"type":"string"},"verification_code":{"type":"string"}},
            "required":["phone","verification_code"]}},
        {"name":"reschedule_appointment","description":"Reschedule appointment.","schema":{
            "type":"object","properties":{
                "phone":{"type":"string"},"verification_code":{"type":"string"},
                "new_date":{"type":"string"},"new_time":{"type":"string"}},
            "required":["phone","verification_code","new_date","new_time"]}},
    ]

def execute_action(name: str, args: dict, session: dict = None):
    if name == "ensure_patient":
        result = ensure_patient_tool(**args)
        if result.get("success") and session is not None:
            ctx = session.setdefault("context", {})
            ctx["patient_id"] = result.get("patient_id")
            ctx["full_name"] = args.get("full_name")
            ctx["user_phone"] = args.get("phone")
        return result
    if name == "get_services": return get_services_tool()
    if name == "book_appointment": return book_appointment_tool(**args)
    if name == "cancel_appointment": return cancel_appointment_tool(**args)
    if name == "reschedule_appointment": return reschedule_appointment_tool(**args)
    if name == "verify_patient": return verify_patient(**args)
    return {"error": f"Unknown tool: {name}"}

async def run_agent_stream(user_text: str, session: dict) -> AsyncGenerator[str, None]:
    if session is None:
        raise ValueError("session must be provided.")

    if "context" in session and "user_phone" in session["context"]:
        for turn in load_recent(session["context"]["user_phone"], k=3):
            pass

    # تهيئة جلسة الـ Live API
    tools_schema = make_tools_schema_for_live()
    ctx_payload = {
        "lang": session.get("context", {}).get("lang", "ar"),
        "patient_id": session.get("context", {}).get("patient_id"),
        "user_phone": session.get("context", {}).get("user_phone"),
    }

    async with LiveAPISession(
        api_key=GOOGLE_API_KEY,
        model="models/gemini-2.0-flash",
        system_instruction=SYSTEM_PROMPT,
        tools=tools_schema,
        response_modalities=["TEXT"],
        turn_detection={"type": "server", "threshold": 0.5},
        max_output_tokens=256,
        context_payload=ctx_payload
    ) as live:
        async for piece in live.send_text(user_text, commit=True):
            yield piece
