# OBS Setup for AI Livestream Hybrid

## 1. Scene layout

Create one OBS scene named:

```text
AI Livestream Main
```

Add sources:

1. **Window Capture**
   - Capture your avatar app window, for example VTube Studio or browser avatar renderer.

2. **Audio Output Capture**
   - Capture the device where your TTS audio is played.
   - On Windows, you can use VB-Audio Cable / virtual audio cable.

3. **Browser Source** optional
   - Product card / QR code / affiliate link overlay.

4. **Text Source** optional
   - Current product name.
   - Current discount.
   - CTA text.

---

## 2. Audio routing recommendation

Recommended Windows routing:

```text
Python TTS playback → CABLE Input
OBS Audio Output Capture → CABLE Output
```

If using mock mode in this skeleton, `output.wav` is generated but not automatically played. Add playback in `tts.py` only after you choose your audio routing method.

---

## 3. Stream settings

OBS → Settings → Stream:

```text
Service: Custom / platform-specific
Server: RTMP server URL
Stream Key: platform key
```

Do not commit stream keys into git.

---

## 4. Practical checklist

- Avatar window visible and captured.
- Audio meter moves when TTS plays.
- Livestream platform receives RTMP signal.
- Python `/health` returns ok.
- n8n webhook can call Python `/speak`.
