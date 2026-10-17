"""Render Talkover's real floating panel (src/voice_panel.py, unchanged) frame by frame, offscreen, from timeline.json.

    <talkover>\\.venv\\Scripts\\python.exe projects\\talkover-demo\\panel_render.py --talkover <talkover checkout>

The panel draws itself with PIL into a Win32 layered window. Here the window is swapped for an in-memory buffer and
the clock for a virtual one, and the panel is driven through the same control files the speak hook and the mic
daemon write (in a private TEMP folder, so a live Talkover on this machine is not touched): claude-user.speaking while
"you" talk, the inbox log line when a message is typed, claude-speak.pid / .progress / .wav while Claude's reply is
read, claude-speak.pause on a barge-in, claude-speak.muted for "stop listening". Mic levels come from the "you"
audio. Writes build/panel/f00000.png ... (RGBA, straight alpha) and build/panel.json (frame size, first frame time).
"""
import argparse
import json
import math
import os
import sys
import tempfile
import time as _time
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
W0 = 1_800_000_000.0           # virtual wall clock at video time 0


class Clock:
    """Stands in for the time module inside voice_panel: time() and perf_counter() follow the video."""

    def __init__(self):
        self.t = 0.0
        self.mktime, self.strptime, self.strftime, self.localtime = _time.mktime, _time.strptime, _time.strftime, \
            _time.localtime

    def time(self):
        return W0 + self.t

    def perf_counter(self):
        return 1000.0 + self.t

    def monotonic(self):
        return 1000.0 + self.t

    def sleep(self, s):
        pass


