# bench_live_api.py
import asyncio
import time
from live_api_client import LiveAPISession


API_KEY = "AIzaSyClZh9D_ipNMVsD_ZyDp7vT09UzG3d8vUY"

async def bench_once(text="Say hello in one short sentence."):
    # فتح جلسة مع Gemini Live API
    async with LiveAPISession(
        api_key=API_KEY,
        model="models/gemini-1.5-pro",
        system_instruction="Be concise.",
        response_modalities=["TEXT"],
        turn_detection={"type": "server", "threshold": 0.5},
        max_output_tokens=64
    ) as live:
        t_commit = time.monotonic()
        first = None


        async for _ in live.send_text(text, commit=True):
            if first is None:
                first = time.monotonic()
                print(f"🚀 First token latency: {(first - t_commit)*1000:.1f} ms")
                break

if __name__ == "__main__":
    asyncio.run(bench_once())
