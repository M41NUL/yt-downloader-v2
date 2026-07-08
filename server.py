# ─────────────────────────────────────────
#  YT DOWNLOADER — server.py  (Flask backend)
#  Dev: Md. Mainul Islam (CODEX-M41NUL)
# ─────────────────────────────────────────

import os
import time
import uuid
import threading
import subprocess
import json
import glob
from urllib.parse import urlparse

from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS

from config import FLASK_HOST, FLASK_PORT, DOWNLOAD_DIR

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_PATH = os.path.join(BASE_DIR, DOWNLOAD_DIR)
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "public"), static_url_path="")
CORS(app)

# jobId -> { done, error, progress, file_path }
JOBS = {}
JOBS_LOCK = threading.Lock()


# ---------- helpers ----------

def is_valid_youtube_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower().replace("www.", "")
        return host in ("youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com")
    except Exception:
        return False


def format_selector_for(quality: str) -> str:
    if quality == "auto":
        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    h = int(quality)
    return (f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]"
            f"/best[height<={h}][ext=mp4]/best[height<={h}]")


def seconds_to_hms(seconds):
    if seconds is None:
        return None
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"


def cleanup_old_files(max_age_seconds=3600):
    now = time.time()
    for f in glob.glob(os.path.join(DOWNLOAD_PATH, "*")):
        try:
            if now - os.path.getmtime(f) > max_age_seconds:
                os.remove(f)
        except OSError:
            pass


def cleanup_loop():
    while True:
        time.sleep(900)
        cleanup_old_files()


# ---------- routes ----------

@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/health")
def health():
    return jsonify({"ok": True})


@app.route("/api/info", methods=["POST"])
def info():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()

    if not url or not is_valid_youtube_url(url):
        return jsonify({"error": "Valid YouTube URL required"}), 400

    try:
        result = subprocess.run(
            ["yt-dlp", "-J", "--no-playlist", "--no-warnings", url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return jsonify({"error": "Could not fetch video info. Check the URL and try again."}), 500

        video = json.loads(result.stdout)
        heights = set()
        for f in video.get("formats", []):
            if f.get("height"):
                heights.add(f["height"])

        available = {}
        for h in (1080, 720, 480, 360):
            available[str(h)] = any(height >= h for height in heights)

        return jsonify({
            "title": video.get("title"),
            "thumbnail": video.get("thumbnail"),
            "duration": seconds_to_hms(video.get("duration")),
            "uploader": video.get("uploader") or video.get("channel"),
            "availableQualities": available,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Request timed out. Try again."}), 504
    except Exception:
        return jsonify({"error": "Could not fetch video info. Check the URL and try again."}), 500


@app.route("/api/download", methods=["POST"])
def download():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    quality = data.get("quality", "auto")

    if not url or not is_valid_youtube_url(url):
        return jsonify({"error": "Valid YouTube URL required"}), 400
    if quality not in ("auto", "1080", "720", "480", "360"):
        quality = "auto"

    job_id = uuid.uuid4().hex[:16]
    output_template = os.path.join(DOWNLOAD_PATH, f"{job_id}.%(ext)s")

    with JOBS_LOCK:
        JOBS[job_id] = {"done": False, "error": None, "progress": 0, "file_path": None}

    def run_download():
        args = [
            "yt-dlp",
            "--no-playlist", "--no-warnings",
            "-f", format_selector_for(quality),
            "--merge-output-format", "mp4",
            "-o", output_template,
            url,
        ]
        try:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, bufsize=1)
            for line in proc.stdout:
                with JOBS_LOCK:
                    job = JOBS.get(job_id)
                if not job:
                    continue
                if "%" in line:
                    try:
                        pct_str = line.split("%")[0].strip().split()[-1]
                        pct = float(pct_str)
                        with JOBS_LOCK:
                            job["progress"] = pct
                    except (ValueError, IndexError):
                        pass
            proc.wait()

            with JOBS_LOCK:
                job = JOBS.get(job_id)
                if not job:
                    return
                if proc.returncode != 0:
                    job["error"] = "Download failed. The video may be restricted or unavailable."
                    job["done"] = True
                    return

            matches = glob.glob(os.path.join(DOWNLOAD_PATH, f"{job_id}.*"))
            if not matches:
                with JOBS_LOCK:
                    job["error"] = "Download completed but file was not found."
                    job["done"] = True
                return

            with JOBS_LOCK:
                job["file_path"] = matches[0]
                job["progress"] = 100
                job["done"] = True

        except Exception as e:
            with JOBS_LOCK:
                job = JOBS.get(job_id)
                if job:
                    job["error"] = f"Download failed: {e}"
                    job["done"] = True

    threading.Thread(target=run_download, daemon=True).start()
    return jsonify({"jobId": job_id})


@app.route("/api/progress/<job_id>")
def progress(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        return jsonify({
            "done": job["done"],
            "error": job["error"],
            "progress": job["progress"],
            "ready": job["done"] and not job["error"],
        })


@app.route("/api/file/<job_id>")
def get_file(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job or not job["done"] or job["error"] or not job["file_path"]:
            return jsonify({"error": "File not ready"}), 404
        file_path = job["file_path"]

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    response = send_file(file_path, as_attachment=True, download_name="video.mp4")

    @response.call_on_close
    def cleanup():
        try:
            os.remove(file_path)
        except OSError:
            pass
        with JOBS_LOCK:
            JOBS.pop(job_id, None)

    return response


def start_server():
    """Called by main.py when user selects 'Start' from the menu."""
    threading.Thread(target=cleanup_loop, daemon=True).start()
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    start_server()
