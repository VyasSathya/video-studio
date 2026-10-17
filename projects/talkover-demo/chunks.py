"""Talkover's speak hook (hooks/speak-response.ps1, Split-Chunks) ported to Python, so the demo's audio is cut into
the same pieces the real hook would read."""
import re


def split_chunks(t: str) -> list:
    sentences = [s for s in re.split(r"(?<=[.!?:])\s+", t) if s]
    chunks, buf = [], ""
    if sentences:
        first, rest = sentences[0], sentences[1:]
        if len(first) > 80:
            m = re.search(r"[,;:]\s", first[30:])
            if m and 30 + m.start() + 1 <= 80:
                cut = 30 + m.start() + 1
                rest = [first[cut:].strip()] + rest
                first = first[:cut]
        chunks.append(first)
        sentences = rest
    for s in sentences:
        if buf and len(buf) + len(s) > 140:
            chunks.append(buf)
            buf = ""
        buf = (buf + " " + s) if buf else s
    if buf:
        chunks.append(buf)
    return chunks
