"""Turn session.json into timed audio and a timeline the panel renderer and the composition both read.

    python projects/talkover-demo/timeline.py            # writes build/ (audio clips, mix.wav, timeline.json)

Timing follows Talkover's own rules: an utterance ends after 600 ms of silence and is typed when Whisper answers;
the speak hook reads a reply in Split-Chunks pieces; a barge-in pauses the reading after 500 ms of voice and the
transcript then ends it. Waits for Claude are shortened (the video marks them as sped up); everything said is played
at real speed.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
from studio import engines, media   # noqa: E402
from chunks import split_chunks      # noqa: E402

BUILD = HERE / "build"
TITLE_S = 2.6          # title card
LEAD_S = 0.7           # scene on screen before the first word
ENDPOINT_S = 0.9       # 600 ms of silence + Whisper
TOOL_S = 0.7           # message typed -> tool row shows
THINK_S = (2.4, 2.8)   # message typed -> first audio, per turn (real waits were 10 to 13 s)
GAP_S = 0.12           # between chunks (the hook fetches the next chunk while one plays)
BARGE_S = 0.5          # voiced audio before the reading pauses
END_HOLD_S = 1.3       # after the last event, before the end card
END_S = 3.6            # end card


def clip(name, text, voice, speed=1.0):
    wav = BUILD / "audio" / (name + ".wav")
    meta = wav.with_suffix(".json")
    if meta.exists():
        m = json.loads(meta.read_text(encoding="utf-8"))
        if m.get("text") == text and m.get("voice") == voice and m.get("speed") == speed:
            return m
    dur = engines.tts(text, wav, voice=voice, speed=speed)
    heard = engines.stt(wav)
    m = {"name": name, "text": text, "voice": voice, "speed": speed, "wav": str(wav), "dur": round(dur, 3),
         "heard": heard["text"], "words": [{"w": w["word"].strip(), "s": w["start"], "e": w["end"]}
                                            for w in heard["words"]]}
    meta.write_text(json.dumps(m, indent=1), encoding="utf-8")
    return m


def main():
    s = json.loads((HERE / "session.json").read_text(encoding="utf-8"))
    BUILD.mkdir(exist_ok=True)
    yv, cv, sp = s["you_voice"], s["claude_voice"], s["claude_speed"]
    t = TITLE_S + LEAD_S
    ev = []        # every timed thing, in order
    audio = []     # (wav, start, cut_at or None)
    turns = s["turns"]
    for i, turn in enumerate(turns):
        you = clip("you%d" % (i + 1), turn["you"], yv)
        if you["heard"] != turn["heard"]:
            print("note: Whisper now hears %r for turn %d (session.json has %r)" % (you["heard"], i + 1, turn["heard"]))
        if i > 0 and ev and ev[-1]["kind"] == "cut":
            t = ev[-1]["you_t"]
        ev.append({"kind": "you", "t": round(t, 3), "dur": you["dur"], "text": turn["you"], "heard": you["heard"],
                   "words": you["words"], "turn": i})
        audio.append((you["wav"], t, None))
        typed = t + you["dur"] + ENDPOINT_S
        if turn.get("command") == "mute":
            ev.append({"kind": "mute", "t": round(typed, 3), "turn": i})
            t = typed + END_HOLD_S
            break
        ev.append({"kind": "typed", "t": round(typed, 3), "text": turn["sent"], "heard": you["heard"], "turn": i})
        for k, tool in enumerate(turn.get("tools", [])):
            ev.append({"kind": "tool", "t": round(typed + TOOL_S + 0.35 * k, 3), "text": tool, "turn": i,
                       "diff": turn.get("diff") if tool.startswith("Edit") else None})
        start = typed + THINK_S[min(i, len(THINK_S) - 1)]
        ev.append({"kind": "reply", "t": round(start - 0.35, 3), "text": turn["reply"], "turn": i,
                   "think_from": round(typed, 3)})
        chunks = split_chunks(turn["reply"])
        t = start
        cut_chunk = turn.get("cut_in_chunk")
        for k, text in enumerate(chunks):
            c = clip("c%d_%d" % (i + 1, k), text, cv, sp)
            if cut_chunk is not None and k == cut_chunk:
                you_t = t + c["dur"] * turn["cut_in_at"]
                pause_t = you_t + BARGE_S
                ev.append({"kind": "chunk", "t": round(t, 3), "dur": round(pause_t - t, 3), "full": c["dur"],
                           "text": text, "words": c["words"], "wav": c["wav"], "turn": i, "k": k, "cut": True})
                audio.append((c["wav"], t, pause_t - t))
                ev.append({"kind": "cut", "t": round(pause_t, 3), "you_t": round(you_t, 3), "turn": i, "k": k})
                break
            ev.append({"kind": "chunk", "t": round(t, 3), "dur": c["dur"], "full": c["dur"], "text": text,
                       "words": c["words"], "wav": c["wav"], "turn": i, "k": k})
            audio.append((c["wav"], t, None))
            t += c["dur"] + GAP_S
        else:
            t += 0.5
    end_t = t
    total = end_t + END_S
    tl = {"fps": 30, "title_s": TITLE_S, "scene": [TITLE_S, round(end_t, 3)], "end": [round(end_t, 3), round(total, 3)],
          "duration": round(total, 3), "events": ev}
    (BUILD / "timeline.json").write_text(json.dumps(tl, indent=1), encoding="utf-8")
    media.mix(audio, total, BUILD / "mix.wav")
    print("timeline: %.1f s (scene %.1f to %.1f), %d events -> %s" % (total, TITLE_S, end_t, len(ev), BUILD))


if __name__ == "__main__":
    main()
