"""Free B-roll stills: Wikimedia Commons search, public domain and CC0 only, with the credit recorded.

    find("black hole", out_dir) -> {"file", "title", "license", "credit", "page"} or None

No key, no account. Every file used is listed in the run's manifest with its source page, so the credit can be
checked. Anything with attribution or share-alike terms is skipped rather than risked.
"""
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
UA = "video-studio/0.1 (https://github.com/VyasSathya/video-studio)"
FREE = ("public domain", "cc0", "pd")


def _get(params):
    url = API + "?" + urllib.parse.urlencode(dict(params, format="json"))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _clean(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def find(query, out_dir, min_w=1200, avoid=()):
    """The first free image for the query, else for its longest word alone."""
    hit = _find(query, out_dir, min_w, avoid)
    words = sorted(re.findall(r"[A-Za-z]{3,}", query), key=lambda w: (not w[0].isupper(), -len(w)))
    for w in (words if len(words) > 1 else []):   # names first ("Mars" before "planet"), then longer words
        if hit:
            break
        hit = _find(w, out_dir, min_w, avoid)
    return hit


def _find(query, out_dir, min_w=1200, avoid=()):
    res = _get({"action": "query", "generator": "search", "gsrnamespace": 6, "gsrlimit": 20,
                "gsrsearch": "filetype:bitmap " + query, "prop": "imageinfo",
                "iiprop": "url|size|extmetadata|mime", "iiurlwidth": 1600})
    pages = sorted((res.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata", {})
        lic = _clean(meta.get("LicenseShortName", {}).get("value", "")).lower()
        if not lic.startswith(FREE) or ii.get("width", 0) < min_w or ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if p["title"] in avoid:
            continue
        want = [w for w in re.findall(r"[a-z]{3,}", query.lower()) if w not in ("photo", "picture", "image", "the", "and")]
        if want and not all(w in p["title"].lower() for w in want):
            continue                               # the file must be what was asked for, by its own title
        url = ii.get("thumburl") or ii["url"]
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ext = ".png" if ii["mime"] == "image/png" else ".jpg"
        dst = out_dir / (re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")[:40] + ext)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            dst.write_bytes(r.read())
        artist = _clean(meta.get("Artist", {}).get("value", "")) or "unknown"
        return {"file": str(dst), "title": p["title"], "license": _clean(meta.get("LicenseShortName", {})
                                                                          .get("value", "")),
                "credit": "%s, %s, via Wikimedia Commons" % (artist[:80], lic),
                "page": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_"))}
    return None
