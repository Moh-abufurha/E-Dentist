# import sqlite3
# DB_NAME = "clinic.db"
#
# def show_table(table_name):
#     conn = sqlite3.connect(DB_NAME)
#     cur = conn.cursor()
#     cur.execute(f"SELECT * FROM {table_name}")
#     rows= cur.fetchall()
#     conn.close()
#     return rows
#
#
# if __name__ == "__main__":
#     print("Patients:", show_table("patients"))
#     print("Services:", show_table("services"))
#     print("Appointments:", show_table("appointments"))

import asyncio
from live_api_client import LiveAPISession

async def bench_once():
    async with LiveAPISession(
        model="models/gemini-2.0-flash-exp",
        system_instruction={"text": "You are a test assistant. Respond briefly."},
        tools=[],
        response_modalities=["TEXT"],
        turn_detection=None,
    ) as session:
        await session.send_text("Hello from Python!")
        async for msg in session.receive():
            print("🔹 Received:", msg)

if __name__ == "__main__":
    asyncio.run(bench_once())
