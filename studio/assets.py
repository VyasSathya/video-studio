"""Gather assets for an edit, free sources first, each with where it came from and its licence.

    gather([{"kind": "site", "url": "https://...", "name": "home"},          # still of a real page (capture.mjs)
            {"kind": "record", "shot": "shot.json", "name": "tour"},          # scripted screen recording (webrec.mjs)
            {"kind": "broll", "query": "space station", "name": "iss"},       # public-domain still (Commons)
            {"kind": "ai_clip", "prompt": "...", "image_url": "...", "seconds": 5, "confirm": False}],
           out_dir) -> assets.json

An ai_clip is a paid image-to-video call (studio.paid.kie_clip, Kling through kie.ai). It stays a dry run with
its price unless KIE_API_KEY and STUDIO_ALLOW_SPEND=1 are set and the spec says confirm: true. Generated clips
are accent shots only: no people, hands, faces or text in them, and never a shot that makes a product claim.
"""
import json
import subprocess
from pathlib import Path

from . import paid, stock

ROOT = Path(__file__).resolve().parents[1]


def gather(specs, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    got = []
    for s in specs:
        k, name = s["kind"], s.get("name") or s["kind"]
        if k == "site":
            cfg = out / (name + ".capture.json")
            cfg.write_text(json.dumps({"url": s["url"], "width": s.get("width", 1440), "height": s.get("height", 900),
                                       "scale": 2, "colorScheme": s.get("scheme", "light"),
                                       "shots": [{"name": name, "steps": s.get("steps", []),
                                                  "focus": s.get("focus")}]}), encoding="utf-8")
            subprocess.run(["node", str(ROOT / "studio" / "capture.mjs"), str(cfg), str(out)], check=True, cwd=str(ROOT))
            got.append({"name": name, "kind": k, "file": str(out / (name + ".png")), "source": s["url"],
                        "licence": "screen capture of a page the owner chose; check its terms before publishing"})
        elif k == "record":
            mp4 = out / (name + ".mp4")
            subprocess.run(["node", str(ROOT / "studio" / "webrec.mjs"), str(s["shot"]), str(mp4)], check=True,
                           cwd=str(ROOT))
            got.append({"name": name, "kind": k, "file": str(mp4), "source": s["shot"], "licence": "own recording"})
        elif k == "broll":
            hit = stock.find(s["query"], out / "stock")
            got.append({"name": name, "kind": k, "file": hit["file"] if hit else None,
                        "source": hit["page"] if hit else None, "licence": hit["license"] if hit else None,
                        "credit": hit["credit"] if hit else None, "found": bool(hit)})
        elif k == "ai_clip":
            r = paid.kie_clip(s["prompt"], s["image_url"], seconds=s.get("seconds", 5), sound=s.get("sound", False),
                              out=out / (name + ".mp4"), confirm=bool(s.get("confirm")))
            got.append({"name": name, "kind": k, "result": r,
                        "licence": "generated (Kling via kie.ai); accent shot only, no people or text"})
    (out / "assets.json").write_text(json.dumps(got, indent=1), encoding="utf-8")
    return got
