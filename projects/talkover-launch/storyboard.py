"""Single source of truth for the Talkover launch film: panel events (what Talkover's real panel is driven through)
and the shot list (framing, type, contract) for both formats. Writes build/panel_events.json and build/storyboard.json.

Every panel line is real: the "you" lines are what Whisper heard from the earlier Talkover demo audio, Claude's lines
are chunks of the real reply a Claude Code agent wrote (video-studio/projects/talkover-demo/session.json), split by
Talkover's own Split-Chunks. Waits are shortened; chunks c1_1, c1_2, c2_1 are skipped (cut for time).
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
SRC_TL = HERE / "data" / "timeline.json"   # the talkover-demo timeline (projects/talkover-demo), kept as data
FPS = 30
BPM = 120
DUR = 20.0

src = json.loads(SRC_TL.read_text(encoding="utf-8"))
chunk_text = {(e["turn"], e["k"]): e["text"] for e in src["events"] if e["kind"] == "chunk"}
words = {e["turn"]: e["words"] for e in src["events"] if e["kind"] == "you"}
HEARD0 = "Hey Claude, what does the install script do?"
HEARD1 = "Wait, make it print how long the install took at the end."


def chunk(t, turn, k, dur, cut=False):
    e = {"kind": "chunk", "t": t, "dur": dur, "full": dur, "text": chunk_text[(turn, k)],
         "wav": str(HERE / "audio" / ("c%d_%d.wav" % (turn + 1, k))), "turn": turn, "k": k}
    if cut:
        e["cut"] = True
    return e


events = [
    {"kind": "you", "t": 1.0, "dur": 1.5, "text": HEARD0, "heard": HEARD0, "words": words[0], "turn": 0},
    {"kind": "typed", "t": 2.5, "text": HEARD0, "heard": HEARD0, "turn": 0},
    chunk(4.4, 0, 0, 1.927),
    chunk(6.35, 0, 3, 3.386, cut=True),
    {"kind": "you", "t": 8.4, "dur": 0.3, "text": HEARD1, "heard": HEARD1, "words": words[1], "turn": 1},
    {"kind": "cut", "t": 8.5, "you_t": 8.4, "turn": 0, "k": 3},
    {"kind": "typed", "t": 8.7, "text": HEARD1, "heard": HEARD1, "turn": 1},
    chunk(11.0, 1, 0, 2.458),
    chunk(12.0, 1, 2, 1.582),
    chunk(13.55, 1, 3, 2.5),
]

# Panel logical coordinates (1x, the panel window incl. its 16 px margin). Measured along the button row (y 48):
# orb glow 23.5-72.5, power 84-120, mic 142-174, robot 180-212, prev 218-250, stop 256-288, next 294-326,
# list 335-365, close 376-392. Caption row y ~84-96 from x 36. Panel body x 17..407, y 16..104.
BUTTONS = [(23.5, 72.5), (84, 120), (142, 174), (180, 212), (218, 250), (256, 288), (294, 326), (335, 365), (376, 392)]
SIZE = {"wide": (1920, 1080), "tall": (1080, 1920)}


def cam(cx, cy, z0, z1, sx, sy, snap=False):
    """Camera for one shot: panel point (cx, cy) held at screen point (sx, sy), zoom z0 -> z1 (screen px per panel px).
    snap=True marks a close-up whose frame edges must fall between buttons for the whole push (see snap_edges)."""
    return {"from": [cx, cy, z0, sx, sy], "to": [cx, cy, z1, sx, sy], "snap": snap}


def edges_ok(cx, z, sx, W):
    for e in (cx - sx / z, cx + (W - sx) / z):
        if any(a - 1.0 <= e <= b + 1.0 for a, b in BUTTONS):
            return False
    return True


def snap_edges(c, W):
    """Move the camera's x focus (and, if needed, shorten the push) so neither frame edge cuts through a button at any
    moment of the shot."""
    cx0, cy, z0, sx, sy = c["from"]
    z1 = c["to"][2]
    for shrink in range(0, 11):
        zz1 = z1 - (z1 - z0) * shrink / 10
        for d in sorted(range(-45, 46), key=abs):
            cx = cx0 + d * 0.5
            if all(edges_ok(cx, z0 + (zz1 - z0) * k / 12, sx, W) for k in range(13)):
                c["from"][0] = c["to"][0] = cx
                c["to"][2] = zz1
                return c
    raise SystemExit("no clean framing for %s" % c)


# 16:9 orb shots keep the caption row below the frame (sy + 36 z > 1080); caption shots keep the whole caption line
# inside the frame. 9:16 caption shots show the full panel width with ~60 px margins in the lower middle; 9:16 orb
# close-ups keep the orb in frame and fade the panel below the orb into the dark (mask_tall = sy + 22 z).
# Rhythm: orb close-ups 1.0 s, caption shots 2.0-2.5 s.
SHOTS = [
    {"id": "s1", "t": 0.0, "end": 1.5, "contract": "Talkover's real panel tilts flat as the camera moves in and you start talking",
     "focal": "whole panel -> orb", "hero": True,
     "wide": {"from": [212, 60, 3.4, 960, 540], "to": [175, 55, 4.4, 960, 520]},
     "tall": {"from": [212, 60, 2.3, 540, 960], "to": [190, 58, 2.6, 540, 1000]}, "type": None},
    {"id": "s2", "t": 1.5, "end": 2.5, "contract": "you just talk: the orb turns teal and follows your voice",
     "focal": "orb + mic button", "wide": cam(100, 52, 7.0, 7.3, 960, 430, True),
     "tall": cam(100, 52, 6.0, 6.2, 540, 1250, True), "type": "listen"},
    {"id": "s3", "t": 2.5, "end": 4.5, "contract": "what you said is typed into Claude Code for you",
     "focal": "caption line", "wide": cam(180, 68, 5.2, 5.4, 960, 440),
     "tall": cam(212, 62, 2.45, 2.5, 540, 1200), "type": "sent"},
    {"id": "s4", "t": 4.5, "end": 5.5, "contract": "Claude's reply is read aloud: the orb turns orange",
     "focal": "orb + robot button", "wide": cam(150, 48, 6.8, 7.0, 960, 850, True),
     "tall": cam(118, 48, 5.0, 5.15, 540, 1250, True), "mask_tall": 1360, "type": "talk"},
    {"id": "s5", "t": 5.5, "end": 8.0, "contract": "the words being read run across the panel",
     "focal": "caption line", "wide": cam(205, 70, 4.7, 4.9, 960, 650),
     "tall": cam(212, 62, 2.45, 2.5, 540, 1200), "type": "talk"},
    {"id": "s6a", "t": 8.0, "end": 9.0, "contract": "you start talking mid-reading: the reading stops, orange snaps to teal",
     "focal": "orb, mic and robot buttons", "wide": cam(125, 48, 7.3, 7.5, 960, 830, True),
     "tall": cam(100, 48, 6.0, 6.2, 540, 1250, True), "mask_tall": 1382, "type": "wait"},
    {"id": "s6b", "t": 9.0, "end": 11.0, "contract": "what you said is sent instead",
     "focal": "caption line", "wide": cam(200, 70, 4.8, 5.0, 960, 650),
     "tall": cam(212, 62, 2.45, 2.5, 540, 1200), "type": "wait"},
    {"id": "s7", "t": 11.0, "end": 12.0, "contract": "Claude answers out loud again",
     "focal": "orb + caption", "wide": cam(162, 62, 5.6, 5.8, 960, 430),
     "tall": cam(118, 48, 5.0, 5.15, 540, 1250, True), "mask_tall": 1360, "type": "resume"},
    {"id": "s8", "t": 12.0, "end": 13.5, "contract": "and picks up where you cut in",
     "focal": "caption line", "wide": cam(195, 78, 4.6, 4.75, 960, 440),
     "tall": cam(212, 62, 2.45, 2.5, 540, 1200), "type": "resume"},
    {"id": "s9", "t": 13.5, "end": 15.5, "contract": "both speech engines run on this machine",
     "focal": "type (panel out of focus behind)", "wide": cam(212, 60, 3.4, 3.7, 960, 300),
     "tall": cam(212, 60, 2.3, 2.5, 540, 1150), "type": "local", "dof": True},
    {"id": "end", "t": 15.5, "end": DUR, "contract": "name, one line, where to get it", "focal": "wordmark",
     "wide": cam(212, 60, 1.6, 1.6, 960, 330), "tall": cam(212, 60, 2.0, 2.0, 540, 640), "type": "end",
     "hide_panel": True},
]

# One text focus per shot: where the panel's caption is the evidence, the title stands alone.
# place: 16:9 titles share one left margin (bl / tl); 9:16 titles all sit at the top.
TYPE = {
    "listen": {"t": 1.5, "end": 2.5, "head": "Always listening.", "place": {"wide": "bl", "tall": "top"}},
    "sent": {"t": 2.5, "end": 4.5, "head": "It types what you say.", "head_tall": "It types\nwhat you say.",
             "sub": "Into Claude Code.", "place": {"wide": "bl", "tall": "top"}},
    "talk": {"t": 4.5, "end": 8.0, "head": "It talks back.", "place": {"wide": "tl", "tall": "top"}},
    "wait": {"t": 8.0, "end": 11.0, "head": "Say \"wait.\" It stops.", "place": {"wide": "tl", "tall": "top"}},
    "resume": {"t": 11.0, "end": 13.5, "head": "It picks up where you cut in.", "head_tall": "It picks up\nwhere you cut in.",
               "place": {"wide": "bl", "tall": "top"}},
    "local": {"t": 13.5, "end": 15.5, "head": "Fully local.", "sub": "Audio never leaves your PC.",
              "place": {"wide": "bl", "tall": "top"}},
    "end": {"t": 15.5, "end": DUR, "head": "Talkover", "sub": "Hands-free, two-way voice for Claude Code.",
            "sub_tall": "Hands-free, two-way voice\nfor Claude Code.",
            "url": "github.com/VyasSathya/talkover"},
}

# The score stops with the reading (the cut-in) and comes back with the answer.
MUSIC = {"stop": 8.5, "back": 11.0}

if __name__ == "__main__":
    BUILD.mkdir(exist_ok=True)
    for s in SHOTS:
        for fmt in ("wide", "tall"):
            if s[fmt].get("snap"):
                before = s[fmt]["from"][0], s[fmt]["to"][2]
                snap_edges(s[fmt], SIZE[fmt][0])
                after = s[fmt]["from"][0], s[fmt]["to"][2]
                if before != after:
                    print("snap %s %s: cx %.1f -> %.1f, z1 %.2f -> %.2f" % (s["id"], fmt, before[0], after[0],
                                                                           before[1], after[1]))
    (BUILD / "panel_events.json").write_text(json.dumps(
        {"fps": FPS, "t_start": -1.0, "t_end": DUR, "events": events}, indent=1), encoding="utf-8")
    beats = [round(i * 60 / BPM, 3) for i in range(int(DUR * BPM / 60) + 1)]
    (BUILD / "storyboard.json").write_text(json.dumps(
        {"fps": FPS, "bpm": BPM, "duration": DUR, "beats": beats, "shots": SHOTS, "type": TYPE, "music": MUSIC},
        indent=1), encoding="utf-8")
    print("storyboard: %d shots, %d panel events" % (len(SHOTS), len(events)))
