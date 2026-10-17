"""Judgment steps, asked of a text model (studio.llm) and checked against the transcript so nothing is invented.

callouts(words)       -> title and 2-4 on-screen callouts, each anchored to words actually said
clips(segments, ...)  -> the best stand-alone short clips in a long transcript, as source time ranges
posts(transcript, ..) -> draft LinkedIn post, X thread and carousel slides (drafts for review, never posted)
"""
import json
import re

from . import edit, llm


def norm(s):
    return re.sub(r"[^a-z0-9' ]+", " ", s.lower()).split()


def find_phrase(words, quote, after=0.0):
    """Start/end time of the first run of words matching quote (case and punctuation ignored)."""
    q = norm(quote)
    b = [" ".join(norm(w["text"])) for w in words]
    for i in range(len(words) - len(q) + 1):
        if words[i]["start"] >= after and b[i:i + len(q)] == q:
            return words[i]["start"], words[i + len(q) - 1]["end"]
    return None


def transcript_text(words):
    return " ".join(w["text"] for w in words)


def callouts(words, max_n=3):
    text = transcript_text(words)
    prompt = (
        "Transcript of a short talking-head video:\n\n" + text + "\n\n"
        "Return JSON only: {\"title\": a hook title of at most 6 words that is true to what is said, "
        "\"callouts\": [{\"quote\": 2 to 5 consecutive words copied exactly from the transcript, "
        "\"label\": the fact itself as on-screen text, at most 4 words}]}. "
        "Example: quote \"for 340 days\", label \"340 days in orbit\". A label is never a category name like "
        "\"Location\" or \"Timeframe\". Give %d callouts, spread across the video, each on a concrete fact (a "
        "number, a place, a duration). Do not invent anything that is not said." % max_n)
    res = llm.complete(prompt, want_json=True)
    said = set(norm(text))
    out = []
    for c in res.get("callouts", []):
        hit = find_phrase(words, c.get("quote", ""))
        label = (c.get("label") or "").strip()
        # a label may only use words said within a few seconds of its quote; otherwise show the quote itself
        near = set(norm(" ".join(w["text"] for w in words if hit and abs(w["start"] - hit[0]) <= 6))) if hit else said
        if not label or len(label) > 28 or not set(norm(label)) <= near:
            q = c.get("quote", "").strip()
            label = q[:1].upper() + q[1:]
        if hit and label and len(label) <= 28 and all(abs(hit[0] - o["t"]) > 6 for o in out):
            out.append({"t": round(hit[0], 2), "text": label, "quote": c["quote"]})
    return {"title": (res.get("title") or "").strip()[:48], "callouts": out[:max_n], "backend": llm.backend()}


def candidates(words, min_s=20, max_s=55, target=38, stride=8):
    """Sentence-aligned windows: start at a sentence, add sentences until about `target` seconds."""
    sents = sentences(words)
    out, last = [], -1e9
    for i, s in enumerate(sents):
        if s["start"] - last < stride:
            continue
        j = i
        while j + 1 < len(sents) and sents[j + 1]["end"] - s["start"] <= target:
            j += 1
        while j + 1 < len(sents) and sents[j]["end"] - s["start"] < min_s and sents[j + 1]["end"] - s["start"] <= max_s:
            j += 1
        d = sents[j]["end"] - s["start"]
        if min_s <= d <= max_s:
            out.append({"start": s["start"], "end": sents[j]["end"], "text": " ".join(x["text"] for x in sents[i:j + 1])})
            last = s["start"]
    return out


