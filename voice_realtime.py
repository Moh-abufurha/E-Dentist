import os
import json
import asyncio
import threading
import numpy as np
import sounddevice as sd
import speech_recognition as sr
import simpleaudio as sa
import queue
from google import genai
from agent import run_agent_stream
os.environ["GEMINI_API_KEY"] = "AIzaSyDe0k7U0qhQqUCSvW82Eugw9-YqTlfTXU0"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
if not GOOGLE_API_KEY:
    raise RuntimeError("Set GOOGLE_API_KEY (or GEMINI_API_KEY) in environment for TTS.")
client = genai.Client(api_key=GOOGLE_API_KEY)


SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_DURATION = 0.5
BLOCK_SIZE = int(SAMPLE_RATE * BLOCK_DURATION)
SILENCE_THRESHOLD = 5.0
MAX_SILENCE_BLOCKS = int(1.0 / BLOCK_DURATION)
MIC_DEVICE_ID = 1

recognizer = sr.Recognizer()
session = {"history": [], "context": {}}
_audio_queue = queue.Queue()


try:
    sd.query_devices(MIC_DEVICE_ID, 'input')
    sd.default.device = MIC_DEVICE_ID
    print(f"✅ Using input device ID = {MIC_DEVICE_ID}")
except Exception:
    sd.default.device = None
    print("⚠️ Using default microphone.")

sd.default.samplerate = SAMPLE_RATE
sd.default.channels = CHANNELS


# 🔊 تشغيل الصوت
def play_audio_bytes(audio_bytes: bytes, sample_rate: int = SAMPLE_RATE):
    try:
        wave_obj = sa.WaveObject(audio_bytes, num_channels=1, bytes_per_sample=2, sample_rate=sample_rate)
        play_obj = wave_obj.play()
        play_obj.wait_done()
    except Exception as e:
        print(f"TTS playback error: {e}")


def text_to_speech_bytes(text: str, lang: str, sample_rate: int = SAMPLE_RATE) -> bytes:
    import io
    from pydub import AudioSegment
    from pydub.effects import speedup

    voice_name = "callisto" if lang == "en" else "callirrhoe"
    try:
        resp = client.models.generate_content(
            model="models/gemini-2.0-flash-exp-tts",
            contents=[{"role": "user", "parts": [{"text": text}]}],
            config={
                "response_modalities": ["AUDIO"],
                "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": voice_name}}},
            },
        )

        if not resp or not getattr(resp, "candidates", None):
            print("⚠️ Gemini-TTS: no candidates returned.")
            return b""

        candidate = resp.candidates[0]
        if not getattr(candidate, "content", None) or not getattr(candidate.content, "parts", None):
            print("⚠️ Gemini-TTS: no audio parts in response.")
            return b""

        part = candidate.content.parts[0]
        if hasattr(part, "inline_data") and hasattr(part.inline_data, "data"):
            audio_bytes = part.inline_data.data
            try:
                audio = AudioSegment.from_raw(
                    io.BytesIO(audio_bytes),
                    sample_width=2,
                    frame_rate=sample_rate,
                    channels=1,
                )
                faster_audio = speedup(audio, playback_speed=1.4)
                buf = io.BytesIO()
                faster_audio.export(buf, format="wav")
                return buf.getvalue()
            except Exception as e:
                print(f"⚠️ Speedup error (fallback): {e}")
                return audio_bytes
        else:
            print("⚠️ Gemini-TTS: inline audio missing.")
            return b""

    except Exception as e:
        print(f"TTS error: {e}")
        return b""


def _tts_and_play(text: str, lang: str):
    try:
        audio_bytes = text_to_speech_bytes(text=text, lang=lang, sample_rate=SAMPLE_RATE)
        if audio_bytes:
            threading.Thread(target=play_audio_bytes, args=(audio_bytes, SAMPLE_RATE), daemon=True).start()
    except Exception as e:
        print(f"TTS error: {e}")


import time

# 🎙️ معالجة الكلام
async def process_audio_buffer(buffer: np.ndarray):
    print("... 🔄 [Processing speech] ...")

    start_total = time.time()
    start_stt = time.time()

    # 🎙️ Speech-to-Text
    if buffer.ndim > 1:
        buffer = buffer[:, 0]
    if buffer.dtype != np.int16:
        buffer = np.clip(buffer, -1.0, 1.0)
        buffer = (buffer * 32767.0).astype(np.int16)
    audio_data = sr.AudioData(buffer.tobytes(), SAMPLE_RATE, 2)
    try:
        text = recognizer.recognize_google(audio_data, language="ar")
        lang = "ar"
    except sr.UnknownValueError:
        try:
            text = recognizer.recognize_google(audio_data, language="en-US")
            lang = "en"
        except Exception:
            print("❌ لم يُفهم الكلام.")
            return

    end_stt = time.time()
    print(f"👤 User ({lang}): {text}")

    ctx = session.setdefault("context", {})
    if "lang" not in ctx:
        ctx["lang"] = lang
    else:
        lang = ctx["lang"]

    # 🧠 LLM (Gemini Live API)
    print("🤖 Agent speaking in realtime...")
    start_llm = time.time()
    buffer_text = ""

    try:
        async for chunk in run_agent_stream(user_text=text, session=session):
            if not buffer_text:
                t_first = time.time()
                print(f"⏱ LLM first-token latency: {round((t_first - start_llm)*1000)} ms")
            buffer_text += chunk

        end_llm = time.time()

        # 🔊 Text-to-Speech
        start_tts = time.time()
        if buffer_text.strip():
            _tts_and_play(buffer_text, lang)
        end_tts = time.time()

        end_total = time.time()

        # 🧭 Latency report
        stt_ms = round((end_stt - start_stt) * 1000)
        llm_ms = round((end_llm - start_llm) * 1000)
        tts_ms = round((end_tts - start_tts) * 1000)
        total_ms = round((end_total - start_total) * 1000)
        print(f"\n⏱ Latency → STT: {stt_ms} ms | LLM: {llm_ms} ms | TTS: {tts_ms} ms | TOTAL: {total_ms} ms\n")
        print("✅ Done speaking.\n")

    except Exception as e:
        print(f"Agent streaming error: {e}")


# 🎧 التقاط الصوت من المايك
def audio_callback(indata, frames, time_info, status):
    data = indata.copy()
    if data.ndim > 1 and data.shape[1] > 1:
        data = data[:, 0]
    data = data.astype(np.float32, copy=False)
    _audio_queue.put(data)


# 🔁 حلقة الاستماع المستمرة
def main_loop():
    print("🎤 Ready! Start speaking...")
    buffer_blocks = []
    silence_blocks = 0
    speaking = False
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        callback=audio_callback,
        blocksize=BLOCK_SIZE,
        dtype="float32",
    ):
        while True:
            block = _audio_queue.get()
            rms = float(np.sqrt(np.mean(block * block)) * 1000.0)
            if speaking:
                buffer_blocks.append(block)
                if rms < SILENCE_THRESHOLD:
                    silence_blocks += 1
                    if silence_blocks >= MAX_SILENCE_BLOCKS:
                        combined = np.concatenate(buffer_blocks, axis=0)
                        buffer_blocks.clear()
                        silence_blocks = 0
                        speaking = False
                        asyncio.run(process_audio_buffer(combined))
                        print("🎙️ Listening again...")
                else:
                    silence_blocks = 0
            else:
                if rms >= SILENCE_THRESHOLD:
                    speaking = True
                    buffer_blocks = [block]


def run():
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")

if __name__ == "__main__":
    run()
