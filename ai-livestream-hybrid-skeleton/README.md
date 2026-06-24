# AI Livestream Hybrid Skeleton

Hybrid architecture for an AI livestream seller/host:

```text
[TikTok/YouTube/Facebook Chat]
        ↓
[n8n Webhook / Polling]
        ↓
[LLM JSON Reply]
        ↓
[Python Service: validate → TTS → avatar trigger → logging]
        ↓
[OBS: Browser/Window capture + audio device]
        ↓
[RTMP Livestream]
```

This repo is intentionally simple and production-oriented:

- deterministic JSON contract between n8n and Python
- retry-friendly endpoints
- structured logging
- safe fallback behavior
- OBS setup documentation

> Note: This skeleton does not include official TikTok/YouTube chat API integration. Use the `n8n` webhook as the integration point for any chat collector you choose.

---

## Quick start

```bash
cd python_service
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
# Linux/macOS: cp .env.example .env

python app.py
```

Health check:

```bash
curl http://127.0.0.1:8088/health
```

Send a test message:

```bash
curl -X POST http://127.0.0.1:8088/speak ^
  -H "Content-Type: application/json" ^
  -d "{\"reply\":\"Xin chào mọi người, hôm nay mình giới thiệu sản phẩm hot nhé!\",\"emotion\":\"happy\",\"action\":\"sell\",\"source_user\":\"demo_user\"}"
```

On Linux/macOS, replace `^` with `\`.

---

## Folder structure

```text
ai-livestream-hybrid-skeleton/
├─ README.md
├─ n8n/
│  ├─ workflow_ai_livestream.json
│  └─ llm_prompt.md
├─ python_service/
│  ├─ app.py
│  ├─ config.py
│  ├─ models.py
│  ├─ tts.py
│  ├─ avatar.py
│  ├─ logger_setup.py
│  ├─ requirements.txt
│  └─ .env.example
├─ obs/
│  ├─ OBS_SETUP.md
│  └─ scenes_checklist.md
├─ scripts/
│  ├─ test_payload.json
│  └─ send_test.ps1
└─ logs/
   └─ .gitkeep
```

---

## Recommended data contract

n8n should POST this JSON to Python:

```json
{
  "reply": "Câu trả lời ngắn, tự nhiên bằng tiếng Việt",
  "emotion": "happy",
  "action": "sell",
  "source_user": "viewer123",
  "comment": "giá bao nhiêu shop?",
  "request_id": "optional-uuid"
}
```

Allowed values:

```text
emotion: neutral | happy | excited | sad | angry
Action: answer | sell | ignore | fallback
```

---

## Recommended production upgrade path

1. Replace mock TTS with Azure Speech / ElevenLabs.
2. Replace mock avatar trigger with VTube Studio WebSocket API.
3. Add Redis queue between n8n and Python.
4. Add dead-letter queue for failed comments.
5. Add moderation and product knowledge retrieval.