def clips(words, n=3, min_s=20, max_s=55, batch=8):
    """Score every candidate window in small batches (the model only sees each window's own words, so its
    titles stay true to the clip), then keep the n best that do not overlap."""
    cands = candidates(words, min_s, max_s)
    for k in range(0, len(cands), batch):
        part = cands[k:k + batch]
        prompt = ("Candidate clips cut from a long video. For each, judge it as a stand-alone vertical short: a "
                  "hook in the first sentence, one complete idea, a satisfying end, makes sense without the rest "
                  "of the video, one person speaking.\n\n" +
                  "\n\n".join("C%d: %s" % (k + i, c["text"]) for i, c in enumerate(part)) +
                  "\n\nReturn JSON only: {\"scores\": [{\"id\": number, \"score\": 1 to 10, \"title\": hook title "
                  "of at most 7 words using only what this clip says, \"reason\": one short sentence about this "
                  "clip only}]}")
        try:
            res = llm.complete(prompt, want_json=True)
        except Exception:
            continue
        for r in res.get("scores", []):
            try:
                idx = int(str(r.get("id")).lstrip("C"))
            except ValueError:
                continue
            if k <= idx < k + len(part):
                cands[idx].update(score=float(r.get("score") or 0), title=str(r.get("title") or "")[:60],
                                  why=str(r.get("reason") or ""))
    ranked = sorted((c for c in cands if c.get("score")), key=lambda c: -c["score"])
    out = []
    for c in ranked:
        if all(c["end"] <= o["start"] or c["start"] >= o["end"] for o in out):
            out.append({k: (round(v, 2) if isinstance(v, float) else v) for k, v in c.items()})
        if len(out) == n:
            break
    return {"clips": out, "backend": llm.backend(), "candidates": len(cands)}


