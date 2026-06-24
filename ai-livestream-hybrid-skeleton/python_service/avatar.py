from config import settings

EMOTION_TO_HOTKEY = {
    "neutral": "neutral",
    "happy": "smile",
    "excited": "excited",
    "sad": "sad",
    "angry": "angry",
}


def trigger_avatar(emotion: str, audio_path: str, request_id: str) -> dict:
    """
    Trigger avatar expression or hotkey.

    Production replacement points:
    - VTube Studio WebSocket API
    - Live2D custom renderer
    - browser avatar controlled via WebSocket
    """
    provider = settings.AVATAR_PROVIDER
    hotkey = EMOTION_TO_HOTKEY.get(emotion, "neutral")

    if provider == "mock":
        return {
            "provider": provider,
            "emotion": emotion,
            "hotkey": hotkey,
            "audio_path": audio_path,
            "request_id": request_id,
        }

    if provider == "vtube_studio":
        # Placeholder only. VTube Studio requires auth token and hotkey IDs.
        # Use websocket-client to call API after completing token flow.
        raise NotImplementedError("VTube Studio adapter placeholder. Add token + hotkey trigger here.")

    raise ValueError(f"Unsupported AVATAR_PROVIDER: {provider}")
