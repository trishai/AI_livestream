import math
import os
import re
import struct
import uuid
import wave
from pathlib import Path

import azure.cognitiveservices.speech as speechsdk

from config import settings


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"


def _safe_filename(value: str) -> str:
    """
    Convert request_id to safe filename.
    """
    value = str(value or "").strip()
    if not value:
        value = str(uuid.uuid4())

    value = re.sub(r"[^a-zA-Z0-9_-]", "_", value)
    return value[:120]


def _generate_mock_wav(path: str, duration_sec: float = 0.8, freq: int = 440) -> str:
    """
    Generate a tiny beep WAV so OBS/audio routing can be tested without paid TTS.
    """
    sample_rate = 16000
    amplitude = 12000
    n_samples = int(sample_rate * duration_sec)

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(out), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        for i in range(n_samples):
            val = int(amplitude * math.sin(2 * math.pi * freq * i / sample_rate))
            wav.writeframes(struct.pack("<h", val))

    return str(out)


def _validate_azure_config() -> None:
    """
    Validate Azure Speech config before calling SDK.
    """
    if not settings.AZURE_SPEECH_KEY:
        raise RuntimeError(
            "Missing AZURE_SPEECH_KEY. Please set it in python_service/.env"
        )

    if settings.AZURE_SPEECH_KEY.strip() in {"YOUR_KEY", "YOUR_REAL_KEY", ""}:
        raise RuntimeError(
            "AZURE_SPEECH_KEY is still a placeholder. "
            "Replace it with your real Azure Speech key."
        )

    if not settings.AZURE_SPEECH_REGION:
        raise RuntimeError(
            "Missing AZURE_SPEECH_REGION. Example: southeastasia"
        )

    if not settings.AZURE_VOICE_NAME:
        raise RuntimeError(
            "Missing AZURE_VOICE_NAME. Example: vi-VN-HoaiMyNeural"
        )


def _build_output_file(request_id: str | None) -> Path:
    """
    Build unique output wav path.
    """
    safe_id = _safe_filename(request_id or str(uuid.uuid4()))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    return OUTPUT_DIR / f"tts_{safe_id}.wav"


def _apply_proxy_if_configured(speech_config: speechsdk.SpeechConfig) -> None:
    """
    Apply proxy for corporate network / px.exe if configured.

    Add these to .env if needed:
        PROXY_HOST=127.0.0.1
        PROXY_PORT=3128
    """
    proxy_host = os.getenv("PROXY_HOST", "").strip()
    proxy_port_raw = os.getenv("PROXY_PORT", "").strip()

    if not proxy_host or not proxy_port_raw:
        return

    try:
        proxy_port = int(proxy_port_raw)
    except ValueError:
        raise RuntimeError(f"Invalid PROXY_PORT: {proxy_port_raw}")

    # Azure Speech SDK expects host and port, not full URL.
    # Correct: 127.0.0.1, 3128
    # Wrong: http://127.0.0.1:3128
    speech_config.set_proxy(proxy_host, proxy_port)


def _play_audio_if_enabled(output_file: Path) -> None:
    """
    Optional local audio playback on Windows.

    Add this to .env if you want auto-play:
        PLAY_AUDIO_AFTER_TTS=true
    """
    play_audio = os.getenv("PLAY_AUDIO_AFTER_TTS", "false").strip().lower()

    if play_audio not in {"1", "true", "yes", "y"}:
        return

    try:
        import winsound

        winsound.PlaySound(str(output_file), winsound.SND_FILENAME)
    except Exception as exc:
        raise RuntimeError(f"Audio playback failed: {exc}") from exc


def synthesize_speech(text: str, request_id: str | None = None) -> str:
    """
    Synthesize text to speech.

    Supported providers:
      - mock
      - azure

    Returns:
      Path to generated wav file.
    """
    provider = (settings.TTS_PROVIDER or "mock").strip().lower()

    if not text or not text.strip():
        raise ValueError("Text for TTS is empty.")

    output_file = _build_output_file(request_id)

    if provider == "mock":
        return _generate_mock_wav(str(output_file))

    if provider == "azure":
        _validate_azure_config()

        speech_config = speechsdk.SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY,
            region=settings.AZURE_SPEECH_REGION,
        )

        _apply_proxy_if_configured(speech_config)

        speech_config.speech_synthesis_voice_name = settings.AZURE_VOICE_NAME

        # WAV output, easy for OBS/debug/playback.
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
        )

        audio_config = speechsdk.audio.AudioOutputConfig(
            filename=str(output_file)
        )

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            _play_audio_if_enabled(output_file)
            return str(output_file)

        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details

            error_message = (
                "Azure TTS failed.\n"
                f"Reason: {cancellation_details.reason}\n"
                f"Error code: {cancellation_details.error_code}\n"
                f"Error details: {cancellation_details.error_details}"
            )

            raise RuntimeError(error_message)

        raise RuntimeError(f"Azure TTS failed with unknown result: {result.reason}")

    raise ValueError(f"Unsupported TTS provider: {provider}")


if __name__ == "__main__":
    print("DEBUG BASE_DIR:", BASE_DIR)
    print("DEBUG TTS_PROVIDER:", settings.TTS_PROVIDER)
    print("DEBUG REGION:", settings.AZURE_SPEECH_REGION)
    print("DEBUG VOICE:", settings.AZURE_VOICE_NAME)
    print("DEBUG PROXY_HOST:", os.getenv("PROXY_HOST", ""))
    print("DEBUG PROXY_PORT:", os.getenv("PROXY_PORT", ""))

    try:
        audio_path = synthesize_speech(
            "Xin chào, đây là kiểm tra Azure Text to Speech.",
            request_id="manual_test",
        )
        print("✅ TTS success:", audio_path)

    except Exception as exc:
        print("❌ TTS failed:")
        print(exc)