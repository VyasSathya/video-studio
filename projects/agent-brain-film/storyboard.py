"""Single source of truth for the agent-brain launch film: the cards (real command output and real files, typeset),
their layout, the shot list (card, framing, type, contract) for both formats, and the music cues.
Writes BUILD/storyboard.json.

Every character on a card comes from data/session.json and data/files.json, written by capture.py, which ran the
README tour for real (the README's own commands, no filters) in a throwaway copy of the repo. A card is a viewport
on that output: a run of consecutive display rows, the way a terminal or editor window shows part of a long output,
with the running command in the window's title bar when its prompt line has scrolled out of view. Long lines are
soft-wrapped for the width (at spaces; a long path at the column); no character is added, dropped or retyped.
"""
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get("STUDIO_WORK") or "C:/video-studio-work") / "runs" / "agent-brain-film"
BUILD = WORK / "build"
FPS, BPM, DUR = 30, 120, 20.5
SIZE = {"wide": (1920, 1080), "tall": (1080, 1920)}

SESSION = json.loads((HERE / "data" / "session.json").read_text(encoding="utf-8"))
FILES = json.loads((HERE / "data" / "files.json").read_text(encoding="utf-8"))
STEP = {s["id"]: s for s in SESSION["steps"]}

# Card metrics in logical px (the camera zooms them). JetBrains Mono advance is 0.6 em.
FS, LH, CW = 22, 36, 13.2
PAD_X, HEADER, PAD_T, PAD_B, GAP = 34, 54, 26, 30, 14
GUTTER = 4          # file cards: line-number column, in characters

# Accent spans: exact substrings of the real output (optionally only right after a context) and their colour:
# diagram tokens, blue = what you run, orange = evidence.
ACCENT = {
    "start0": [("0", "ev", "Project handoffs: ")],
    "cur2": [("true", "ev", "\"evidence_changed\": ")],
    "deps": [("[]", "in", None)],
}


def wrap(text, cols):
    """Soft-wrap for display, the way a terminal or editor wraps a long line: at the last space that fits (that one
    space is the break and is not shown), or, for a token longer than the width (a path), after one of its slashes.
    A token with neither is wrapped at the column. Every other character stays, indentation and double spaces
    included; none is added."""
    out = []
    for line in text.expandtabs(8).split("\n"):    # a terminal shows a tab as spaces to the next 8-column stop
        while len(line) > cols:
            ind = len(line) - len(line.lstrip(" "))
            i = line.rfind(" ", ind + 1, cols + 1)
            if i > ind:
                out.append(line[:i])
                line = line[i + 1:]
                continue
            j = line.rfind("/", ind + 1, cols)
            if j > ind:
                out.append(line[:j + 1])
                line = line[j + 1:]
                continue
            out.append(line[:cols])
            line = line[cols:]
        out.append(line)
    return out


def marks_for(sid, full):
    marks = []
    for sub, cls, ctx in ACCENT.get(sid, []):
        i = full.find((ctx or "") + sub)
        if i >= 0:
            marks.append((i + len(ctx or ""), i + len(ctx or "") + len(sub), cls))
    return marks


def term_rows(steps, cols):
    """Every display row of a run of commands, in order: '$ ' + command, then its output."""
    rows = []
    for k, sid in enumerate(steps):
        st = STEP[sid]
        for i, ln in enumerate(wrap(st["cmd"], cols - 2)):
            rows.append({"kind": "cmd", "text": ln, "first": i == 0, "step": sid, "gap": k > 0 and i == 0,
                         "src": [sid, "cmd", i]})
        if st["out"]:
            full = st["out"].expandtabs(8)
            marks, pos = marks_for(sid, full), 0
            i = 0
            for j, line in enumerate(st["out"].split("\n")):   # same rows as wrap(out), tagged by source line
                for ln in wrap(line, cols):
                    at = full.find(ln, pos) if ln else pos
                    pos = at + len(ln)
                    acc = [[max(a, at) - at, min(b, pos) - at, c] for a, b, c in marks if a < pos and b > at]
                    rows.append({"kind": "out", "text": ln, "step": sid, "acc": acc, "src": [sid, "out", i],
                                 "ln": j})
                    i += 1
    return rows


def find(rows, text, start=0):
    return next(i for i in range(start, len(rows)) if text in rows[i]["text"])


