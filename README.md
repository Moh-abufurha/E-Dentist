🩺 Medical AI Voice Assistant



An intelligent real-time bilingual (Arabic/English) medical voice assistant that listens, understands, and speaks naturally. It helps patients **book, cancel, verify, and reschedule appointments** using **Gemini 2.5 Flash** and a local **SQLite database** 

It also includes a Tkinter-based desktop interface (app.py) for easy interaction with the assistant in real-time..



---

 🚀 Features



* 🎙️ Real-time **Speech-to-Text (STT)** using Google Speech Recognition

* 🧠 **LLM-powered reasoning** with Gemini 2.5 Flash

* 🔊 **Text-to-Speech (TTS)** using Gemini voices (Callisto / Callirrhoe)

* 🗂️ Local **SQLite database** for patients, services, and appointments

* 🧾 Intelligent conversation memory system per patient

* 🧩 Modular agentic architecture (tools, memory, logic)

* 💬 Bilingual interaction (Arabic ↔ English)

* 🖥️ Simple desktop **GUI (Tkinter)** for starting, stopping, and viewing conversations in real-time.





---



🧱 Project Structure



medical-agent/

├── app.py               # Graphical user interface (Tkinter) for real-time interaction

├── agent.py             # LLM logic, reasoning, and tool-calling system

├── voice_realtime.py    # Real-time voice loop (STT → LLM → TTS)

├── auth.py              # Patient verification logic

├── db_init.py           # Database setup and seeding

├── tools.py             # Tools for booking, cancelling, rescheduling

├── memory_manager.py    # Stores and retrieves past conversation turns

├── test_db.py           # View database contents

└── README.md            # Documentation





---



🧠 System Overview



1️⃣ Speech-to-Text (STT)



* Converts user voice (Arabic or English) into text using **Google SpeechRecognition**.



2️⃣ Reasoning (LLM)



* The **Gemini 2.5 Flash** model interprets the text, determines intent, and decides which tool to call.



3️⃣ Database Actions



* Executes real-world logic such as creating patients, booking or rescheduling appointments using SQLite.



 4️⃣ Text-to-Speech (TTS)



* Responds naturally using Gemini’s **Callisto (English)** or **Callirrhoe (Arabic)** voices.



 5️⃣ User Interface (GUI)

* The app.py file provides a friendly graphical interface to interact with the assistant, record audio, and display conversation logs.

 



---



🧩 Core Components



| File                | Description                                                             |

| ------------------- | ----------------------------------------------------------------------- |

| agent.py          | Core agent logic – handles memory, planning, and Gemini tool calls.     |

| voice_realtime.py | Handles audio recording, silence detection, and live responses.         |

| tools.py          | Implements actions: booking, canceling, rescheduling, listing services. |

| auth.py           | Verifies patients using phone and verification codes.                   |

| db_init.py        | Initializes database tables and seeds test data.                        |

| memory_manager.py | Saves and loads previous chat history.                                  |

| test_db.py        | Simple script to view database tables.                                  |



---



⚙️ Installation & Setup

1️⃣ Clone the Repository



bash

https://github.com/Moh-abufurha/E-Dentist.git





2️⃣ Install Dependencies



bash

pip install -r requirements.txt





Required Packages:



google-genai

sounddevice

simpleaudio

speechrecognition

numpy

pydub





3️⃣ Set Environment Variables



Create a .env file:



GEMINI_API_KEY=your_api_key_here





Or set it directly:



bash

export GEMINI_API_KEY=your_api_key_here





4️⃣ Initialize Database



bash

python db_init.py





5️⃣ Run the GUI Version



If you prefer a graphical interface:



bash

python app.py



---

 🧬 Database Schema



 Patients



| id | full_name | phone | verified |



 Services



| id | name | doctor_name |



Appointments



| id | patient_id | service_id | date | time | status | verification_code |



Conversation Memory



| id | user_phone | role | message | created_at |



---



🧠 Tools Summary



| Tool                          | Description                                           |

| ----------------------------- | ----------------------------------------------------- |

| `ensure_patient_tool`         | Ensures patient record exists or creates a new one.   |

| `get_services_tool`           | Lists all available medical services.                 |

| `book_appointment_tool`       | Books an appointment and generates verification code. |

| `cancel_appointment_tool`     | Cancels an existing appointment.                      |

| `reschedule_appointment_tool` | Reschedules appointment with new date/time.           |

  
