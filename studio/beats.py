"""Plan overlay beats from a plain-language prompt, the way you would brief an editor:

    "When he says Mars, bring in a picture of Mars on the right. When he says 340 days, show a big number.
     Highlight the key words at the bottom."

    rules = parse(prompt)                 # a text model turns the prompt into rules (or write them yourself)
    beats = place(rules, words, duration) # each rule fires where its trigger words were actually said

A rule: {"when": "340 days", "show": "number" | "image" | "card" | "draw" | "bullets" | "takeover",
         "text": "...", "query": "...", "side": "left" | "right" | "center", "hold": seconds}
Placement is deterministic: a trigger that is never said places nothing (and is reported), so nothing appears
over words that do not match it. Beats never overlap; a later beat waits until the earlier one is gone.
"""
import re

from . import llm, picks

KINDS = {"number", "image", "card", "draw", "bullets", "takeover"}


def parse(prompt, words=None):
    said = picks.transcript_text(words)[:6000] if words else ""
    q = ("An editor's instructions for overlays on a talking video:\n\n" + prompt + "\n\n" +
         ("Transcript, for the exact trigger words:\n" + said + "\n\n" if said else "") +
         "Turn each instruction into a rule. Return JSON only: {\"rules\": [{\"when\": the exact words that trigger "
         "it (2 to 4 words copied from the transcript if one is given), \"show\": one of number, image, card, draw, "
         "bullets, takeover, \"text\": the words to show (at most 6), \"query\": 2 to 4 words to search a public-domain "
         "photo archive (image only), \"draw\": for draw or takeover, what to draw if the instructions say (clock, planet, arrow, star, rocket), \"side\": left, right or center, \"hold\": seconds, 2 to 5}], "
         "\"highlight_keywords\": true or false}")
    res = llm.complete(q, want_json=True)
    rules = []
    for r in res.get("rules", []):
        if r.get("show") not in KINDS or not str(r.get("when", "")).strip():
            continue
        text = r.get("text", "")
        if isinstance(text, (list, tuple)):          # models sometimes return the bullets as a list
            text = ", ".join(str(x) for x in text)
        rules.append({"when": str(r["when"]).strip(), "show": r["show"], "text": str(text)[:60],
                      "query": str(r.get("query", "")), "draw": str(r.get("draw", "") or ""),
                      "side": r.get("side") if r.get("side") in
                      ("left", "right", "center") else "right", "hold": float(r.get("hold") or 3)})
    return {"rules": rules, "highlight_keywords": bool(res.get("highlight_keywords", True)), "backend": llm.backend()}


def place(rules, words, duration, gap=0.4, tail=1.5):
    """tail: seconds at the end that stay on the speaker, so a film never ends on a card."""
    beats, missing, busy_until = [], [], 0.0
    for r in rules:
        hit = picks.find_phrase(words, r["when"], after=0.0)
        if not hit:
            missing.append(r["when"])
            continue
        t = max(hit[0] - 0.15, busy_until + gap)
        r = dict(r)
        if r["show"] in ("takeover", "draw") and t + 1.5 > duration - tail:
            r["show"] = "card"                    # too late for a full takeover: keep the speaker in view
        end_limit = duration - (tail if r["show"] in ("takeover", "draw") else 0.2)
        if t >= end_limit - 1.0:
            missing.append(r["when"])
            continue
        hold = min(r.get("hold", 3.0), end_limit - t)
        beats.append(dict(r, t=round(t, 2), end=round(t + hold, 2)))
        busy_until = t + hold
    beats.sort(key=lambda b: b["t"])
    return {"beats": beats, "not_said": missing}


STOP = set("the a an and or but so of to in on at for with is are was were be been it its this that these those i "
           "you he she we they my your our their me him her them as by from up out about into over just like then "
           "than there here what when where who how which not no yes do does did have has had will would can could "
           "know get got going really very".split())


def keywords(words, every=6.0):
    """One emphasis word per stretch of speech: the longest content word, numbers first."""
    out, last = [], -1e9
    for i, w in enumerate(words):
        b = re.sub(r"[^\w']", "", w["text"].lower())
        if w["start"] - last < every or b in STOP or len(b) < 5 and not b.isdigit():
            continue
        window = [x for x in words[i:i + 12] if x["start"] - w["start"] < 3]
        best = max(window, key=lambda x: (re.sub(r"[^\d]", "", x["text"]) != "",
                                          len(re.sub(r"[^\w]", "", x["text"]))))
        out.append(best["start"])
        last = best["start"]
    return out
