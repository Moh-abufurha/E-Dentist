import os
import json
import warnings
from tools import log_action
import google.generativeai as genai
from google.generativeai import types
from google.ai.generativelanguage_v1beta.types import Content, Part
from memory_manager import save_turn, load_recent
from tools import (
    get_services_tool,
    book_appointment_tool,
    ensure_patient_tool,
    cancel_appointment_tool,
    reschedule_appointment_tool,
    verify_patient_tool,
)

os.environ["GEMINI_API_KEY"] = "AIzaSyDe0k7U0qhQqUCSvW82Eugw9-YqTlfTXU0"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
genai.configure(api_key=GOOGLE_API_KEY)

MODEL = "models/gemini-2.5-flash"
warnings.filterwarnings("ignore", category=UserWarning)

SYSTEM_PROMPT = """
You are the AI receptionist of a dental clinic — a bilingual (Arabic/English) intelligent medical assistant agent.
You help patients manage clinic appointments by reasoning step-by-step and using available tools correctly.

Core Behavior
- Think step-by-step internally before taking any action (do not explain reasoning to the user).
- Always respond in the same language the user used (Arabic ↔ English).
- Keep responses friendly, clear, and concise while following the defined workflow.
- Ask the user for any missing required details naturally before calling any tool.

Workflow Logic
1. Patient Identification
   - Ask for the patient's full name and phone number.
   - Call ensure_patient to verify or create the patient record.
   - Remember patient_id and phone in context once known.

2. Service Selection
   - Ask which service the patient wants (e.g., cleaning, filling, extraction).
   - Use get_services to show available services and doctors.

3. Appointment Booking
   - Ask for date and time (if missing).
   - Call book_appointment only when all required info is ready.
   - Confirm the booking ONLY if a verification_code is returned.

4. Changes or Cancellations
   - If the user wants to cancel, call cancel_appointment.
   - If the user wants to change a booking, call reschedule_appointment.

5. Verification
   - If the patient needs to be verified again, use verify_patient.

Rules & Constraints
- Never call a tool unless all required inputs are available.
- Never claim a booking/cancellation succeeded unless the tool returns success=True and a valid verification_code or confirmation message.
- Always store tool results in context (patient_id, service_id, verification_code).
- Always explain errors gently to the user in simple terms.
- End the conversation politely once the process is fully complete.

Output Format
All tool responses and reasoning outputs must follow this structure:
{
  "success": true/false,
  "message": "short description",
  "data": {...relevant details...}
}

Example:
User: "احجزلي تنظيف أسنان بكرة"
→ Agent: "أكيد، ممكن اسمك ورقم تلفونك أولًا؟"
→ Then calls tools step-by-step until booking is confirmed.
"""

def make_tools():
    return types.Tool(function_declarations=[
        types.FunctionDeclaration(name="get_services", description="List available services and doctors."),
        types.FunctionDeclaration(
            name="book_appointment",
            description="Book an appointment after collecting service, date, and time.",
            parameters={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "number"},
                    "service_id": {"type": "number"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                },
                "required": ["patient_id", "service_id", "date", "time"]
            }
        ),
        types.FunctionDeclaration(
            name="ensure_patient",
            description="Ensure patient exists or create new one.",
            parameters={
                "type": "object",
                "properties": {"full_name": {"type": "string"}, "phone": {"type": "string"}},
                "required": ["full_name", "phone"]
            }
        ),
        types.FunctionDeclaration(
            name="verify_patient",
            description="Verify patient identity using phone number.",
            parameters={
                "type": "object",
                "properties": {"phone": {"type": "string"}},
                "required": ["phone"]
            }
        ),
        types.FunctionDeclaration(
            name="cancel_appointment",
            description="Cancel appointment using phone and verification code.",
            parameters={
                "type": "object",
                "properties": {"phone": {"type": "string"}, "verification_code": {"type": "string"}},
                "required": ["phone", "verification_code"]
            }
        ),
        types.FunctionDeclaration(
            name="reschedule_appointment",
            description="Reschedule appointment using phone, code, new date & time.",
            parameters={
                "type": "object",
                "properties": {
                    "phone": {"type": "string"},
                    "verification_code": {"type": "string"},
                    "new_date": {"type": "string"},
                    "new_time": {"type": "string"},
                },
                "required": ["phone", "verification_code", "new_date", "new_time"]
            }
        ),
    ])

