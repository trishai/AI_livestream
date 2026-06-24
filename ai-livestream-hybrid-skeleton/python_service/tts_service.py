import base64
import math
import os
import re
import struct
import subprocess
import uuid
import wave
from pathlib import Path


try:
    from config import settings
except Exception:
    settings = None


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"


def _get_setting(name: str, default: str = "") -> str:
    """
    Read value from config.settings first, then environment variable.
    This avoids crashing if config.py does not define new fields.
    """
    if settings is not None and hasattr(settings, name):
        value = getattr(settings, name)
        if value is not None:
            return str(value)

    return os.getenv(name, default)


def _safe_filename(value: str) -> str:
    """
    Convert request_id to safe filename.
    """
    value = str(value or "").strip()

    if not value:
        value = str(uuid.uuid4())

    value = re.sub(r"[^a-zA-Z0-9_-]", "_", value)

    return value[:120]


def _build_output_file(
    request_id: str | None,
    extension: str = ".mp3",
) -> Path:
    """
    Build unique output file path.
    """
    safe_id = _safe_filename(request_id or str(uuid.uuid4()))

    if not extension.startswith("."):
        extension = "." + extension

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    return OUTPUT_DIR / f"tts_{safe_id}{extension}"


def _generate_mock_wav(
    path: str,
    duration_sec: float = 0.8,
    freq: int = 440,
) -> str:
    """
    Generate a tiny beep WAV so OBS/audio routing can be tested without TTS.
    This is used when TTS_PROVIDER=mock.
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


def _run_powershell_script(script: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    """
    Run PowerShell safely using EncodedCommand to avoid quote escaping issues.
    PowerShell expects UTF-16LE base64 for -EncodedCommand.
    """
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")

    merged_env = os.environ.copy()
    merged_env.update(env)

    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded,
        ],
        env=merged_env,
        capture_output=True,
        text=True,
        check=False,
    )


def _tts_windows_builtin(text: str, output_path: str) -> str:
    """
    Windows built-in TTS using System.Speech.Synthesis.

    Advantages:
      - Offline
      - No Azure key
      - No external package
      - No internet
      - Works with OBS as WAV output

    Optional .env:
      WINDOWS_TTS_VOICE=
      WINDOWS_TTS_RATE=0
      WINDOWS_TTS_VOLUME=100
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    rate_raw = os.getenv("WINDOWS_TTS_RATE", "0").strip()
    volume_raw = os.getenv("WINDOWS_TTS_VOLUME", "100").strip()
    voice_name = os.getenv("WINDOWS_TTS_VOICE", "").strip()

    try:
        rate = int(rate_raw)
    except ValueError:
        rate = 0

    try:
        volume = int(volume_raw)
    except ValueError:
        volume = 100

    rate = max(-10, min(10, rate))
    volume = max(0, min(100, volume))

    script = r"""
Add-Type -AssemblyName System.Speech

$text = [Environment]::GetEnvironmentVariable("TTS_TEXT")
$output = [Environment]::GetEnvironmentVariable("TTS_OUTPUT")
$voiceName = [Environment]::GetEnvironmentVariable("WINDOWS_TTS_VOICE")
$rateRaw = [Environment]::GetEnvironmentVariable("WINDOWS_TTS_RATE")
$volumeRaw = [Environment]::GetEnvironmentVariable("WINDOWS_TTS_VOLUME")

if ([string]::IsNullOrWhiteSpace($text)) {
    throw "TTS_TEXT is empty."
}

if ([string]::IsNullOrWhiteSpace($output)) {
    throw "TTS_OUTPUT is empty."
}

$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer

try {
    if (-not [string]::IsNullOrWhiteSpace($voiceName)) {
        $speak.SelectVoice($voiceName)
    }

    $rate = 0
    if (-not [string]::IsNullOrWhiteSpace($rateRaw)) {
        $rate = [int]$rateRaw
    }

    $volume = 100
    if (-not [string]::IsNullOrWhiteSpace($volumeRaw)) {
        $volume = [int]$volumeRaw
    }

    if ($rate -lt -10) { $rate = -10 }
    if ($rate -gt 10) { $rate = 10 }

    if ($volume -lt 0) { $volume = 0 }
    if ($volume -gt 100) { $volume = 100 }

    $speak.Rate = $rate
    $speak.Volume = $volume

    $speak.SetOutputToWaveFile($output)
    $speak.Speak($text)
}
finally {
    $speak.Dispose()
}
"""

    result = _run_powershell_script(
        script=script,
        env={
            "TTS_TEXT": text,
            "TTS_OUTPUT": str(out),
            "WINDOWS_TTS_VOICE": voice_name,
            "WINDOWS_TTS_RATE": str(rate),
            "WINDOWS_TTS_VOLUME": str(volume),
        },
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Windows TTS failed.\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    if not out.exists():
        raise RuntimeError(f"Windows TTS failed. Output file was not created: {out}")

    if out.stat().st_size <= 0:
        raise RuntimeError(f"Windows TTS failed. Output file is empty: {out}")

    return str(out)


def _play_audio_if_enabled(output_file: Path) -> None:
    """
    Optional local audio playback.

    .env:
      PLAY_AUDIO_AFTER_TTS=true
    """
    play_audio = os.getenv("PLAY_AUDIO_AFTER_TTS", "false").strip().lower()

    if play_audio not in {"1", "true", "yes", "y"}:
        return

    try:
        os.startfile(str(output_file))
    except Exception as exc:
        raise RuntimeError(f"Audio playback failed: {exc}") from exc


def _validate_azure_config() -> None:
    """
    Validate Azure Speech config before calling SDK.
    Azure provider is optional. It is only used when TTS_PROVIDER=azure.
    """
    azure_key = _get_setting("AZURE_SPEECH_KEY", "").strip()
    azure_region = _get_setting("AZURE_SPEECH_REGION", "").strip()
    azure_voice = _get_setting("AZURE_VOICE_NAME", "").strip()

    if not azure_key:
        raise RuntimeError(
            "Missing AZURE_SPEECH_KEY. Please set it in python_service/.env"
        )

    if azure_key in {"YOUR_KEY", "YOUR_REAL_KEY", "xxx", ""}:
        raise RuntimeError(
            "AZURE_SPEECH_KEY is still a placeholder. "
            "Replace it with your real Azure Speech key."
        )

    if not azure_region:
        raise RuntimeError(
            "Missing AZURE_SPEECH_REGION. Example: southeastasia"
        )

    if not azure_voice:
        raise RuntimeError(
            "Missing AZURE_VOICE_NAME. Example: vi-VN-HoaiMyNeural"
        )


def _apply_proxy_if_configured(speech_config) -> None:
    """
    Apply proxy for Azure Speech SDK.

    .env:
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

    speech_config.set_proxy(proxy_host, proxy_port)


def _synthesize_azure_tts(text: str, request_id: str | None = None) -> str:
    """
    Azure Speech provider.

    This requires:
      - azure-cognitiveservices-speech installed
      - AZURE_SPEECH_KEY
      - AZURE_SPEECH_REGION
      - AZURE_VOICE_NAME
    """
    _validate_azure_config()

    try:
        import azure.cognitiveservices.speech as speechsdk
    except Exception as exc:
        raise RuntimeError(
            "Azure Speech SDK is not installed or cannot be imported. "
            "Install azure-cognitiveservices-speech or use TTS_PROVIDER=windows."
        ) from exc

    output_file = _build_output_file(request_id, extension=".mp3")

    speech_config = speechsdk.SpeechConfig(
        subscription=_get_setting("AZURE_SPEECH_KEY", "").strip(),
        region=_get_setting("AZURE_SPEECH_REGION", "").strip(),
    )

    _apply_proxy_if_configured(speech_config)

    speech_config.speech_synthesis_voice_name = _get_setting(
        "AZURE_VOICE_NAME",
        "vi-VN-HoaiMyNeural",
    ).strip()

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

        raise RuntimeError(
            "Azure TTS failed.\n"
            f"Reason: {cancellation_details.reason}\n"
            f"Error code: {cancellation_details.error_code}\n"
            f"Error details: {cancellation_details.error_details}"
        )

    raise RuntimeError(f"Azure TTS failed with unknown result: {result.reason}")


def synthesize_speech(text: str, request_id: str | None = None) -> str:
    """
    Main TTS function.

    Supported providers:
      - mock
      - windows
      - sapi
      - azure

    Recommended for your current Bosch environment:
      TTS_PROVIDER=windows

    Returns:
      Path to generated audio file.
    """
    provider = _get_setting("TTS_PROVIDER", "mock").strip().lower()

    if not text or not text.strip():
        raise ValueError("Text for TTS is empty.")

    if provider == "mock":
        output_file = _build_output_file(request_id, extension=".mp3")
        audio_path = _generate_mock_wav(str(output_file))
        _play_audio_if_enabled(Path(audio_path))
        return audio_path

    if provider in {"windows", "sapi", "system"}:
        output_file = _build_output_file(request_id, extension=".mp3")
        audio_path = _tts_windows_builtin(text=text, output_path=str(output_file))
        _play_audio_if_enabled(Path(audio_path))
        return audio_path

    if provider == "azure":
        return _synthesize_azure_tts(
            text=text,
            request_id=request_id,
        )

    raise ValueError(
        f"Unsupported TTS provider: {provider}. "
        "Use one of: mock, windows, azure."
    )


def list_windows_voices() -> list[str]:
    """
    List installed Windows SAPI voices.
    Useful if you want to set WINDOWS_TTS_VOICE.
    """
    script = r"""
Add-Type -AssemblyName System.Speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer

try {
    $voices = $speak.GetInstalledVoices()
    foreach ($voice in $voices) {
        $info = $voice.VoiceInfo
        Write-Output $info.Name
    }
}
finally {
    $speak.Dispose()
}
"""

    result = _run_powershell_script(script=script, env={})

    if result.returncode != 0:
        raise RuntimeError(
            "Failed to list Windows voices.\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    return [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]


if __name__ == "__main__":
    print("DEBUG BASE_DIR:", BASE_DIR)
    print("DEBUG OUTPUT_DIR:", OUTPUT_DIR)
    print("DEBUG TTS_PROVIDER:", _get_setting("TTS_PROVIDER", "mock"))
    print("DEBUG AZURE_REGION:", _get_setting("AZURE_SPEECH_REGION", ""))
    print("DEBUG AZURE_VOICE:", _get_setting("AZURE_VOICE_NAME", ""))
    print("DEBUG WINDOWS_TTS_VOICE:", os.getenv("WINDOWS_TTS_VOICE", ""))
    print("DEBUG WINDOWS_TTS_RATE:", os.getenv("WINDOWS_TTS_RATE", "0"))
    print("DEBUG WINDOWS_TTS_VOLUME:", os.getenv("WINDOWS_TTS_VOLUME", "100"))
    print("DEBUG PLAY_AUDIO_AFTER_TTS:", os.getenv("PLAY_AUDIO_AFTER_TTS", "false"))

    try:
        print("DEBUG Installed Windows voices:")
        for voice in list_windows_voices():
            print(" -", voice)
    except Exception as exc:
        print("WARNING: Could not list Windows voices:")
        print(exc)

    try:
        audio_path = synthesize_speech(
            "Xin chào, đây là kiểm tra Text to Speech chạy offline bằng Windows.",
            request_id="manual_test",
        )
        print("✅ TTS success:", audio_path)

    except Exception as exc:
        print("❌ TTS failed:")
        print(exc)