import uuid
import time
import json
from fastapi import FastAPI, HTTPException
import uvicorn

from config import settings
from models import SpeakRequest, SpeakResponse
from tts_service import synthesize_speech
from avatar import trigger_avatar
from logger_setup import setup_logger

logger = setup_logger(settings.LOG_LEVEL)
app = FastAPI(title="AI Livestream Hybrid Service", version="0.1.0")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "tts_provider": settings.TTS_PROVIDER,
        "avatar_provider": settings.AVATAR_PROVIDER,
    }


@app.post("/speak", response_model=SpeakResponse)
def speak(req: SpeakRequest):
    started = time.time()
    request_id = req.request_id or str(uuid.uuid4())

    if req.action == "ignore":
        logger.info(json.dumps({
            "event": "ignored",
            "request_id": request_id,
            "source_user": req.source_user,
            "comment": req.comment,
        }, ensure_ascii=False))
        return SpeakResponse(
            status="ignored",
            request_id=request_id,
            tts_provider=settings.TTS_PROVIDER,
            avatar_provider=settings.AVATAR_PROVIDER,
            message="Action is ignore; no TTS/avatar triggered.",
        )

    try:
        audio_path = synthesize_speech(req.reply, request_id)
        avatar_result = trigger_avatar(req.emotion, audio_path, request_id)
        latency_ms = int((time.time() - started) * 1000)

        logger.info(json.dumps({
            "event": "speak_success",
            "request_id": request_id,
            "source_user": req.source_user,
            "comment": req.comment,
            "reply": req.reply,
            "emotion": req.emotion,
            "action": req.action,
            "audio_path": audio_path,
            "avatar_result": avatar_result,
            "latency_ms": latency_ms,
        }, ensure_ascii=False))

        return SpeakResponse(
            status="ok",
            request_id=request_id,
            tts_provider=settings.TTS_PROVIDER,
            avatar_provider=settings.AVATAR_PROVIDER,
            message="Speech and avatar trigger completed.",
        )

    except Exception as ex:
        latency_ms = int((time.time() - started) * 1000)
        logger.exception(json.dumps({
            "event": "speak_failed",
            "request_id": request_id,
            "error": str(ex),
            "latency_ms": latency_ms,
        }, ensure_ascii=False))
        raise HTTPException(status_code=500, detail={
            "request_id": request_id,
            "error": str(ex),
        })
# from fastapi import Request
# from fastapi.responses import JSONResponse

# @app.post("/speak")
# async def speak_debug(request: Request):
#     try:
#         raw = await request.body()

#         print("\n========== RAW BODY ==========")
#         print(raw)
#         print("========== END BODY ==========\n")

#         return {"ok": True}

#     except Exception as e:
#         print("ERROR:", e)
#         return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    uvicorn.run("app:app", host=settings.HOST, port=settings.PORT, reload=False)
