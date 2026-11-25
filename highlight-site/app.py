"""
Highlight Clip Maker - server (backend)

    POST /api/clip      -> kaam shuru karo, job_id milega
    GET  /api/job/<id>  -> kaam ka status (progress / done / error)
    GET  /clips/<file>  -> taiyar video / caption file
    GET  /              -> website (docs/ folder)

Local chalane ke liye:
    pip install -r requirements.txt
    python app.py          ->  http://localhost:5000
"""

import os
import shutil
import threading
import time
import uuid

from flask import Flask, jsonify, request, send_from_directory

import clipper

BASE = os.path.dirname(os.path.abspath(__file__))
CLIPS = os.path.join(BASE, "clips")
os.makedirs(CLIPS, exist_ok=True)

MAX_ACTIVE = int(os.environ.get("MAX_ACTIVE_JOBS", "2"))    # ek saath kitne kaam
MAX_CLIP = int(os.environ.get("MAX_CLIP_SECONDS", "120"))
KEEP_SECONDS = 60 * 60                                       # 1 ghante baad files delete
# GitHub Pages ka link yahan daalo (jaise https://naam.github.io). "*" = sab allowed.
CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

app = Flask(__name__, static_folder="docs", static_url_path="")

JOBS = {}
JOBS_LOCK = threading.Lock()


@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = CORS_ORIGIN
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


def update(job_id, **kw):
    with JOBS_LOCK:
        JOBS[job_id].update(kw)


def active_jobs():
    with JOBS_LOCK:
        return sum(1 for j in JOBS.values() if j["status"] in ("queued", "working"))


def run_job(job_id, url, clip_len, vertical, captions):
    try:
        update(job_id, status="working")
        result = clipper.make_clip(
            url, clip_len, vertical, captions, CLIPS, f"highlight_{job_id}",
            progress=lambda m: update(job_id, message=m))
        update(job_id, status="done", message="Clip taiyar hai!", note=result["note"],
               video="/clips/" + result["video"],
               srt=("/clips/" + result["srt"]) if result["srt"] else None)
    except Exception as e:  # noqa: BLE001
        update(job_id, status="error", message=clipper.friendly_error(e))


def cleaner():
    """Purani files aur jobs hata do, taaki disk na bhare."""
    while True:
        time.sleep(600)
        now = time.time()
        for f in os.listdir(CLIPS):
            p = os.path.join(CLIPS, f)
            try:
                if now - os.path.getmtime(p) > KEEP_SECONDS:
                    os.remove(p)
            except OSError:
                pass
        with JOBS_LOCK:
            for k in [k for k, j in JOBS.items() if now - j["created"] > KEEP_SECONDS]:
                del JOBS[k]


threading.Thread(target=cleaner, daemon=True).start()


@app.route("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/clip", methods=["POST"])
def api_clip():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    try:
        clip_len = int(data.get("len", 45))
    except (TypeError, ValueError):
        clip_len = 45
    clip_len = max(10, min(MAX_CLIP, clip_len))
    vertical = bool(data.get("vertical"))
    captions = bool(data.get("captions"))

    if not url:
        return jsonify(error="Pehle video ka link daalo."), 400
    if not clipper.host_allowed(url):
        return jsonify(error="Abhi sirf ye sites chalti hain: " + ", ".join(clipper.ALLOWED)), 400
    if shutil.which("ffmpeg") is None:
        return jsonify(error="Server par ffmpeg install nahi hai."), 500
    if active_jobs() >= MAX_ACTIVE:
        return jsonify(error="Abhi server vyast hai. Thodi der baad try karo."), 429

    job_id = uuid.uuid4().hex[:12]
    with JOBS_LOCK:
        JOBS[job_id] = {"status": "queued", "message": "Kaam shuru ho raha hai...",
                        "created": time.time()}
    threading.Thread(target=run_job,
                     args=(job_id, url, clip_len, vertical, captions),
                     daemon=True).start()
    return jsonify(job_id=job_id)


@app.route("/api/job/<job_id>")
def api_job(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify(error="Ye kaam nahi mila (shayad purana ho gaya)."), 404
        return jsonify({k: v for k, v in job.items() if k != "created"})


@app.route("/clips/<path:filename>")
def clips(filename):
    return send_from_directory(CLIPS, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
