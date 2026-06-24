import uuid
import time
import json

from fastapi import FastAPI, HTTPException, Request
import uvicorn

from config import settings
from models import SpeakResponse
from tts import synthesize_speech
from avatar import trigger_avatar
from logger_setup import setup_logger


logger = setup_logger(settings.LOG_LEVEL)

app = FastAPI(
    title="AI Livestream Hybrid Service",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "tts_provider": settings.TTS_PROVIDER,
        "avatar_provider": settings.AVATAR_PROVIDER,
        "host": settings.HOST,
        "port": settings.PORT,
    }


@app.post("/speak")
async def speak(request: Request):
    """
    Accept simple n8n payload:

    {
        "reply": "{{ $json.reply }}"
    }

    Also supports optional fields:
    {
        "reply": "...",
        "request_id": "...",
        "source_user": "...",
        "comment": "...",
        "emotion": "neutral",
        "action": "speak"
    }
    """

    started = time.time()

    try:
        raw_body = await request.body()

        logger.info(
            json.dumps(
                {
                    "event": "speak_raw_body",
                    "raw_body": raw_body.decode("utf-8", errors="replace"),
                },
                ensure_ascii=False,
            )
        )

        try:
            payload = json.loads(raw_body or b"{}")
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON body.",
            )

        reply = str(payload.get("reply") or "").strip()

        if not reply:
            raise HTTPException(
                status_code=400,
                detail="Missing required field: reply",
            )

        request_id = str(payload.get("request_id") or uuid.uuid4())
        source_user = str(payload.get("source_user") or "unknown")
        comment = str(payload.get("comment") or "")
        emotion = str(payload.get("emotion") or "neutral")
        action = str(payload.get("action") or "speak").lower().strip()

        if action == "ignore":
            logger.info(
                json.dumps(
                    {
                        "event": "ignored",
                        "request_id": request_id,
                        "source_user": source_user,
                        "comment": comment,
                        "reply": reply,
                    },
                    ensure_ascii=False,
                )
            )

            return {
                "status": "ignored",
                "request_id": request_id,
                "tts_provider": settings.TTS_PROVIDER,
                "avatar_provider": settings.AVATAR_PROVIDER,
                "message": "Action is ignore; no TTS/avatar triggered.",
            }

        audio_path = synthesize_speech(reply, request_id)

        avatar_result = trigger_avatar(
            emotion=emotion,
            audio_path=audio_path,
            request_id=request_id,
        )

        latency_ms = int((time.time() - started) * 1000)

        logger.info(
            json.dumps(
                {
                    "event": "speak_success",
                    "request_id": request_id,
                    "source_user": source_user,
                    "comment": comment,
                    "reply": reply,
                    "emotion": emotion,
                    "action": action,
                    "audio_path": audio_path,
                    "avatar_result": avatar_result,
                    "latency_ms": latency_ms,
                },
                ensure_ascii=False,
            )
        )

        return {
            "status": "ok",
            "request_id": request_id,
            "tts_provider": settings.TTS_PROVIDER,
            "avatar_provider": settings.AVATAR_PROVIDER,
            "message": "Speech and avatar trigger completed.",
            "reply": reply,
            "audio_path": audio_path,
            "avatar_result": avatar_result,
            "latency_ms": latency_ms,
        }

    except HTTPException:
        raise

    except Exception as ex:
        latency_ms = int((time.time() - started) * 1000)

        logger.exception(
            json.dumps(
                {
                    "event": "speak_failed",
                    "error": str(ex),
                    "latency_ms": latency_ms,
                },
                ensure_ascii=False,
            )
        )

        raise HTTPException(
            status_code=500,
            detail={
                "error": str(ex),
                "latency_ms": latency_ms,
            },
        )


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
    )