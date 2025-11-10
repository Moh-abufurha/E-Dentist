# live_api_client.py
import os
import json
import asyncio
from websockets.asyncio.client import connect



import time
from typing import AsyncGenerator, Dict, Any, Optional, List

#LIVE_API_WS_URL = os.getenv("GEMINI_LIVE_WS_URL", "wss://<your-live-api-endpoint>")
LIVE_API_WS_URL = f"wss://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:streamGenerateContent?key=AIzaSyClZh9D_ipNMVsD_ZyDp7vT09UzG3d8vUY"

class LiveAPISession:
    def __init__(
        self,
        api_key: str,
        model: str = "models/gemini-1.5-pro",
        system_instruction: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        response_modalities: Optional[List[str]] = None,
        turn_detection: Optional[Dict[str, Any]] = None,
        max_output_tokens: Optional[int] = None,
        client_secret: Optional[str] = None,
        extra_config: Optional[Dict[str, Any]] = None,
        context_payload: Optional[Dict[str, Any]] = None,
    ):
        self.api_key = api_key
        self.model = model
        self.system_instruction = system_instruction
        self.tools = tools or []  # tool schemas
        self.response_modalities = response_modalities or ["TEXT"]
        self.turn_detection = turn_detection or {"type": "server", "threshold": 0.5}
        self.max_output_tokens = max_output_tokens or 256
        self.client_secret = client_secret  # لو المرجع يتطلب clientSecret
        self.extra_config = extra_config or {}
        self.context_payload = context_payload or {}
        self.ws = None

    async def __aenter__(self):
        # افتح الاتصال
        headers = [("Authorization", f"Bearer {self.api_key}")]
        self.ws = await connect(LIVE_API_WS_URL, additional_headers=headers, ping_interval=20)

        # أرسل رسالة setup
        setup_msg = {
            "type": "setup",
            "model": self.model,
            # بعض الريبو يسميها "config" أو يضعها top-level — اتبع سكيمة المرجع لديك
            "config": {
                "systemInstruction": self.system_instruction or "",
                "tools": self.tools,  # [{"name": "...","description":"...","schema": {...}}]
                "responseModalities": self.response_modalities,  # ["TEXT"] أو ["AUDIO","TEXT"]
                "turnDetection": self.turn_detection,
                "generationConfig": {
                    "maxOutputTokens": self.max_output_tokens
                },
                **self.extra_config
            },
            # إن كان المرجع يطلب clientSecret
            **({"clientSecret": self.client_secret} if self.client_secret else {}),
            # سياق أولي (مثلاً patient_id, lang)
            **({"sessionContext": self.context_payload} if self.context_payload else {}),
        }
        await self.ws.send(json.dumps(setup_msg))
        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if self.ws:
                await self.ws.close()
        finally:
            self.ws = None

    async def send_text(self, text: str, commit: bool = True) -> AsyncGenerator[str, None]:
        """
        يرسل input_text → يكمّل بـ commit → يرجع ستريم tokens كنص.
        """
        assert self.ws is not None, "WebSocket not open"

        # 1) input_text
        input_msg = {"type": "input_text", "text": text}
        await self.ws.send(json.dumps(input_msg))

        # 2) commit (حسب البروتوكول في المرجع)
        if commit:
            await self.ws.send(json.dumps({"type": "commit"}))

        # 3) استقبل chunks
        # البروتوكول عادةً يرسل أحداث مثل:
        # {"type":"response_chunk","text":"..."} أو {"type":"token","text":"..."}
        # وبالنهاية {"type":"response_end"} أو {"type":"done"}
        first_token_ts = None
        while True:
            try:
                raw = await asyncio.wait_for(self.ws.recv(), timeout=120)
            except asyncio.TimeoutError:
                break

            data = json.loads(raw)

            if data.get("type") in ("token", "response_chunk"):
                if first_token_ts is None:
                    first_token_ts = time.monotonic()
                piece = data.get("text") or ""
                if piece:
                    yield piece
            elif data.get("type") in ("response_end", "done", "server_close"):
                break
            elif data.get("type") == "error":

                raise RuntimeError(f"Live API error: {data.get('message', data)}")


    async def ping(self):
        if self.ws:
            await self.ws.ping()