def _build_model(tools):
    return genai.GenerativeModel(MODEL, system_instruction=SYSTEM_PROMPT, tools=tools)

def _append(role: str, text: str, session: dict):
    session.setdefault("history", []).append(Content(role=role, parts=[Part(text=text)]))
    try:
        user_phone = session.get("context", {}).get("user_phone")
        save_turn(user_phone, role, text)
    except Exception:
        pass

def _load_context_if_any(session):
    if "context" in session and "user_phone" in session["context"]:
        recent = load_recent(session["context"]["user_phone"], k=6)
        if recent:
            for turn in recent:
                session["history"].append(Content(role=turn["role"], parts=[Part(text=turn["message"])]))

def execute_action(name: str, args: dict, session: dict = None):
    try:
        if name == "ensure_patient":
            result = ensure_patient_tool(**args)
            if result["success"] and session is not None:
                ctx = session.setdefault("context", {})
                data = result.get("data") or {}
                ctx["patient_id"] = data.get("patient_id")
                ctx["full_name"] = args.get("full_name")
                ctx["user_phone"] = args.get("phone")
                result["message"] += " Patient verified. Please provide service, date, and time to continue."
        elif name == "get_services":
            result = get_services_tool()
        elif name == "book_appointment":
            result = book_appointment_tool(**args)
        elif name == "verify_patient":
            result = verify_patient_tool(**args)
        elif name == "cancel_appointment":
            result = cancel_appointment_tool(**args)
        elif name == "reschedule_appointment":
            result = reschedule_appointment_tool(**args)
        else:
            result = {"success": False, "message": f"Unknown tool: {name}", "data": None}
        log_action("tool_call", f"{name} executed successfully", session.get("context", {}).get("user_phone"))
        session.setdefault("context", {})["last_result"] = result
        return result
    except Exception as e:
        log_action("tool_error", f"{name} failed: {e}")
        return {"success": False, "message": str(e), "data": None}

MAX_STEPS = 10

def run_agent_stream(user_text: str, session: dict):
    if session is None:
        raise ValueError("session must be provided.")
    _load_context_if_any(session)
    _append("user", user_text, session)
    model = _build_model(make_tools())
    ctx = session.setdefault("context", {})
    step = 0
    while step < MAX_STEPS:
        step += 1
        tool_call = None
        try:
            stream = model.generate_content(contents=session["history"], stream=True)
            for chunk in stream:
                if not getattr(chunk, "candidates", None):
                    continue
                for cand in chunk.candidates:
                    if not getattr(cand, "content", None):
                        continue
                    for part in cand.content.parts:
                        if getattr(part, "text", None):
                            text = part.text.strip()
                            if text:
                                yield text
                                _append("model", text, session)
                        elif getattr(part, "function_call", None):
                            tool_call = {
                                "name": part.function_call.name,
                                "args": dict(part.function_call.args or {})
                            }
                            break
                    if tool_call:
                        break
                if tool_call:
                    break
        except Exception as e:
            yield f"Streaming error: {e}"
            continue
        if tool_call:
            result = execute_action(tool_call["name"], tool_call["args"], session)
            _append("model", f"[Tool executed] {tool_call['name']}: {json.dumps(result, ensure_ascii=False)}", session)
            continue
        last_result = session.get("context", {}).get("last_result", {})


        if isinstance(last_result, list):
            data = {}
        elif isinstance(last_result, dict):
            data = last_result.get("data", {}) or {}
        else:
            data = {}

        if isinstance(data, dict) and data.get("verification_code"):
            break

    yield "Conversation complete."
