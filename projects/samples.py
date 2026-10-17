"""Neutral sample media for the pipeline tests: public-domain NASA video from Wikimedia Commons, fetched on
first use into the work folder (never committed). Commons asks for a descriptive User-Agent."""
from pathlib import Path

from studio import media

UA = "video-studio-samples/0.1 (https://github.com/VyasSathya/video-studio)"
SAMPLES = {
    # 55 min NASA all-hands event; we keep the first 20 minutes
    "kelly": ("https://upload.wikimedia.org/wikipedia/commons/a/a0/Scott_Kelly_Talks_About_His_Year_in_Space.webm",
              "kelly-20min.webm", 1200),
}


def sample(key):
    url, name, keep = SAMPLES[key]
    d = media.work_root() / "samples"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    if not p.exists():
        media.run(["-user_agent", UA, "-i", url] + (["-t", keep] if keep else []) + ["-c", "copy", p])
    return p
