# ─────────────────────────────────────────
#  YT DOWNLOADER — server.py  (Flask backend)
#  Dev: Md. Mainul Islam (CODEX-M41NUL)
# ─────────────────────────────────────────

import os
import re
import time
import uuid
import threading
import subprocess
import json
import glob
from urllib.parse import urlparse

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from config import FLASK_HOST, FLASK_PORT, DOWNLOAD_DIR, HISTORY_FILE
from settings import get_setting

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_PATH = os.path.join(BASE_DIR, DOWNLOAD_DIR)
HISTORY_PATH = os.path.join(BASE_DIR, HISTORY_FILE)
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "public"), static_url_path="")
CORS(app)

# jobId -> { done, error, progress, file_path, file_paths, mode, title, is_playlist, job_dir }
JOBS = {}
JOBS_LOCK = threading.Lock()
HISTORY_LOCK = threading.Lock()

# ---------- rate limiting (per-IP) ----------
RATE_LOCK = threading.Lock()
RATE_BUCKET = {}  # ip -> [timestamps]


def is_rate_limited(ip: str) -> bool:
    window = get_setting("rate_limit_window_seconds", 60)
    max_requests = get_setting("rate_limit_max_requests", 6)
    now = time.time()
    with RATE_LOCK:
        bucket = RATE_BUCKET.setdefault(ip, [])
        while bucket and now - bucket[0] > window:
            bucket.pop(0)
        if len(bucket) >= max_requests:
            return True
        bucket.append(now)
        return False


# ---------- helpers ----------

def is_valid_youtube_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower().replace("www.", "")
        return host in ("youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com")
    except Exception:
        return False


def is_playlist_url(url: str) -> bool:
    return "list=" in url


def sanitize_filename(name: str, max_len: int = None) -> str:
    """Turn a YouTube title into a safe filename, shortening if too long."""
    if max_len is None:
        max_len = get_setting("max_filename_length", 60)
    if not name:
        return "untitled"
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > max_len:
        name = name[:max_len].rstrip() + "…"
    return name or "untitled"


def format_selector_for(mode: str, quality: str) -> str:
    if mode == "audio":
        return "bestaudio[ext=m4a]/bestaudio/best"
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


def cleanup_old_files(max_age_seconds=None):
    if max_age_seconds is None:
        max_age_seconds = get_setting("cleanup_max_age_seconds", 3600)
    now = time.time()
    for f in glob.glob(os.path.join(DOWNLOAD_PATH, "*")):
        try:
            if now - os.path.getmtime(f) > max_age_seconds:
                if os.path.isdir(f):
                    import shutil
                    shutil.rmtree(f, ignore_errors=True)
                else:
                    os.remove(f)
        except OSError:
            pass


def cleanup_loop():
    while True:
        time.sleep(900)
        cleanup_old_files()


