"""Single source of truth for the crewboard launch film: the page events (what crewboard's real page is driven
through, on the film clock) and the shot list (focus, framing, type, contract) for both formats.
Writes <work>/build/ui_events.json and <work>/build/storyboard.json.

Every pixel of product UI is crewboard's own page (web/index.html + app.js) served by
`python -m crewboard serve --demo` (example tasks and example sessions only) and recorded by ui_render.mjs.
Every UI word on screen is crewboard's demo data (crewboard/examples/progress.json and sessions.json).
Cameras are not numbers typed here: each shot names the DOM block it is about; build.py reads where that block
sits from rects.json (measured in the live page) and solves the framing so no frame edge cuts a line of text.
"""
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get("CREWBOARD_FILM_WORK", r"C:\video-studio-work\runs\crewboard-film"))
BUILD = WORK / "build"
FPS = 30
BPM = 120
DUR = 21.0
UI_END = 16.5                 # the page is on screen until the end card
PAGE = (1440, 900)            # CSS viewport; captured at 2x
SCALE = 2

# Page events on the film clock. Each lands on a cut or on a beat inside a shot.
EVENTS = [
    {"t": 5.5, "do": "click", "sel": "[data-live=\"c:demo-dark\"]", "label": "open the session"},
    {"t": 8.5, "do": "cli", "args": ["status", "py313", "doing"], "label": "an agent moves a task to In progress"},
    {"t": 10.0, "do": "click", "sel": "[data-mode=\"now\"]", "label": "open Now"},
    {"t": 10.5, "do": "click", "sel": "[data-ans=\"flaky-checkout|decide|freeze\"][data-v=\"Yes\"]", "label": "answer Yes"},
    {"t": 11.5, "do": "click", "sel": "[data-ans=\"flaky-checkout|decide|inject\"][data-v=\"No\"]", "label": "answer No"},
]

SIZE = {"wide": (1920, 1080), "tall": (1080, 1920)}

# Camera intent per shot and format: `focus` = DOM blocks (selectors from rects.json, optionally [selector, index]);
# `z` = screen px per CSS px at the start and end of the push (2.0 = the capture's own pixels, 1:1); `at` = the
# screen point the focus centre sits on. 16:9 keeps the bottom band (y > 800) for the title; 9:16 keeps the top
# band (y < 640) for the title and the bottom fifth clear. hold_x 332 = the gap between the list column (text ends
# at x 306) and the page body (starts at 358): 16:9 list shots hold the right frame edge there.
# light = the room light colour: a status token of the theme (doing, waiting, done) or neutral.
SHOTS = [
    {"id": "s1", "t": 0.0, "end": 1.5, "hero": True, "light": "neutral",
     "contract": "crewboard's real page tilts flat as the camera settles on it: sessions left, Now right",
     "focal": "the whole page",
     "wide": {"focus": ["page"], "z": [1.06, 1.13], "at": [960, 530], "tilt": [18, -12, 0, 0]},
     "tall": {"focus": ["page"], "z": [0.74, 0.66], "at": [540, 980], "tilt": [10, -36, 3, -24]}, "type": None},
    {"id": "s2", "t": 1.5, "end": 3.5, "light": "doing",
     "contract": "every Claude Code session on the machine, each with its state dot and what it is doing now",
     "focal": "Active list",
     "wide": {"focus": [["#live .hubrow", 0], ["#live .hubrow", 5]], "z": [2.85, 3.0], "at": [1420, 540]},
     "tall": {"focus": [["#live .hubrow", 0], ["#live .hubrow", 5]], "z": [3.45, 3.6], "at": [540, 1080]},
     "type": "live"},
    {"id": "s3", "t": 3.5, "end": 5.5, "light": "done",
     "contract": "the session's agents sit under it: one working (amber), one finished (green)",
     "focal": "the first session and the agents nested under it",
     "wide": {"focus": [["#live .hubrow", 0], ["#live .hubrow", 2]], "z": [3.6, 3.75], "at": [1420, 540]},
     "tall": {"focus": [["#live .hubrow", 0], ["#live .hubrow", 2]], "z": [3.6, 3.75], "at": [540, 1040]}, "type": "agents"},
    {"id": "s4", "t": 5.5, "end": 7.5, "light": "doing",
     "contract": "open a session: what it is doing now, its own to-do list",
     "focal": "the open session's own to-do list",
     "wide": {"focus": [".hs .plan"], "z": [2.9, 3.05], "at": [1000, 540], "anchor": "left"},
     "tall": {"focus": [".hs .plan"], "z": [2.75, 2.85], "at": [110, 1000], "anchor": "left"}, "type": "doing"},
    {"id": "s5", "t": 7.5, "end": 10.0, "light": "doing",
     "contract": "the shared task list (dark theme); an agent's command moves a task into In progress while you watch",
     "focal": "task list groups",
     "wide": {"focus": [["#list .gh", 0], ["#list .gh", 2]], "z": [3.4, 3.55], "at": [1420, 540]},
     "tall": {"focus": [["#list .gh", 0], ["#list .rrow", 4]], "z": [3.0, 3.12], "at": [540, 1110]},
     "type": "list"},
    {"id": "s6", "t": 10.0, "end": 12.5, "light": "waiting",
     "contract": "a question an agent left on the Now page; you answer it with one click",
     "focal": "Decide questions and their buttons",
     "wide": {"focus": [[".now .q", 0], [".now .q", 1]], "z": [2.55, 2.7], "at": [990, 540], "anchor": "left"},
     "tall": {"focus": [[".now .q", 0], [".now .q", 1]], "z": [2.75, 2.85], "at": [110, 1120], "anchor": "left"},
     "type": "answer"},
    {"id": "s7", "t": 12.5, "end": 16.5, "light": "neutral", "whole": True, "hide_page": True,
     "contract": "it runs on this machine: the command and the line it prints",
     "focal": "the terminal, lit like the page, turning flat",
     "wide": {"focus": ["page"], "z": [0.8, 0.86], "at": [1240, 470]},
     "tall": {"focus": ["page"], "z": [0.6, 0.63], "at": [540, 850]}, "type": "local"},
    {"id": "end", "t": 16.5, "end": DUR, "light": "neutral", "hide_page": True,
     "contract": "name, one line, where to get it", "focal": "wordmark",
     "wide": {"focus": ["page"], "z": [1.0, 1.0], "at": [960, 540]},
     "tall": {"focus": ["page"], "z": [1.0, 1.0], "at": [540, 960]}, "type": "end"},
]

