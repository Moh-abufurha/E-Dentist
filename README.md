🩺 Medical AI Voice Assistant
An intelligent real-time bilingual (Arabic/English) medical voice assistant that listens, understands, and speaks naturally.
It helps patients book, cancel, verify, and reschedule appointments using Gemini 2.5 Flash and a local SQLite database.
A Tkinter-based desktop interface (app.py) allows real-time interaction and voice testing.

🚀 Features
🎙️ Real-time Speech-to-Text (STT) using Google Speech Recognition

🧠 LLM-powered reasoning with Gemini 2.5 Flash

🔊 Text-to-Speech (TTS) using Gemini voices (Callisto for English / Callirrhoe for Arabic)

🗂️ Local SQLite database for patients, services, and appointments

🧾 Persistent conversation memory per patient

🧩 Agentic modular architecture (tools + logic + memory)

💬 Bilingual support (Arabic ↔ English)

🖥️ Simple Tkinter GUI for recording, stopping, and viewing chat logs

🧱 Project Structure
graphql
نسخ الكود
medical-agent/
├── app.py               # Tkinter GUI for live interaction
├── agent.py             # Core LLM reasoning & tool-calling logic
├── voice_realtime.py    # Handles STT → LLM → TTS streaming loop
├── auth.py              # Patient verification logic (rate-limited)
├── db_init.py           # Creates & seeds the SQLite database
├── tools.py             # Booking / cancelling / rescheduling / logging tools
├── memory_manager.py    # Saves & retrieves conversation history
├── test_db.py           # Utility to inspect database tables
└── README.md
🧠 System Overview
1️⃣ Speech-to-Text (STT)
Captures patient voice in Arabic or English and converts it to text using Google SpeechRecognition.

2️⃣ Reasoning (LLM)
The Gemini 2.5 Flash model interprets intent and selects the proper tool (book_appointment, cancel_appointment, etc.).

3️⃣ Database Actions
Executes real-world logic via SQLite:

Creates patients

Books / cancels / reschedules appointments

Verifies identity with a 4-digit code

4️⃣ Text-to-Speech (TTS)
Generates natural speech replies using Gemini TTS (Flash Exp) voices, then plays them instantly.

5️⃣ GUI Interface
app.py offers a desktop interface to start / stop recording and view real-time dialogue.

🧩 Core Components
File	Description
agent.py	LLM reasoning engine + tool invocation logic using Gemini 2.5 Flash
voice_realtime.py	Handles live voice loop, speech segmentation, latency timing, and TTS playback
tools.py	Implements all actions (book, cancel, reschedule, verify, log)
auth.py	Secure verification (3-attempt limit per 10 min)
db_init.py	Builds & seeds database with sample services and patients
memory_manager.py	Stores recent conversation turns per patient in conversation_memory
test_db.py	Simple table viewer for debugging the database

⚙️ Installation & Setup
1️⃣ Clone the Repository
bash
نسخ الكود
git clone https://github.com/Moh-abufurha/E-Dentist.git
cd E-Dentist
2️⃣ Install Dependencies
bash
نسخ الكود
pip install -r requirements.txt
Key Packages

نسخ الكود
google-genai
google-generativeai
google-ai-generativelanguage
sounddevice
simpleaudio
SpeechRecognition
pydub
numpy
torch
faster-whisper
3️⃣ Set Environment Variables
Create .env file:

ini
نسخ الكود
GEMINI_API_KEY=your_api_key_here
or:

bash
نسخ الكود
export GEMINI_API_KEY=your_api_key_here
4️⃣ Initialize the Database
bash
نسخ الكود
python db_init.py
(Creates and seeds tables for patients, services, appointments, and logs.)

5️⃣ Run the GUI
bash
نسخ الكود
python app.py
Then press “Start Speaking” to begin interacting with the assistant.

🧬 Database Schema
Patients
| id | full_name | phone | verified |

Services
| id | name | doctor_name | date | time |

Appointments
| id | patient_id | service_id | date | time | status | verification_code |

Conversation Memory
| id | user_phone | role | message | created_at |

🧰 Tools Summary
Tool	Description
ensure_patient_tool	Verifies or creates a patient record
get_services_tool	Lists available services & doctors
book_appointment_tool	Books an appointment and generates a 4-digit code
cancel_appointment_tool	Cancels an existing appointment
reschedule_appointment_tool	Reschedules with new date and time
verify_patient_tool	Checks patient verification status

⏱️ Performance Metrics
Each interaction logs latency in milliseconds:

yaml
نسخ الكود
⏱️ Latency → STT: 650 ms | LLM: 1200 ms | TTS: 800 ms | TOTAL: ~2.6 s
🧩 Architecture Highlights
Agentic loop (Gemini reasoning → tool execution → context update)

Streaming responses with real-time speech generation

Context memory persisted by phone number

Echo-free TTS playback and silence detection

Arabic + English voice support (Callirrhoe / Callisto)

🩵 Author
Mohammed R. Abufurha

