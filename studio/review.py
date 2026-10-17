"""Review page for a run folder (manifest.json): the outputs to look at before anything is used anywhere.

    review.page(run_dir)            -> run_dir/review.html
    review.index([run_dir, ...], out)  -> one page listing several runs

Base view is titles only; each item opens on click. Nothing here posts anything: posting is a separate step
with its own approval queue.
"""
import html
import json
import os
from pathlib import Path


def esc(s):
    return html.escape(str(s), quote=True)


def _qc_line(q):
    if not q:
        return ""
    bits = ["%.1f s" % q["seconds"], "%.1f MB" % q["mb"]]
    if q.get("lufs") is not None:
        bits.append("%.1f LUFS" % q["lufs"])
    if q.get("true_peak") is not None:
        bits.append("peak %.1f dBTP" % q["true_peak"])
    if q.get("wpm"):
        bits.append("%.0f wpm" % q["wpm"])
    line = " &middot; ".join(bits)
    if q.get("problems"):
        line += '<div class="bad">%s</div>' % esc("; ".join(q["problems"]))
    return '<div class="meta">%s</div>' % line


def _rel(p, base):
    return os.path.relpath(p, base).replace("\\", "/")


def section(run_dir, base):
    run_dir = Path(run_dir)
    m = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    items = []
    for o in m.get("outputs", []):
        src = _rel(run_dir / o["file"], base)
        if o["kind"] == "video":
            cls = "tall" if o.get("aspect") == "9:16" else "wide"
            body = '<video class="%s" src="%s" controls preload="metadata"></video>' % (cls, esc(src))
        else:
            body = '<img class="still" src="%s" alt="%s">' % (esc(src), esc(o["label"]))
        extra = ""
        if o.get("why"):
            extra = '<p class="why">%s</p>' % esc(o["why"])
        items.append('<details><summary>%s</summary><div class="body">%s%s%s'
                     '<a class="file" href="%s">%s</a></div></details>'
                     % (esc(o["label"]), body, extra, _qc_line(o.get("qc")), esc(src), esc(o["file"])))
    for im in m.get("images", []):
        src = _rel(run_dir / im["file"], base)
        items.append('<details><summary>%s</summary><div class="body"><img class="still" src="%s" alt="%s">'
                     '</div></details>' % (esc(im["label"]), esc(src), esc(im["label"])))
    drafts = m.get("drafts")
    if drafts:
        if drafts.get("linkedin"):
            items.append(_text("LinkedIn post draft", drafts["linkedin"]))
        if drafts.get("x_thread"):
            items.append(_text("X thread draft", "\n\n".join("%d/ %s" % (i + 1, t) for i, t in
                                                              enumerate(drafts["x_thread"]))))
        if drafts.get("problems"):
            items.append('<details><summary>Draft checks not passed</summary><div class="body"><div class="bad">%s'
                         '</div></div></details>' % esc("; ".join(drafts["problems"])))
        if drafts.get("dropped"):
            items.append(_text("Dropped in review", "\n\n".join("%s\n(%s)" % (x["text"], x["why"])
                                                                 for x in drafts["dropped"])))
        if drafts.get("slides"):
            imgs = "".join('<img class="slide" src="%s" alt="slide %d">' % (esc(_rel(run_dir / s, base)), i + 1)
                           for i, s in enumerate(drafts["slides"]))
            items.append('<details><summary>Carousel slides</summary><div class="body"><div class="slides">%s'
                         '</div></div></details>' % imgs)
    if m.get("decisions"):
        rows = "".join('<tr><td>%s</td><td>%.2f&ndash;%.2f</td><td>%s</td></tr>' % (
            esc(d["why"]), d["start"], d["end"], esc(d.get("text", ""))) for d in m["decisions"])
        items.append('<details><summary>Every cut</summary><div class="body"><table>%s</table></div></details>'
                     % rows)
    src = m.get("source") or {}
    sub = " &middot; ".join(esc(x) for x in [m.get("created", ""), src.get("credit") or ""] if x)
    return ('<section><h2>%s</h2><div class="sub">%s</div>%s</section>' % (esc(m.get("title") or run_dir.name),
                                                                           sub, "".join(items)))


def _text(title, text):
    return ('<details><summary>%s</summary><div class="body"><pre>%s</pre>'
            '<button onclick="navigator.clipboard.writeText(this.previousElementSibling.innerText)">Copy</button>'
            '</div></details>' % (esc(title), esc(text)))


def page(run_dir, out=None):
    run_dir = Path(run_dir)
    out = Path(out or run_dir / "review.html")
    m = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    out.write_text(PAGE.replace("__TITLE__", esc(m.get("title") or run_dir.name))
                   .replace("__BODY__", section(run_dir, out.parent)), encoding="utf-8")
    return out


def index(run_dirs, out):
    out = Path(out)
    body = "".join(section(r, out.parent) for r in run_dirs if (Path(r) / "manifest.json").exists())
    out.write_text(PAGE.replace("__TITLE__", "Review").replace("__BODY__", body), encoding="utf-8")
    return out


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root { --bg: #fafafa; --card: #ffffff; --line: #e6e6ea; --text: #17171a; --muted: #6b6b75; --accent: #b98900;
        --bad: #c0392b; color-scheme: light; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #0e0e10; --card: #151518; --line: #26262c; --text: #ececf0; --muted: #9a9aa5; --accent: #ffd84d;
          --bad: #ff7a6b; color-scheme: dark; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 15px/1.5 Inter, system-ui, sans-serif;
       -webkit-font-smoothing: antialiased; }
main { max-width: 980px; margin: 0 auto; padding: 40px 16px 80px; }
section { margin-bottom: 40px; }
h2 { font-size: 20px; font-weight: 600; letter-spacing: -0.01em; margin: 0 0 4px; }
.sub { color: var(--muted); font-size: 13px; margin-bottom: 14px; }
details { background: var(--card); border: 1px solid var(--line); border-radius: 10px; margin: 8px 0; }
summary { cursor: pointer; padding: 12px 16px; font-weight: 500; list-style: none; }
summary::-webkit-details-marker { display: none; }
summary::after { content: "+"; float: right; color: var(--muted); }
details[open] summary::after { content: "\\2212"; }
.body { padding: 0 16px 16px; }
video.wide { width: 100%; border-radius: 8px; background: #000; }
video.tall { width: min(100%, 420px); aspect-ratio: 9 / 16; height: auto; border-radius: 8px; background: #000;
             display: block; }
img.still { width: 100%; border-radius: 8px; border: 1px solid var(--line); }
.slides { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
img.slide { width: 100%; border-radius: 8px; border: 1px solid var(--line); }
.meta { color: var(--muted); font-size: 13px; margin-top: 8px; }
.bad { color: var(--bad); margin-top: 4px; }
.why { color: var(--muted); margin: 8px 0 0; }
a.file { display: inline-block; margin-top: 6px; font-size: 13px; color: var(--muted); font-feature-settings: "calt" 0; }
pre { white-space: pre-wrap; font: inherit; margin: 0 0 10px; }
button { font: inherit; font-size: 13px; padding: 6px 12px; border-radius: 8px; border: 1px solid var(--line);
         background: var(--bg); color: var(--text); cursor: pointer; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
td { padding: 5px 8px; border-top: 1px solid var(--line); color: var(--muted); }
td:first-child { color: var(--text); white-space: nowrap; }
td:nth-child(2) { white-space: nowrap; font-variant-numeric: tabular-nums; }
</style></head>
<body><main>__BODY__</main></body></html>
"""