def view(cid, rows, a, b, focus, band, title):
    """A window onto rows[a:b]: the card is laid out from those rows only. focus/band: indices into rows."""
    out, y = [], HEADER + PAD_T
    for i in range(a, b):
        r = dict(rows[i])
        if r.get("gap") and i > a:
            y += GAP
        r["y"] = y
        r["focus"] = i in focus
        r["band"] = band if i in focus and band else None
        out.append(r)
        y += LH
    n = max(len(r["text"]) + (2 if r["kind"] == "cmd" else 0) + (GUTTER if r["kind"] == "file" else 0) for r in out)
    x0 = PAD_X + (GUTTER * CW if out[0]["kind"] == "file" else 0)
    return {"id": cid, "kind": out[0]["kind"] if out[0]["kind"] == "file" else "term", "title": title,
            "w": round(2 * PAD_X + (max(n, 24) + 1) * CW, 1), "h": y + PAD_B, "rows": out, "x0": x0}


def file_rows(lines, cols, wrap_lines=True):
    rows = []
    for n, line in enumerate(lines, 1):
        if n == len(lines) and line == "":
            break
        parts = (wrap(line, cols) if line else [""]) if wrap_lines else [line]
        for i, ln in enumerate(parts):
            rows.append({"kind": "file", "n": n if i == 0 else None, "line": n, "text": ln, "src": ["file", n, i]})
    return rows


def term_view(cid, steps, cols, anchor, nlines, focus_text, nfocus, band=None, prompt=True):
    """A window of whole lines: from the output line containing `anchor` (or the first), `nlines` source lines
    (None: to the end), with the prompt line(s) on top when `prompt`."""
    rows = term_rows(steps, cols)
    if anchor:
        k = find(rows, anchor)
        L0, sid0 = rows[k]["ln"], rows[k]["step"]
        sel = [i for i, r in enumerate(rows) if r["step"] == sid0 and r["kind"] == "out"
               and L0 <= r["ln"] < (L0 + nlines if nlines else 10 ** 6)]
        a, b = sel[0], sel[-1] + 1
    else:
        a, b = 0, len(rows)
    if prompt:
        a = 0
    f0 = find(rows, focus_text, a)
    focus = set(range(f0, f0 + nfocus))
    title = "agent-brain" if rows[a]["kind"] == "cmd" else STEP[steps[0]]["cmd"]
    c = view(cid, rows, a, b, focus, band, title)
    c["src"] = {"steps": steps, "cols": cols}
    return c


def file_view(cid, name, key, lines, cols, first_line, last_line, focus_lines, band, wrap_lines=True):
    rows = file_rows(lines, cols - GUTTER, wrap_lines)
    a = next(i for i, r in enumerate(rows) if r["line"] == first_line)
    b = max(i for i, r in enumerate(rows) if r["line"] == last_line) + 1
    focus = {i for i, r in enumerate(rows) if r["line"] in focus_lines}
    c = view(cid, rows, a, b, focus, band, name)
    c["src"] = {"file": key, "cols": cols - GUTTER, "wrap": wrap_lines}
    if not wrap_lines:            # an editor that does not wrap: long lines run past the window edge, clipped
        c["w"] = round(2 * PAD_X + cols * CW, 1)
        c["clip"] = True
    return c


def cards(fmt):
    w = fmt == "wide"
    H = FILES["handoff"]
    notes_after = FILES["NOTES.md@after"]
    return {
        # the cold start: before any handoff, a session is handed zero tasks
        # one whole output line, scrolled to: the cold start's task count
        "s1": term_view("s1", ["start0"], 44 if w else 28, "Project handoffs:", 1, "Project handoffs:", 2,
                        band="in", prompt=False),
        # after one handoff: the handoff overview at the end of what the next session is handed (three whole lines)
        "s2": term_view("s2", ["startup"], 44 if w else 28, "## Handoff overview", 3, "## Handoff overview",
                        4 if w else 5, band="in", prompt=False),
        "s3": term_view("s3", ["route"], 44 if w else 28, None, None, '{"project"', 1 if w else 2, band="in"),
        "s4a": file_view("s4a", H["name"], "handoff", H["lines"], 72 if w else 34, 20, 26, {23, 24}, "ev",
                         wrap_lines=not w),
        "s4b": file_view("s4b", "examples/todo-api/NOTES.md", "NOTES.md", FILES["NOTES.md"], 58 if w else 34, 7, 10,
                         {9}, "ev"),
        "s5": term_view("s5", ["refuse"], 44 if w else 30, None, None, "agent-brain error:", 2 if w else 3,
                        band="in"),
        "s6a": file_view("s6a", "examples/todo-api/NOTES.md", "NOTES.md@after", notes_after, 58 if w else 34, 7, 11,
                         {11}, "in"),
        "s6b": term_view("s6b", ["cur2"], 54 if w else 28, None, None, '"evidence_changed"', 1, band="ev"),
        "s7": term_view("s7", ["ls", "deps"], 44 if w else 28, None, None, "dependencies =", 1, band="in"),
    }