# One sentence per shot, sentence case with a period. `dot` = the status dot of the state the shot is about, in
# crewboard's own style (its .sdot: doing amber with the live pulse, waiting violet, done green), set before the title. 16:9 titles share one left margin at the bottom; 9:16 titles
# sit at the top. head_tall gives explicit 9:16 line breaks (max 42 characters per line everywhere).
TYPE = {
    "live": {"t": 1.5, "end": 3.5, "head": "Every session, live.", "head_two": "Every session,\nlive.", "dot": "doing"},
    "agents": {"t": 3.5, "end": 5.5, "head": "Every agent, under its session.", "dot": "done",
               "head_tall": "Every agent,\nunder its session."},
    "doing": {"t": 5.5, "end": 7.5, "head": "What each one is doing.", "dot": "doing", "head_tall": "What each one\nis doing."},
    "list": {"t": 7.5, "end": 10.0, "head": "One list, shared with agents.", "dot": "doing",
             "head_tall": "One list,\nshared with agents."},
    "answer": {"t": 10.0, "end": 12.5, "head": "Answer what's waiting.", "dot": "waiting", "head_tall": "Answer\nwhat's waiting."},
    "local": {"t": 12.5, "end": 16.5, "head": "Runs on your machine.", "head_tall": "Runs on\nyour machine.",
              "term": ["python -m crewboard", "crewboard on http://localhost:7788/"]},
    "end": {"t": 16.5, "end": DUR, "head": "crewboard", "sub": "One screen for every Claude Code session.",
            "sub_tall": "One screen for every\nClaude Code session.", "url": "github.com/VyasSathya/crewboard"},
}

# Score cues: a soft tick on each page event inside a shot (the agent's command and both answers), the drums drop
# for one beat before the end card, a low hit on it.
MUSIC = {"ticks": [8.5, 10.5, 11.5], "drop": 16.0, "end": 16.5}

if __name__ == "__main__":
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "ui_events.json").write_text(json.dumps({"fps": FPS, "t_end": UI_END, "page": PAGE, "scale": SCALE,
                                                      "events": EVENTS}, indent=1), encoding="utf-8")
    beats = [round(i * 60 / BPM, 3) for i in range(int(DUR * BPM / 60) + 1)]
    (BUILD / "storyboard.json").write_text(json.dumps(
        {"fps": FPS, "bpm": BPM, "duration": DUR, "ui_end": UI_END, "page": PAGE, "scale": SCALE, "beats": beats,
         "shots": SHOTS, "type": TYPE, "music": MUSIC, "events": EVENTS}, indent=1), encoding="utf-8")
    print("storyboard: %d shots, %d page events" % (len(SHOTS), len(EVENTS)))
