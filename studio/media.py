"""ffmpeg helpers: find a build with libx264, mix timed clips, make GIFs and QA contact sheets."""
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ffmpeg_bin() -> str:
    """ffmpeg with libx264: STUDIO_FFMPEG, then tools/ffmpeg-*/bin (scripts/setup.ps1 puts one there), then PATH."""
    env = os.getenv("STUDIO_FFMPEG")
    if env:
        return env
    for d in sorted((ROOT / "tools").glob("ffmpeg-*/bin"), reverse=True):
        exe = d / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if exe.exists():
            return str(exe)
    return shutil.which("ffmpeg") or "ffmpeg"


def work_root() -> Path:
    """STUDIO_WORK, else D:/video-studio-work when a D: drive exists, else build/ in the repo."""
    return Path(os.getenv("STUDIO_WORK") or (r"D:\video-studio-work" if os.name == "nt" and Path("D:/").exists()
                                             else str(ROOT / "build")))


def work_dir(name: str) -> Path:
    """Scratch space for one run, under work_root()/runs."""
    p = work_root() / "runs" / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def ffprobe_bin() -> str:
    f = Path(ffmpeg_bin())
    p = f.with_name(f.name.replace("ffmpeg", "ffprobe"))
    return str(p) if p.exists() else (shutil.which("ffprobe") or "ffprobe")


def env_with_ffmpeg() -> dict:
    """Environment whose PATH finds our ffmpeg first (HyperFrames shells out to ffmpeg by name)."""
    e = dict(os.environ)
    e["PATH"] = str(Path(ffmpeg_bin()).parent) + os.pathsep + e.get("PATH", "")
    return e


def run(args, **kw):
    cmd = [ffmpeg_bin(), "-hide_banner", "-v", "error", "-y"] + [str(a) for a in args]
    subprocess.run(cmd, check=True, **kw)


def duration(path) -> float:
    out = subprocess.run([ffprobe_bin(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(path)], capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def mix(clips, total: float, out, rate: int = 48000) -> None:
    """clips: (wav, start_s, keep_s or None). Each clip is placed at its start, cut (with a 40 ms fade) when keep_s is
    given, and everything is summed into one mono wav of `total` seconds, peak-limited."""
    args, parts = [], []
    for i, (wav, start, keep) in enumerate(clips):
        args += ["-i", wav]
        f = "[%d:a]aresample=%d,aformat=channel_layouts=mono" % (i, rate)
        if keep is not None:
            f += ",atrim=0:%.3f,afade=t=out:st=%.3f:d=0.04" % (keep, max(0.0, keep - 0.04))
        f += ",adelay=%d:all=1[a%d]" % (int(round(start * 1000)), i)
        parts.append(f)
    n = len(clips)
    graph = ";".join(parts) + ";" + "".join("[a%d]" % i for i in range(n)) + \
        "amix=inputs=%d:normalize=0:duration=longest,apad,atrim=0:%.3f,alimiter=limit=0.95[out]" % (n, total)
    run(args + ["-filter_complex", graph, "-map", "[out]", "-ar", rate, "-ac", 1, out])


def mux_loud(video, audio, out, target=-14.0, peak=-1.5, crf=20, max_rate="8M"):
    """Picture from `video`, sound from `audio`, two-pass loudnorm to `target` LUFS (one pass undershoots),
    re-encoded to H.264 at a size meant for sharing."""
    import json as _json
    p = subprocess.run([ffmpeg_bin(), "-hide_banner", "-nostats", "-i", str(audio), "-af",
                        "loudnorm=I=%g:TP=%g:LRA=11:print_format=json" % (target, peak), "-f", "null", "-"],
                       capture_output=True, text=True)
    m = _json.loads(p.stderr[p.stderr.rfind("{"):p.stderr.rfind("}") + 1])
    af = ("loudnorm=I=%g:TP=%g:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:"
          "offset=%s:linear=true" % (target, peak, m["input_i"], m["input_tp"], m["input_lra"], m["input_thresh"],
                                     m["target_offset"]))
    run(["-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", crf, "-maxrate", max_rate,
         "-bufsize", "16M", "-preset", "slow", "-pix_fmt", "yuv420p", "-af", af, "-ar", 48000, "-c:a", "aac",
         "-b:a", "192k", "-shortest", "-movflags", "+faststart", out])
    return Path(out)


def gif(src, out, start: float = 0, length: float = None, width: int = 960, fps: int = 15, colors: int = 160,
        max_mb: float = 8.0) -> Path:
    """Palette GIF; steps width and fps down until it is under max_mb."""
    out = Path(out)
    for w, f in ((width, fps), (int(width * 0.85), fps), (int(width * 0.75), 12), (int(width * 0.6), 10)):
        args = ["-ss", start] + (["-t", length] if length else []) + ["-i", src, "-vf",
                "fps=%d,scale=%d:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=%d:stats_mode=diff[p];"
                "[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle" % (f, w, colors), "-loop", 0, out]
        run(args)
        if out.stat().st_size <= max_mb * 1024 * 1024:
            break
    return out


def frames(src, out_dir, times) -> list:
    """Extract one PNG per time (seconds) for looking at."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for t in times:
        p = out_dir / ("t%06.2f.png" % t)
        run(["-ss", "%.3f" % t, "-i", src, "-frames:v", 1, p])
        paths.append(p)
    return paths


def contact_sheet(src, out, every: float = 3.0, cols: int = 4, width: int = 480) -> Path:
    """One image with a frame every `every` seconds, for a quick look at a whole video."""
    run(["-i", src, "-vf", "fps=1/%g,scale=%d:-1,tile=%dx%d:padding=6:margin=6:color=0x202024" %
         (every, width, cols, max(1, int(duration(src) / every / cols + 0.999))), "-frames:v", 1, out])
    return Path(out)