# id, t, end, type key, contract, focal
SPEC = [
    ("s1", 0.0, 2.0, "forget", "a fresh session is handed nothing: zero active tasks", "Project handoffs: 0"),
    ("s2", 2.0, 3.5, "remember", "after one handoff, the next session is handed its overview", "Handoff overview"),
    ("s3", 3.5, 5.5, "route", "a folder inside the project resolves to the project and its role", "project, role"),
    ("s4a", 5.5, 7.0, "cites", "the saved handoff file holds the line number and the exact quote", "line + quote"),
    ("s4b", 7.0, 8.0, "cites", "that is the real line 9 in the example repo", "line 9"),
    ("s5", 8.0, 10.0, "refuse", "saving again without naming what it replaces is refused", "error line"),
    ("s6a", 10.0, 11.0, "drift", "a line is added to the cited file", "line 11"),
    ("s6b", 11.0, 13.0, "drift", "the next `current` reports evidence_changed true", "evidence_changed: true"),
    ("s7", 13.0, 16.0, "plain", "the brain is a folder of plain files; the package has no dependencies",
     "file list, dependencies = []"),
    ("end", 16.0, DUR, "end", "name, one line, where to get it", "wordmark"),
]
# Camera angle per shot (degrees, held for the shot; the opener settles from a steeper angle).
ANGLE = {"s1": (22, -16), "s3": (4, 12), "s5": (3, -10), "s7": (6, 9)}
# 16:9 titles share one left margin, top or bottom; the card takes the other side.
PLACE = {"s1": "tl", "s2": "tl", "s3": "tl", "s4a": "tl", "s4b": "tl", "s5": "tl", "s6a": "tl", "s6b": "tl",
         "s7": "tl"}


def camera(sid, c, fmt):
    """The whole card, centred in the space the title leaves, as large as the frame allows with margins. Over the
    shot the camera pushes toward the focus rows: in 16:9 by up to 22 percent (the out-of-focus part of the card
    may run off the frame), in 9:16 only as far as the card stays inside the side margins."""
    W, H = SIZE[fmt]
    wide = fmt == "wide"
    if wide:
        top, bottom = (250, 1010) if PLACE[sid] == "tl" else (70, 830)
        if sid == "s7":
            top = 320
    else:
        top, bottom = (640 if sid == "s7" else 560), 1780
    tilt = 0.9 if sid in ANGLE and sid != "s1" else 1.0
    z0 = min(W * (0.80 if wide else 0.86) / c["w"], (bottom - top) / c["h"], 3.0) * tilt
    if not wide and sid == "s6b":       # the long JSON line: full width, its tail runs off the bottom of the frame
        z0 = W * 0.86 / c["w"]
    fr = [r for r in c["rows"] if r["focus"]]
    fy = (fr[0]["y"] + fr[-1]["y"] + LH) / 2
    fw = max(len(r["text"]) for r in fr) * CW
    if wide:
        z1 = min(z0 * 1.22, W * 0.86 / (fw + 2 * PAD_X), 3.4)
    else:
        z1 = min(z0 * 1.04, W * 0.90 / c["w"])
    z1 = max(z1, z0)
    sy = (top + bottom) / 2
    # never let the card slide under the title: the side facing the title stays in the card's space
    if not wide or PLACE[sid] == "tl":
        fy = min(fy, (sy - top) / z1)
    if not wide or PLACE[sid] == "bl":
        fy = max(fy, c["h"] - (bottom - sy) / z1)
    if not wide:
        fy = min(fy, (sy - top) / z1)
    # start: card centre at the centre of its space; end: the focus rows' centre there, the card's centre column kept
    cy0 = c["h"] / 2
    if not wide or PLACE[sid] == "tl":
        cy0 = min(cy0, (sy - top) / z0)
    return {"from": [c["w"] / 2, cy0, round(z0, 3), W / 2, round(sy)],
            "to": [c["w"] / 2, fy, round(z1, 3), W / 2, round(sy)]}