def rms_track(wav_path, fps=100):
    with wave.open(str(wav_path)) as w:
        rate = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32)
    # the inbox hears 16 kHz int16 mic audio; its rms -> level mapping is in Levels.drain (44..70 dB)
    win = rate // fps
    n = len(x) // win
    r = np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(axis=1))
    return r, fps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--talkover", default=str(Path(__file__).resolve().parents[3] / "talkover"))
    ap.add_argument("--scale", type=float, default=8.0)
    ap.add_argument("--only", type=str, default="")
    a = ap.parse_args()

    tl = json.loads((BUILD / "panel_events.json").read_text(encoding="utf-8"))
    fps = tl["fps"]
    t_start = tl["t_start"]
    t_end = tl["t_end"]

    tmp = Path(tempfile.mkdtemp(prefix="talkover-launch-"))
    home = tmp / "home"
    (home / "logs").mkdir(parents=True)
    (home / "voice_panel.json").write_text(json.dumps({"caption": True}), encoding="utf-8")
    empty_cfg = tmp / "config.env"
    empty_cfg.write_text("", encoding="utf-8")
    os.environ.update(TEMP=str(tmp), TMP=str(tmp), TALKOVER_HOME=str(home), TALKOVER_CONFIG=str(empty_cfg),
                      TALKOVER_LEVEL_PORT="42798", VOICE_PANEL_NOTRAY="1", TALKOVER_MUTEX_PREFIX="TalkoverLaunch_")
    sys.path.insert(0, str(Path(a.talkover) / "src"))
    import voice_panel as vp
    import voice_chats

    clock = Clock()
    vp.time = clock
    voice_chats.active = lambda keep="": []
    voice_chats.read_pin = lambda: None
    voice_chats.clear_pin = lambda: None
    dpi = int(round(96 * a.scale))

    class FakeWindow:
        def __init__(self, handler):
            self.w = self.h = 0
            self.pix = None

        def dpi(self):
            return dpi

        def resize(self, w, h):
            self.w, self.h = w, h
            self.pix = np.zeros((h, w, 4), np.uint8)
            return self.pix

        def push(self):
            pass

        def move(self, x, y):
            pass

        def pos(self):
            return 0, 0

        def keep_on_top(self):
            pass

        def show(self, on):
            pass

    vp.LayeredWindow = FakeWindow

    ev = tl["events"]
    you = [e for e in ev if e["kind"] == "you"]
    typed = [e for e in ev if e["kind"] in ("typed", "mute")]
    chunks = [e for e in ev if e["kind"] == "chunk"]
    cuts = {e["turn"]: e for e in ev if e["kind"] == "cut"}
    mic = {}
    for e in you:
        mic[e["turn"]] = rms_track(HERE / "audio" / ("you%d.wav" % (e["turn"] + 1)))
    # when each turn's reading ends (killed by the next message after a cut, or after its last chunk)
    read_end = {}
    for turn in sorted({c["turn"] for c in chunks}):
        cs = [c for c in chunks if c["turn"] == turn]
        if turn in cuts:
            nxt = [x for x in typed if x["turn"] == turn + 1]
            read_end[turn] = nxt[0]["t"] if nxt else cuts[turn]["t"]
        else:
            read_end[turn] = cs[-1]["t"] + cs[-1]["dur"]
    log_lines = []

    def touch(name, t, text=None, data=None):
        p = tmp / name
        if data is not None:
            p.write_bytes(data)
        elif text is not None:
            p.write_text(text, encoding="utf-8")
        elif not p.exists():
            p.write_bytes(b"")
        os.utime(p, (W0 + t, W0 + t))

    def drop(name):
        try:
            (tmp / name).unlink()
        except OSError:
            pass

    def set_state(t):
        # you talking: stamp fresh from the first word until the message is typed (the inbox keeps it fresh then)
        talking = None
        for e in you:
            end = next((x["t"] for x in typed if x["turn"] == e["turn"]), e["t"] + e["dur"])
            if e["t"] <= t < end:
                talking = e
        if talking:
            touch("claude-user.speaking", t)
        lv = None
        if talking and t < talking["t"] + talking["dur"]:
            r, rfps = mic[talking["turn"]]
            i = int((t - talking["t"]) * rfps)
            if 0 <= i < len(r):
                db = 20.0 * math.log10(max(float(r[i]) * 0.5, 1.0))
                lv = max(0.0, min(1.0, (db - 44.0) / 26.0))
        if lv is not None:
            panel.levels.mic, panel.levels.mic_t = lv, clock.time()
        # typed messages: the inbox log line the panel reads
        for x in typed:
            if x["kind"] == "typed" and x["t"] <= t and x["t"] not in log_lines:
                log_lines.append(x["t"])
                stamp = _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(W0 + x["t"]))
                with open(home / "logs" / "voice_inbox.log", "a", encoding="utf-8") as f:
                    f.write("%s,000 INFO typed %.1fs: %r\n" % (stamp, 3.0, x["heard"]))
            if x["kind"] == "mute" and x["t"] <= t:
                touch("claude-speak.muted", x["t"])
        # reading
        reading = None
        for turn, end in read_end.items():
            first = min(c["t"] for c in chunks if c["turn"] == turn)
            if first <= t < end:
                reading = turn
        if reading is None:
            drop("claude-speak.pid")
            drop("claude-speak.pause")
            drop("claude-speak.progress")
        else:
            touch("claude-speak.pid", t, text="1")
            cut = cuts.get(reading)
            if cut and t >= cut["t"]:
                touch("claude-speak.pause", cut["t"])
            else:
                drop("claude-speak.pause")
            cur = [c for c in chunks if c["turn"] == reading and c["t"] <= t]
            if cur:
                c = cur[-1]
                key = "%s:%s" % (c["turn"], c["k"])
                if state.get("chunk") != key:
                    state["chunk"] = key
                    touch("claude-speak.wav", c["t"] - 0.01, data=Path(c["wav"]).read_bytes())
                    touch("claude-speak.progress", c["t"], text=c["text"])

    state = {}
    out = BUILD / "panel"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("f*.png"):
        old.unlink()
    from PIL import Image
    clock.t = t_start
    set_state(t_start)
    panel = vp.Panel()
    n = int(round((t_end - t_start) * fps))
    only = [int(x) for x in a.only.split(",") if x]
    for i in range(n):
        if only and i > max(only):
            break
        t = t_start + i / fps
        clock.t = t
        set_state(t)
        panel.render(1.0 / fps)
        bgra = panel.win.pix.astype(np.float32)
        alpha = bgra[..., 3:4] / 255.0
        rgb = np.where(alpha > 0, bgra[..., [2, 1, 0]] / np.maximum(alpha, 1e-6), 0)
        rgba = np.concatenate([np.clip(rgb, 0, 255), bgra[..., 3:4]], axis=2).astype(np.uint8)
        if not only or i in only:
            Image.fromarray(rgba, "RGBA").save(out / ("f%05d.png" % i), compress_level=1)
        if i % 300 == 0:
            print("panel frame %d/%d (t=%.1f, mode=%s)" % (i, n, t, panel.mode))
    meta = {"t0": t_start, "fps": fps, "frames": n, "w": panel.win.w, "h": panel.win.h, "scale": a.scale,
            "margin": panel.lay.M}
    (BUILD / "panel.json").write_text(json.dumps(meta), encoding="utf-8")
    print("panel: %d frames %dx%d -> %s" % (n, panel.win.w, panel.win.h, out))


if __name__ == "__main__":
    main()