def append_history(title, mode, quality, status):
    entry = {
        "title": title or "Untitled",
        "mode": mode,
        "quality": quality,
        "status": status,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with HISTORY_LOCK:
        try:
            history = []
            if os.path.exists(HISTORY_PATH):
                with open(HISTORY_PATH, "r", encoding="utf-8") as fh:
                    history = json.load(fh)
            history.append(entry)
            history = history[-200:]
            with open(HISTORY_PATH, "w", encoding="utf-8") as fh:
                json.dump(history, fh, indent=2)
        except Exception:
            pass


def read_history(limit=50):
    with HISTORY_LOCK:
        try:
            if not os.path.exists(HISTORY_PATH):
                return []
            with open(HISTORY_PATH, "r", encoding="utf-8") as fh:
                history = json.load(fh)
            return list(reversed(history))[:limit]
        except Exception:
            return []


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

    playlist = is_playlist_url(url)

    try:
        if playlist:
            result = subprocess.run(
                ["yt-dlp", "-J", "--flat-playlist", "--no-warnings", url],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return jsonify({"error": "Could not fetch playlist info. Check the URL and try again."}), 500

            data_json = json.loads(result.stdout)
            entries = data_json.get("entries", []) or []

            first_thumbnail = None
            if entries:
                first_id = entries[0].get("id")
                if first_id:
                    first_thumbnail = f"https://i.ytimg.com/vi/{first_id}/hqdefault.jpg"

            return jsonify({
                "isPlaylist": True,
                "title": data_json.get("title") or "Playlist",
                "uploader": data_json.get("uploader") or data_json.get("channel"),
                "videoCount": len(entries),
                "thumbnail": first_thumbnail,
                "entries": [{"title": e.get("title"), "id": e.get("id")} for e in entries[:100]],
            })

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
            "isPlaylist": False,
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


def build_download_args(url, mode, quality, output_template, is_playlist):
    args = ["yt-dlp", "--no-warnings"]
    args += ["--yes-playlist"] if is_playlist else ["--no-playlist"]
    args += ["-f", format_selector_for(mode, quality), "-o", output_template]

    if mode == "audio":
        # extract mp3 + embed the video thumbnail as album art + tag metadata
        args += ["--extract-audio", "--audio-format", "mp3", "--embed-thumbnail", "--add-metadata"]
    else:
        args += ["--merge-output-format", "mp4"]

    args.append(url)
    return args


_PROGRESS_RE = re.compile(
    r"([\d.]+)%"
    r"(?:.*?at\s+([\d.]+\s*[KMG]?i?B/s))?"
    r"(?:.*?ETA\s+([\d:]+|Unknown))?"
)


def run_yt_dlp(args, on_progress):
    """Run yt-dlp once, streaming progress (percent, speed, ETA) to on_progress(). Returns returncode."""
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, bufsize=1)
    for line in proc.stdout:
        if "%" in line:
            match = _PROGRESS_RE.search(line)
            if match:
                try:
                    pct = float(match.group(1))
                except (ValueError, TypeError):
                    continue
                speed = match.group(2).replace(" ", "") if match.group(2) else None
                eta = match.group(3) if match.group(3) and match.group(3) != "Unknown" else None
                on_progress(pct, speed, eta)
    proc.wait()
    return proc.returncode


@app.route("/api/download", methods=["POST"])
def download():
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if is_rate_limited(client_ip):
        return jsonify({"error": "Too many download requests. Please wait a moment and try again."}), 429

    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    quality = data.get("quality", get_setting("default_quality", "auto"))
    mode = data.get("mode", "video")  # "video" or "audio"
    title = data.get("title", "")
    total_videos = data.get("videoCount")  # optional hint from /api/info, for X/Y progress display

    if not url or not is_valid_youtube_url(url):
        return jsonify({"error": "Valid YouTube URL required"}), 400
    if quality not in ("auto", "1080", "720", "480", "360"):
        quality = "auto"
    if mode not in ("video", "audio"):
        mode = "video"
    try:
        total_videos = int(total_videos) if total_videos else None
    except (ValueError, TypeError):
        total_videos = None

    playlist = is_playlist_url(url)
    job_id = uuid.uuid4().hex[:16]
    safe_title = sanitize_filename(title) if title else None
    name_part = safe_title if safe_title else "%(title).60s"

    job_dir = None
    if playlist:
        job_dir = os.path.join(DOWNLOAD_PATH, job_id)
        os.makedirs(job_dir, exist_ok=True)
        output_template = os.path.join(job_dir, "%(playlist_index)03d - %(title).60s.%(ext)s")
    else:
        output_template = os.path.join(DOWNLOAD_PATH, f"{job_id}__{name_part}.%(ext)s")

    with JOBS_LOCK:
        JOBS[job_id] = {
            "done": False, "error": None, "progress": 0,
            "file_path": None, "file_paths": None,
            "mode": mode, "title": title,
            "is_playlist": playlist, "job_dir": job_dir,
            "total_videos": total_videos if playlist else None,
            "speed": None, "eta": None,
        }

    def set_progress(pct, speed=None, eta=None):
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if job:
                job["progress"] = pct
                if speed:
                    job["speed"] = speed
                if eta:
                    job["eta"] = eta

    def run_download():
        label = f"[{mode.upper()}]{' [PLAYLIST]' if playlist else ''} {title or url}"
        print(f"\n  >>> Download started: {label}")

        args = build_download_args(url, mode, quality, output_template, playlist)

        max_retries = get_setting("max_retries", 2)
        attempt = 0
        returncode = 1
        while attempt <= max_retries:
            attempt += 1
            if attempt > 1:
                print(f"  >>> Retry {attempt - 1}/{max_retries}: {label}")
            try:
                returncode = run_yt_dlp(args, set_progress)
            except Exception as e:
                print(f"  >>> Attempt {attempt} error: {label} — {e}")
                returncode = 1
            if returncode == 0:
                break
            time.sleep(1.5)

        print()

        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if not job:
                return
            if returncode != 0:
                job["error"] = "Download failed after retries. The video may be restricted or unavailable."
                job["done"] = True
                print(f"  >>> Failed: {label}")
                append_history(title, mode, quality, "failed")
                return

        if playlist:
            matches = sorted(glob.glob(os.path.join(job_dir, "*")))
            if not matches:
                with JOBS_LOCK:
                    job["error"] = "Download completed but no files were found."
                    job["done"] = True
                print(f"  >>> Failed (no files found): {label}")
                append_history(title, mode, quality, "failed")
                return
            with JOBS_LOCK:
                job["file_paths"] = matches
                job["progress"] = 100
                job["done"] = True
            print(f"  >>> Done: {label} ({len(matches)} files)")
            append_history(title or f"Playlist ({len(matches)} items)", mode, quality, "done")
        else:
            matches = glob.glob(os.path.join(DOWNLOAD_PATH, f"{job_id}__*"))
            if not matches:
                with JOBS_LOCK:
                    job["error"] = "Download completed but file was not found."
                    job["done"] = True
                print(f"  >>> Failed (file not found): {label}")
                append_history(title, mode, quality, "failed")
                return
            with JOBS_LOCK:
                job["file_path"] = matches[0]
                job["progress"] = 100
                job["done"] = True
            print(f"  >>> Done: {label}")
            append_history(title, mode, quality, "done")

    threading.Thread(target=run_download, daemon=True).start()
    return jsonify({"jobId": job_id, "isPlaylist": playlist})


@app.route("/api/progress/<job_id>")
def progress(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        is_playlist = job.get("is_playlist", False)
        job_dir = job.get("job_dir")
        total_videos = job.get("total_videos")
        mode = job.get("mode")
        done = job["done"]
        error = job["error"]
        progress_pct = job["progress"]
        file_paths = job.get("file_paths")
        file_path = job.get("file_path")
        speed = job.get("speed")
        eta = job.get("eta")

    # count fully-finished files live, even mid-download, so the UI can show "X / Y".
    # Only count the FINAL output extension — yt-dlp/ffmpeg create intermediate
    # files while merging/converting/embedding (e.g. raw .m4a before mp3 conversion,
    # temp .jpg/.webp thumbnails before embedding), and counting those too makes
    # the number flicker up and down instead of only ever increasing.
    if is_playlist and job_dir and os.path.isdir(job_dir):
        final_ext = ".mp3" if mode == "audio" else ".mp4"
        finished = glob.glob(os.path.join(job_dir, f"*{final_ext}"))
        live_file_count = len(finished)
        # never let the displayed count go backwards (extra safety against any
        # transient filesystem state during merge/convert/embed steps)
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if job is not None:
                prev_max = job.get("max_file_count", 0)
                if live_file_count < prev_max:
                    live_file_count = prev_max
                else:
                    job["max_file_count"] = live_file_count
    else:
        live_file_count = len(file_paths) if file_paths else (1 if file_path else 0)

    return jsonify({
        "done": done,
        "error": error,
        "progress": progress_pct,
        "ready": done and not error,
        "isPlaylist": is_playlist,
        "fileCount": live_file_count,
        "totalVideos": total_videos,
        "speed": speed,
        "eta": eta,
    })


@app.route("/api/stats")
def stats():
    with JOBS_LOCK:
        active = [j for j in JOBS.values() if not j["done"]]
        playlist_active = [j for j in active if j.get("is_playlist")]
        return jsonify({
            "activeJobs": len(active),
            "activePlaylistJobs": len(playlist_active),
            "totalJobs": len(JOBS),
        })


@app.route("/api/history")
def history():
    return jsonify({"history": read_history()})


@app.route("/api/file/<job_id>")
def get_file(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job or not job["done"] or job["error"]:
            return jsonify({"error": "File not ready"}), 404
        mode = job["mode"]
        is_playlist = job.get("is_playlist", False)

        if is_playlist:
            job_dir = job["job_dir"]
            if not job_dir or not os.path.isdir(job_dir):
                return jsonify({"error": "File not found"}), 404
            zip_base = os.path.join(DOWNLOAD_PATH, f"{job_id}_playlist")
            zip_path = zip_base + ".zip"
            if not os.path.exists(zip_path):
                import shutil
                shutil.make_archive(zip_base, "zip", job_dir)
            file_path = zip_path
            download_name = "playlist_audio.zip" if mode == "audio" else "playlist_video.zip"
        else:
            file_path = job["file_path"]
            if not file_path:
                return jsonify({"error": "File not found"}), 404
            ext = "mp3" if mode == "audio" else "mp4"
            base_name = os.path.basename(file_path)
            display_name = base_name.split("__", 1)[-1] if "__" in base_name else base_name
            download_name = display_name if display_name.lower().endswith(f".{ext}") else f"{display_name}.{ext}"

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    response = send_file(file_path, as_attachment=True, download_name=download_name)

    @response.call_on_close
    def cleanup():
        try:
            if is_playlist:
                import shutil
                shutil.rmtree(job["job_dir"], ignore_errors=True)
                if os.path.exists(file_path):
                    os.remove(file_path)
            else:
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