def clips_by_lines(words, n=3, min_s=20, max_s=55):
    """One-shot variant for a strong model: it picks ranges of numbered sentences from the whole transcript."""
    sents = sentences(words)
    lines = ["L%d [%d:%02d] %s" % (i, s["start"] // 60, s["start"] % 60, s["text"]) for i, s in enumerate(sents)]
    prompt = (
        "Numbered transcript of a long video, one sentence per line, with the time it starts:\n\n" +
        "\n".join(lines) + "\n\n"
        "Pick the %d best moments to post as stand-alone vertical clips, each %d to %d seconds long: a clear hook "
        "in the first sentence, one complete idea, a satisfying end, understandable without the rest of the "
        "video. Return JSON only: {\"clips\": [{\"first_line\": number, \"last_line\": number, \"title\": hook "
        "title of at most 7 words, true to what is said, \"why\": one sentence}]}" % (n, min_s, max_s))
    res = llm.complete(prompt, want_json=True)
    out = []
    for c in res.get("clips", []):
        try:
            a, b = int(str(c.get("first_line")).lstrip("L")), int(str(c.get("last_line")).lstrip("L"))
        except ValueError:
            continue
        if not (0 <= a <= b < len(sents)):
            continue
        s, e = sents[a]["start"], sents[b]["end"]
        while e - s > max_s and b > a:        # too long: drop sentences from the end
            b -= 1
            e = sents[b]["end"]
        while e - s < min_s and b + 1 < len(sents):  # too short: add the next sentence
            b += 1
            e = sents[b]["end"]
        if min_s * 0.8 <= e - s <= max_s * 1.15 and all(e <= o["start"] or s >= o["end"] for o in out):
            out.append({"start": round(s, 2), "end": round(e, 2), "title": (c.get("title") or "")[:60],
                        "why": c.get("why", ""), "lines": [a, b]})
    return {"clips": out[:n], "backend": llm.backend(), "asked": res}


def sentences(words, max_words=45):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if w["text"].rstrip().endswith((".", "?", "!")) or len(cur) >= max_words:
            out.append({"start": cur[0]["start"], "end": cur[-1]["end"], "text": " ".join(x["text"] for x in cur)})
            cur = []
    if cur:
        out.append({"start": cur[0]["start"], "end": cur[-1]["end"], "text": " ".join(x["text"] for x in cur)})
    return out


FIRST_PERSON = re.compile(r"\b(i|i'm|i've|i'd|i'll|me|my|mine|myself)\b", re.I)


NUMBER_WORDS = {w: str(i) for i, w in enumerate("zero one two three four five six seven eight nine ten eleven "
                                                 "twelve thirteen fourteen fifteen sixteen seventeen eighteen "
                                                 "nineteen twenty".split())}


def _nums(s):
    return set(re.findall(r"\d+(?:\.\d+)?", str(s).replace(",", "")))


def number_claims(s):
    """(number, the word it counts) pairs: "340 days" -> ("340", "days"); "six spacewalks" -> ("6", "space")."""
    toks = re.findall(r"[a-z]+|\d+(?:\.\d+)?", str(s).lower().replace(",", ""))
    out = set()
    for i, t in enumerate(toks):
        n = NUMBER_WORDS.get(t, t if t[0].isdigit() else None)
        if n is None:
            continue
        nxt = [w for w in toks[i + 1:i + 4] if not w[0].isdigit() and w not in ("of", "the", "a", "more", "than")]
        out.add((n, nxt[0][:5] if nxt else ""))
    return out


def unsupported_numbers(claims_text, source_text):
    have = number_claims(source_text)
    have_n = {n for n, _ in have}
    return sorted("%s %s" % c for c in number_claims(claims_text) if c not in have and
                  not (c[1] == "" and c[0] in have_n))


def check_posts(res, text, voice="third"):
    """Problems with a set of drafts, or []: numbers must be in the transcript; in the third-person voice no
    draft speaks as anyone in the video; lengths and shapes as asked."""
    problems = []
    li, xs, car = res.get("linkedin") or "", res.get("x_thread") or [], res.get("carousel") or []
    blob = " ".join([li] + [str(x) for x in xs] + [" ".join(str(v) for v in c.values()) for c in car])
    bad = unsupported_numbers(blob, text)
    if bad:
        problems.append("numbers the transcript does not say: " + ", ".join(bad))
    if voice == "third" and FIRST_PERSON.search(blob):
        problems.append("written in the first person as someone in the video")
    if not 90 <= len(li.split()) <= 230:
        problems.append("LinkedIn post is %d words" % len(li.split()))
    if not 3 <= len(xs) <= 7 or any(len(str(x)) > 280 for x in xs):
        problems.append("X thread shape")
    if not 4 <= len(car) <= 8:
        problems.append("carousel has %d slides" % len(car))
    return problems


def posts(text, title, link_hint="(link to the full video)", voice="third", tries=3):
    """Drafts for review, never posted. voice="third" writes about the people in the video (anyone else's
    footage); voice="first" writes as the speaker, only for the poster's own video."""
    who = ("Write as the speaker, in the first person: this is the poster's own video." if voice == "first" else
           "Write about the people in the video in the third person; never write as them (no I, me, my).")
    prompt = (
        "Source transcript:\n\n" + text[:24000] + "\n\n"
        "Write drafts that repurpose this video, true to what is said, no invented facts, every number exactly as "
        "said in the transcript, at most 3 hashtags per post, no emojis. " + who + " Return JSON only: {"
        "\"linkedin\": a LinkedIn post of 130 to 200 words in 3 or 4 short paragraphs ending with " + link_hint + ", "
        "\"x_thread\": [4 to 6 posts, each under 270 characters], "
        "\"carousel\": [5 to 7 slides, each {\"head\": at most 7 words, \"body\": at most 22 words}]} "
        "Video title: " + title)
    best = None
    for _ in range(tries):
        res = llm.complete(prompt, want_json=True)
        res["problems"] = check_posts(res, text, voice)
        if best is None or len(res["problems"]) < len(best["problems"]):
            best = res
        if not res["problems"]:
            break
    best["backend"] = llm.backend()
    best["voice"] = voice
    return best


def retimed_callouts(callouts_res, words_src, keep):
    """Map callout times found on source words onto an edited timeline."""
    out = []
    for c in callouts_res:
        t = edit.map_time(c["t"], keep)
        if t is not None:
            out.append(dict(c, t=round(t, 2)))
    return out