def shots():
    out = []
    C = {f: cards(f) for f in SIZE}
    for sid, t, end, ty, contract, focal in SPEC:
        s = {"id": sid, "t": t, "end": end, "card": sid if sid != "end" else None, "contract": contract,
             "focal": focal, "type": ty, "angle": ANGLE.get(sid, (0, 0))}
        for fmt in SIZE:
            if sid == "end":
                s[fmt] = {"from": [0, 0, 1, 0, 0], "to": [0, 0, 1, 0, 0]}
                continue
            s[fmt] = camera(sid, C[fmt][sid], fmt)
        if sid == "s1":
            s["hero"] = True
        out.append(s)
    return out, C


# One text focus per shot. 16:9: one left margin, top (tl) or bottom (bl); 9:16: top.
TYPE = {
    "forget": {"t": 0.0, "end": 2.0, "head": "Your agents forget.", "place": {"wide": "tl", "tall": "top"}},
    "remember": {"t": 2.0, "end": 3.5, "head": "It remembers.", "place": {"wide": "tl", "tall": "top"}},
    "route": {"t": 3.5, "end": 5.5, "head": "It knows your project.", "head_tall": "It knows\nyour project.",
              "place": {"wide": "tl", "tall": "top"}},
    "cites": {"t": 5.5, "end": 8.0, "head": "Every note cites the line.", "head_tall": "Every note\ncites the line.",
              "place": {"wide": "tl", "tall": "top"}},
    "refuse": {"t": 8.0, "end": 10.0, "head": "It refuses a silent overwrite.",
               "head_tall": "It refuses a\nsilent overwrite.", "place": {"wide": "tl", "tall": "top"}},
    "drift": {"t": 10.0, "end": 13.0, "head": "It notices when files change.",
              "head_tall": "It notices when\nfiles change.", "place": {"wide": "tl", "tall": "top"}},
    "plain": {"t": 13.0, "end": 16.0, "head": "Plain files, no service.", "head_tall": "Plain files,\nno service.",
              "sub": "Standard library Python only.", "place": {"wide": "tl", "tall": "top"}},
    "end": {"t": 16.0, "end": DUR, "head": "agent-brain", "sub": "Shared memory for Claude Code and Codex.",
            "sub_tall": "Shared memory for\nClaude Code and Codex.", "url": "github.com/VyasSathya/agent-brain"},
}

# Score cues: muffled until it remembers; drums out for one beat-pair at the refusal; a bell when evidence_changed
# turns true; the last chord on the end card.
MUSIC = {"open": 2.0, "full": 5.5, "refuse": 8.0, "back": 9.0, "true": 11.0, "end": 16.0}
# Light behind each card: a neutral cool key; it warms only when evidence_changed turns true.
LIGHT = {"s1": "132,140,176", "s2": "140,152,200", "s3": "140,152,200", "s4a": "150,150,170", "s4b": "150,150,170",
         "s5": "150,150,170", "s6a": "140,152,200", "s6b": "214,150,100", "s7": "140,152,200", "end": "140,140,160"}

if __name__ == "__main__":
    BUILD.mkdir(parents=True, exist_ok=True)
    SHOTS, C = shots()
    beats = [round(i * 60 / BPM, 3) for i in range(int(DUR * BPM / 60) + 1)]
    (BUILD / "storyboard.json").write_text(json.dumps(
        {"fps": FPS, "bpm": BPM, "duration": DUR, "beats": beats, "shots": SHOTS, "type": TYPE, "music": MUSIC,
         "light": LIGHT, "cards": C, "metrics": {"fs": FS, "lh": LH, "cw": CW, "pad_x": PAD_X, "header": HEADER,
                                                 "gutter": GUTTER}}, indent=1), encoding="utf-8")
    for s in SHOTS:
        print("%-4s %4.1f-%4.1f wide z %.2f->%.2f  tall z %.2f->%.2f" % (
            s["id"], s["t"], s["end"], s["wide"]["from"][2], s["wide"]["to"][2], s["tall"]["from"][2],
            s["tall"]["to"][2]))
