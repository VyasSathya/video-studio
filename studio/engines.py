"""Local speech engines: Kokoro (text to speech) and Whisper (speech to text with word timestamps).

Both speak the OpenAI audio API, so any compatible server works:
  Kokoro-FastAPI   POST {TTS}/v1/audio/speech            (default http://127.0.0.1:8880)
  speaches         POST {STT}/v1/audio/transcriptions    (default http://127.0.0.1:2022)
Override with STUDIO_TTS_BASE / STUDIO_STT_BASE.
"""
import io
import json
import os
import uuid
import urllib.request
import wave
from pathlib import Path

TTS_BASE = os.getenv("STUDIO_TTS_BASE", "http://127.0.0.1:8880").rstrip("/")
STT_BASE = os.getenv("STUDIO_STT_BASE", "http://127.0.0.1:2022").rstrip("/")


def tts(text: str, out: Path, voice: str = "af_heart", speed: float = 1.0) -> float:
    """Speak text into a wav file; returns its duration in seconds."""
    body = json.dumps({"model": "kokoro", "voice": voice, "input": text, "response_format": "wav",
                       "speed": speed}).encode()
    req = urllib.request.Request(TTS_BASE + "/v1/audio/speech", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_clean_wav(data, out)
    return wav_duration(out)


def write_clean_wav(data: bytes, out: Path) -> None:
    """Kokoro streams its wav, so the header's sizes are placeholders. Rewrite it with real sizes."""
    i = data.find(b"fmt ")
    ch = int.from_bytes(data[i + 10:i + 12], "little")
    rate = int.from_bytes(data[i + 12:i + 16], "little")
    bits = int.from_bytes(data[i + 22:i + 24], "little")
    j = data.find(b"data")
    pcm = data[j + 8:]
    width = bits // 8
    pcm = pcm[:len(pcm) // (width * ch) * (width * ch)]
    with wave.open(str(out), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(pcm)


def wav_duration(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / float(w.getframerate())


def stt(path: Path, words: bool = True, language: str = "en", prompt: str = "") -> dict:
    """Transcribe a wav. Returns {"text", "words": [{"word", "start", "end"}], "segments"}."""
    fields = [("model", "whisper-1"), ("language", language), ("temperature", "0")]
    if words:
        fields += [("response_format", "verbose_json"), ("timestamp_granularities[]", "word"),
                   ("timestamp_granularities[]", "segment")]
    else:
        fields += [("response_format", "json")]
    if prompt:
        fields.append(("prompt", prompt))
    boundary = uuid.uuid4().hex
    buf = io.BytesIO()
    for k, v in fields:
        buf.write(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, k, v)).encode())
    buf.write(("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.wav\"\r\n"
               "Content-Type: audio/wav\r\n\r\n" % boundary).encode())
    buf.write(Path(path).read_bytes())
    buf.write(("\r\n--%s--\r\n" % boundary).encode())
    req = urllib.request.Request(STT_BASE + "/v1/audio/transcriptions", data=buf.getvalue(),
                                 headers={"Content-Type": "multipart/form-data; boundary=" + boundary})
    with urllib.request.urlopen(req, timeout=300) as r:
        res = json.loads(r.read().decode("utf-8"))
    res.setdefault("words", [])
    res["text"] = (res.get("text") or "").strip()
    return res


def health() -> dict:
    """Which engines answer right now."""
    out = {}
    for name, url in (("kokoro", TTS_BASE + "/v1/audio/voices"), ("whisper", STT_BASE + "/v1/models")):
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                out[name] = r.status == 200
        except Exception:
            out[name] = False
    return out
