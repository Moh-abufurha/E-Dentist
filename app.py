import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from voice_realtime import process_audio_buffer, SAMPLE_RATE, CHANNELS
import sounddevice as sd
import numpy as np
import queue
import asyncio

root = tk.Tk()
root.title("Medical AI Assistant")
root.geometry("700x700")
root.configure(bg="#f7f7fb")

audio_queue = queue.Queue()
is_listening = False

title = tk.Label(root, text="Medical AI Assistant", font=("Arial", 18, "bold"), bg="#f7f7fb", fg="#4f46e5")
title.pack(pady=10)

chat_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=20, font=("Arial", 11))
chat_box.pack(padx=15, pady=10)
chat_box.insert(tk.END, "Hello! Click 'Start Speaking' to begin the conversation.\n")
chat_box.configure(state=tk.DISABLED)

def audio_callback(indata, frames, time_info, status):
    if not is_listening:
        return
    data = indata.copy()
    if data.ndim > 1:
        data = data[:, 0]
    audio_queue.put(data)

def listen_audio():
    global is_listening
    if is_listening:
        messagebox.showinfo("Info", "Recording is already running.")
        return
    is_listening = True
    chat_box.configure(state=tk.NORMAL)
    chat_box.insert(tk.END, "\nListening started...\n")
    chat_box.configure(state=tk.DISABLED)
    threading.Thread(target=record_loop, daemon=True).start()

def record_loop():
    global is_listening
    print("Stream opened successfully — ready for continuous listening.")

    buffer_blocks = []
    silence_blocks = 0
    speaking = False

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        callback=audio_callback,
        blocksize=int(SAMPLE_RATE * 0.3),
        dtype="float32",
    ):
        while is_listening:
            try:
                block = audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            rms = float(np.sqrt(np.mean(block * block)) * 1000.0)

            if speaking:
                buffer_blocks.append(block)
                if rms < 15.0:
                    silence_blocks += 1
                    if silence_blocks >= 3:
                        combined = np.concatenate(buffer_blocks, axis=0)
                        buffer_blocks.clear()
                        silence_blocks = 0
                        speaking = False

                        print("Speech detected, processing...")
                        combined = np.clip(combined, -1.0, 1.0)
                        combined = (combined * 32767.0).astype(np.int16)

                        threading.Thread(
                            target=process_audio_sync,
                            args=(combined,),
                            daemon=True
                        ).start()
                else:
                    silence_blocks = 0
            else:
                if rms >= 20.0:
                    speaking = True
                    buffer_blocks = [block]

def process_audio_sync(buffer):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_audio_buffer(buffer))
    finally:
        loop.close()

def stop_listening():
    global is_listening
    if not is_listening:
        messagebox.showinfo("Info", "Recording is not active.")
        return
    is_listening = False
    chat_box.configure(state=tk.NORMAL)
    chat_box.insert(tk.END, "\nListening stopped.\n")
    chat_box.configure(state=tk.DISABLED)

button_frame = tk.Frame(root, bg="#f7f7fb")
button_frame.pack(pady=10)

start_btn = tk.Button(button_frame, text="Start Speaking", command=listen_audio, font=("Arial", 12, "bold"), bg="#4f46e5", fg="white", width=15)
start_btn.grid(row=0, column=0, padx=10)

stop_btn = tk.Button(button_frame, text="Stop", command=stop_listening, font=("Arial", 12, "bold"), bg="#ef4444", fg="white", width=15)
stop_btn.grid(row=0, column=1, padx=10)

root.mainloop()
