import os
import json
import warnings
import google.generativeai as genai
from google.generativeai import types
from google.ai.generativelanguage_v1beta.types import Content, Part
from auth import verify_patient
from memory_manager import save_turn, load_recent
from tools import (
    get_services_tool,
    book_appointment_tool,
    ensure_patient_tool,
    cancel_appointment_tool,
    reschedule_appointment_tool,
)

os.environ["GEMINI_API_KEY"] = "AIzaSyCxG0o8YfEcMxEC_b1EkAh_zaDzgLECbE4"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
genai.configure(api_key=GOOGLE_API_KEY)

MODEL = "models/gemini-2.5-flash"
warnings.filterwarnings("ignore", category=UserWarning)

SYSTEM_PROMPT = """
You are a bilingual medical assistant that autonomously helps patients book, cancel, or reschedule appointments.

Behavior:
- Think step-by-step to complete the full workflow.
- Ask for missing details naturally (name, phone, service, date, time).
- Automatically call tools in the correct order: ensure_patient → get_services → book_appointment.
- Keep track of patient_id and phone once known.
- Stop only when the booking (or cancellation) is fully confirmed.
- Always speak in the user's language (Arabic or English).

Rules:
- Never say the appointment is booked unless `book_appointment` succeeded and returned a verification_code.
- Keep responses short and natural.
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
        recent = load_recent(session["context"]["user_phone"], k=3)
        if recent:
            for turn in recent:
                session["history"].append(Content(role=turn["role"], parts=[Part(text=turn["message"])]))

def execute_action(name: str, args: dict, session: dict = None):
    try:
        if name == "ensure_patient":
            result = ensure_patient_tool(**args)
            if result["success"] and session is not None:
                ctx = session.setdefault("context", {})
                ctx["patient_id"] = result.get("patient_id")
                ctx["full_name"] = args.get("full_name")
                ctx["user_phone"] = args.get("phone")
                result["message"] += " Patient verified. Please provide service, date, and time to continue."
            return result
        elif name == "get_services":
            return get_services_tool()
        elif name == "book_appointment":
            return book_appointment_tool(**args)
        elif name == "verify_patient":
            return verify_patient(**args)
        elif name == "cancel_appointment":
            return cancel_appointment_tool(**args)
        elif name == "reschedule_appointment":
            return reschedule_appointment_tool(**args)
        else:
            return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"error": str(e)}

MAX_STEPS = 10

def run_agent_stream(user_text: str, session: dict):
    if session is None:
        raise ValueError("session must be provided.")

    _load_context_if_any(session)
    _append("user", user_text, session)
    session["history"] = session["history"][-6:]

    ctx = session.get("context", {})
    context_summary = []
    if ctx.get("full_name"):
        context_summary.append(f"Full name: {ctx['full_name']}")
    if ctx.get("user_phone"):
        context_summary.append(f"Phone: {ctx['user_phone']}")
    if ctx.get("patient_id"):
        context_summary.append(f"Patient ID: {ctx['patient_id']}")
    if context_summary:
        session["history"].append(
            Content(role="user", parts=[Part(text="Context: " + ", ".join(context_summary))])
        )

    model_local = _build_model([make_tools()])
    step = 0

    while step < MAX_STEPS:
        step += 1
        buffered_text = []
        tool_call = None

        try:
            stream = model_local.generate_content(contents=session["history"], stream=True)
            for chunk in stream:
                if not getattr(chunk, "candidates", None):
                    continue
                for cand in chunk.candidates:
                    if not getattr(cand, "content", None):
                        continue
                    for p in cand.content.parts:
                        if getattr(p, "function_call", None):
                            tool_call = {
                                "name": p.function_call.name,
                                "args": dict(p.function_call.args or {})
                            }
                            break
                        elif getattr(p, "text", None):
                            text = p.text.strip()
                            if text:
                                buffered_text.append(text)
                                yield text
                    if tool_call:
                        break
                if tool_call:
                    break

        except Exception as e:
            yield f"Streaming error: {e}"
            continue

        out_text = "".join(buffered_text).strip()

        if tool_call:
            if out_text:
                _append("model", out_text, session)
            else:
                _append("model", "[Notice] Function call emitted with no text.", session)
            try:
                result = execute_action(tool_call["name"], tool_call["args"], session)
            except Exception as e:
                yield f"Tool error: {str(e)}"
                continue

            tool_note = f"[Tool executed] {json.dumps({'tool': tool_call['name'], 'args': tool_call['args'], 'result': result}, ensure_ascii=False)}"
            _append("model", tool_note, session)
            continue

        if out_text:
            _append("model", out_text, session)
            if any(end_kw in out_text.lower() for end_kw in [
                "تم", "successful", "code", "التحقق", "complete", "completed"
            ]):
                break

    yield "Conversation complete."
