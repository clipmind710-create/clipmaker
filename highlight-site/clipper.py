"""
clipper.py - clip banane ka asli kaam (server aur GitHub Actions dono yahi use karte hain)

make_clip(url, clip_len, vertical, captions, out_dir, name) ->
    {"video": "file.mp4", "srt": "file.srt" ya None, "note": "..."}
"""

import os
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlparse

import numpy as np
import yt_dlp
from yt_dlp.utils import download_range_func

FONT = os.environ.get("CAPTION_FONT", "Arial")            # caption ka font
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")   # tiny / base / small
COOKIES = os.environ.get("YT_COOKIES", "")                # cookies.txt ka path (optional)
MAX_AUDIO_MIN = int(os.environ.get("MAX_AUDIO_MINUTES", "90"))

# Sirf ye sites allowed (server ko galat use hone se bachane ke liye). Sab ke liye "*".
ALLOWED = [h.strip().lower()
           for h in os.environ.get("ALLOWED_HOSTS", "youtube.com,youtu.be,twitch.tv").split(",")
           if h.strip()]

_model = None


class UserError(Exception):
    """Aisi galti jo seedha user ko dikhani hai."""


def host_allowed(url):
    try:
        u = urlparse(url)
    except ValueError:
        return False
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    if "*" in ALLOWED:
        return True
    host = u.hostname.lower()
    return any(host == a or host.endswith("." + a) for a in ALLOWED)


def clean_error(text):
    text = re.sub(r"\x1b\[[0-9;]*m", "", str(text))
    lines = text.strip().splitlines()
    return lines[-1][:300] if lines else "Unknown error"


def friendly_error(exc):
    """Kisi bhi error ko user ke liye saaf message me badlo."""
    if isinstance(exc, UserError):
        return str(exc)
    msg = clean_error(exc)
    if "Sign in to confirm" in msg or "not a bot" in msg:
        return ("YouTube ne is server ko block kar diya hai. Thodi der baad try karo "
                "ya cookies set karo (README dekho).")
    return "Video process nahi ho paya: " + msg


def ydl_opts(**extra):
    opts = {"quiet": True, "noprogress": True, "noplaylist": True}
    if COOKIES and os.path.exists(COOKIES):
        opts["cookiefile"] = COOKIES
    opts.update(extra)
    return opts


def heatmap_start(info, clip_len):
    """YouTube ke 'Most replayed' graph se sabse zyada dekhe gaye point ke paas ka start."""
    heat = info.get("heatmap")
    if not heat:
        return None
    best = max(heat, key=lambda h: h["value"])
    center = (best["start_time"] + best["end_time"]) / 2
    duration = info.get("duration") or 0
    start = max(0, center - clip_len / 2)
    if duration:
        start = min(start, max(0, duration - clip_len))
    return start


def audio_start(url, clip_len):
    """Graph na ho to sabse tez awaaz wala hissa dhundo."""
    tmp = tempfile.mkdtemp()
    try:
        opts = ydl_opts(format="bestaudio/best",
                        outtmpl=os.path.join(tmp, "audio.%(ext)s"))
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        path = os.path.join(tmp, os.listdir(tmp)[0])

        rate = 8000
        cmd = ["ffmpeg", "-v", "quiet", "-i", path,
               "-f", "s16le", "-ac", "1", "-ar", str(rate), "-"]
        raw = subprocess.run(cmd, capture_output=True).stdout
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64)

        seconds = len(samples) // rate
        if seconds <= clip_len:
            return 0
        samples = samples[: seconds * rate].reshape(seconds, rate)
        loud = np.sqrt((samples ** 2).mean(axis=1))
        cs = np.concatenate([[0], np.cumsum(loud)])
        return int(np.argmax(cs[clip_len:] - cs[:-clip_len]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def make_vertical(name, out_dir):
    out = name.rsplit(".", 1)[0] + "_vertical.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", name,
         "-vf", "crop=ih*9/16:ih,scale=1080:1920", "-c:a", "copy", out],
        cwd=out_dir, check=True)
    return out


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def add_captions(name, out_dir):
    """Video ki awaaz sunke caption banao aur video par likh do."""
    global _model
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise UserError("Caption wala package (faster-whisper) install nahi hai.")

    if _model is None:
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    segments, info = _model.transcribe(os.path.join(out_dir, name), vad_filter=True)
    segments = list(segments)

    base = name.rsplit(".", 1)[0]
    srt_name = base + ".srt"
    count = 0
    with open(os.path.join(out_dir, srt_name), "w", encoding="utf-8") as f:
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            count += 1
            f.write(f"{count}\n{srt_time(seg.start)} --> {srt_time(seg.end)}\n{text}\n\n")

    if count == 0:
        os.remove(os.path.join(out_dir, srt_name))
        return name, None, None

    out = base + "_caption.mp4"
    style = f"FontName={FONT},FontSize=18,Outline=2,Shadow=0,Alignment=2,MarginV=30"
    # out_dir me chalate hain taaki Windows ke path (C:\...) se dikkat na aaye
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", name,
         "-vf", f"subtitles={srt_name}:force_style='{style}'",
         "-c:a", "copy", out],
        cwd=out_dir, check=True)
    return out, srt_name, info.language


def make_clip(url, clip_len, vertical, captions, out_dir, name, progress=None):
    progress = progress or (lambda msg: None)
    os.makedirs(out_dir, exist_ok=True)

    progress("Video ki jaankari la raha hoon...")
    with yt_dlp.YoutubeDL(ydl_opts()) as ydl:
        info = ydl.extract_info(url, download=False)

    if info.get("is_live"):
        raise UserError("Ye stream abhi live chal rahi hai. Live khatam hone ke baad "
                        "(jab recording ban jaye) dobara link do.")

    start = heatmap_start(info, clip_len)
    if start is None:
        if (info.get("duration") or 0) / 60 > MAX_AUDIO_MIN:
            raise UserError("Is lambe video me 'most replayed' graph nahi hai, aur "
                            f"{MAX_AUDIO_MIN} minute se lambe video ki awaaz jaanchna "
                            "abhi allowed nahi hai.")
        progress("Graph nahi mila, awaaz se sabse tez hissa dhundh raha hoon...")
        start = audio_start(url, clip_len)
        source = "sabse loud hissa"
    else:
        source = "most replayed graph"

    duration = info.get("duration") or (start + clip_len)
    end = min(duration, start + clip_len)

    progress(f"Hissa mil gaya ({int(start)}s se {int(end)}s). Clip kaat raha hoon...")
    opts = ydl_opts(
        format="bv*[height<=720]+ba/b[height<=720]/b",
        download_ranges=download_range_func(None, [(start, end)]),
        force_keyframes_at_cuts=True,
        merge_output_format="mp4",
        outtmpl=os.path.join(out_dir, name + ".%(ext)s"),
    )
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    video = name + ".mp4"
    if not os.path.exists(os.path.join(out_dir, video)):
        found = [f for f in os.listdir(out_dir) if f.startswith(name)]
        if not found:
            raise UserError("Clip ban nahi paayi. Dobara try karo.")
        video = found[0]

    if vertical:
        progress("Vertical (9:16) bana raha hoon...")
        video = make_vertical(video, out_dir)

    srt = None
    note = f"{int(start)}s se {int(end)}s tak ({source})"
    if captions:
        progress("Bolne wale shabd sun raha hoon, caption laga raha hoon...")
        video, srt, lang = add_captions(video, out_dir)
        if srt:
            note += f", caption bhasha: {lang}"
        else:
            note += ", is hisse me bolne wali awaaz nahi mili"

    return {"video": video, "srt": srt, "note": note}
