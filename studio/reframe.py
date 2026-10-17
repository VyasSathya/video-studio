"""Reframe a landscape video for another aspect (9:16 by default).

Each shot (ffmpeg scene detection) is handled on its own: if a face shows up in enough sampled frames, the crop
sits on the median face position for that shot; if not (B-roll, slides, wide shots), the whole frame is fitted
over a blurred, darkened copy of itself. No tracking jitter: one crop per shot, the way an editor would do it.
"""
import re
import subprocess

from . import media


def shots(src, threshold=0.3, min_len=0.6):
    """Shot boundaries in seconds, [0, ..., duration]."""
    p = subprocess.run([media.ffmpeg_bin(), "-hide_banner", "-nostats", "-i", str(src), "-an", "-vf",
                        "scale=320:-2,select='gt(scene,%g)',showinfo" % threshold, "-f", "null", "-"],
                       capture_output=True, text=True)
    cuts = [float(m.group(1)) for m in re.finditer(r"pts_time:([\d.]+)", p.stderr)]
    dur = media.duration(src)
    out = [0.0]
    for c in cuts:
        if c - out[-1] >= min_len and dur - c >= min_len:
            out.append(c)
    out.append(dur)
    return out


def faces(src, times):
    """{t: (cx, cy, w) of the largest face as fractions of the frame, or None}, using OpenCV's stock cascade."""
    import cv2
    det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(str(src))
    out = {}
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            out[t] = None
            continue
        h, w = frame.shape[:2]
        small = cv2.resize(frame, (640, int(640 * h / w)))
        g = cv2.equalizeHist(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
        found = det.detectMultiScale(g, scaleFactor=1.1, minNeighbors=6, minSize=(36, 36))
        if len(found) == 0:
            out[t] = None
            continue
        x, y, fw, fh = max(found, key=lambda f: f[2] * f[3])
        sw = small.shape[1]
        sh = small.shape[0]
        out[t] = ((x + fw / 2) / sw, (y + fh / 2) / sh, fw / sw)
    cap.release()
    return out


def plan(src, aspect=(9, 16), step=0.5, min_face_share=0.4):
    """[{"start","end","mode": "crop"|"fit","cx"}] per shot."""
    b = shots(src)
    out = []
    for s, e in zip(b, b[1:]):
        ts = [s + 0.15 + k * step for k in range(max(1, int((e - s - 0.3) / step) + 1)) if s + 0.15 + k * step < e]
        f = faces(src, ts)
        hits = sorted(v[0] for v in f.values() if v)
        if hits and len(hits) >= min_face_share * len(ts):
            out.append({"start": round(s, 3), "end": round(e, 3), "mode": "crop", "cx": round(float(hits[len(hits) // 2]), 4)})
        else:
            out.append({"start": round(s, 3), "end": round(e, 3), "mode": "fit"})
    return out


def render(src, shot_plan, out, size=(1080, 1920), fps=30, crf=18):
    """Apply a shot plan in one ffmpeg pass; audio is copied through untouched."""
    W, H = size
    sw, sh = probe_size(src)
    crop_w = int(sh * W / H) // 2 * 2
    parts, labels = [], []
    for i, s in enumerate(shot_plan):
        trim = "[0:v]trim=start=%.3f:end=%.3f,setpts=PTS-STARTPTS" % (s["start"], s["end"])
        if s["mode"] == "crop" and crop_w <= sw:
            x = int(min(max(s["cx"] * sw - crop_w / 2, 0), sw - crop_w))
            parts.append("%s,crop=%d:%d:%d:0,scale=%d:%d:flags=lanczos,setsar=1[v%d]" % (trim, crop_w, sh, x, W, H, i))
        else:
            q = (W // 4, H // 4)
            parts.append("%s,split[f%d][g%d];[g%d]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
                         "boxblur=10:2,eq=brightness=-0.12,scale=%d:%d[bg%d];[f%d]scale=%d:-2:flags=lanczos[fg%d];"
                         "[bg%d][fg%d]overlay=(W-w)/2:(H-h)/2,setsar=1[v%d]"
                         % ((trim, i, i, i) + q + q + (W, H, i, i, W, i, i, i, i)))
        labels.append("[v%d]" % i)
    graph = ";".join(parts) + ";" + "".join(labels) + "concat=n=%d:v=1:a=0,fps=%d[v]" % (len(labels), fps)
    media.run(["-i", src, "-filter_complex", graph, "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", crf,
               "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", out])
    return out


def probe_size(src):
    out = subprocess.run([media.ffprobe_bin(), "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", str(src)], capture_output=True, text=True,
                         check=True).stdout.strip()
    w, h = out.split(",")[:2]
    return int(w), int(h)
