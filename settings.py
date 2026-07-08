# ─────────────────────────────────────────
#  YT DOWNLOADER — settings.py
#  Persisted, user-editable runtime settings
#  Dev: Md. Mainul Islam (CODEX-M41NUL)
# ─────────────────────────────────────────

import os
import json
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

_LOCK = threading.Lock()

DEFAULTS = {
    "default_quality": "auto",        # auto, 1080, 720, 480, 360
    "max_filename_length": 60,        # auto-shorten long YouTube titles past this length
    "max_retries": 2,                 # extra retry attempts on failed download
    "rate_limit_max_requests": 6,     # max /api/download calls per IP...
    "rate_limit_window_seconds": 60,  # ...per this many seconds
    "cleanup_max_age_seconds": 3600,  # auto-delete leftover files older than this
}

# Human-readable descriptions shown in the Settings menu
DESCRIPTIONS = {
    "default_quality": "Default video quality (auto/1080/720/480/360)",
    "max_filename_length": "Max characters before a title is auto-shortened",
    "max_retries": "Extra retry attempts if a download fails",
    "rate_limit_max_requests": "Max download requests allowed per IP",
    "rate_limit_window_seconds": "Time window (seconds) for the rate limit",
    "cleanup_max_age_seconds": "Auto-delete leftover files older than N seconds",
}

VALID_QUALITIES = ("auto", "1080", "720", "480", "360")


def _load():
    with _LOCK:
        if not os.path.exists(SETTINGS_FILE):
            return dict(DEFAULTS)
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            merged = dict(DEFAULTS)
            merged.update({k: v for k, v in data.items() if k in DEFAULTS})
            return merged
        except Exception:
            return dict(DEFAULTS)


def _save(data):
    with _LOCK:
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            return True
        except OSError:
            return False


def get_all_settings():
    return _load()


def get_setting(key, fallback=None):
    data = _load()
    return data.get(key, fallback if fallback is not None else DEFAULTS.get(key))


def set_setting(key, value):
    if key not in DEFAULTS:
        return False, f"Unknown setting: {key}"

    # basic type-aware validation per key
    try:
        if key == "default_quality":
            value = str(value).strip().lower()
            if value not in VALID_QUALITIES:
                return False, f"Must be one of {', '.join(VALID_QUALITIES)}"
        elif key in ("max_filename_length", "max_retries",
                     "rate_limit_max_requests", "rate_limit_window_seconds",
                     "cleanup_max_age_seconds"):
            value = int(value)
            if value < 0:
                return False, "Must be a non-negative number"
            if key == "max_filename_length" and value < 10:
                return False, "Must be at least 10"
            if key == "max_retries" and value > 10:
                return False, "Must be 10 or fewer"
    except (ValueError, TypeError):
        return False, "Invalid value type"

    data = _load()
    data[key] = value
    ok = _save(data)
    return ok, None if ok else "Could not write settings file"


def reset_defaults():
    return _save(dict(DEFAULTS))
