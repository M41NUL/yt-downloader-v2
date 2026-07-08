# ─────────────────────────────────────────
#  YT DOWNLOADER — main.py
#  Dev: Md. Mainul Islam (CODEX-M41NUL)
# ─────────────────────────────────────────

import os
import sys
import time
import json
import glob
import socket
import signal
import subprocess

from banner import show_banner
from utils import R, G, Y, C, O, W, BLD, DIM, RST, clear_screen, Spinner
from config import FLASK_HOST, FLASK_PORT, HISTORY_FILE, DOWNLOAD_DIR, VERSION
from setup import ensure_all_dependencies
import settings as settings_mod

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_PATH = os.path.join(BASE_DIR, DOWNLOAD_DIR)

flask_proc = None
local_url = None


# ---------- helpers ----------

def get_lan_ip():
    """Best-effort LAN IP detection (works on Termux without extra packages)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def box_line(text, width, color=W):
    """Pad a line to fit inside a fixed-width box, truncating if too long."""
    if len(text) > width - 2:
        text = text[: width - 5] + "..."
    pad = width - 2 - len(text)
    return f"  {O}{BLD}|{RST} {color}{text}{RST}{' ' * max(pad - 1, 0)}{O}{BLD}|{RST}"


def box_border(width, corner_l="+", corner_r="+"):
    return f"  {O}{BLD}{corner_l}{'-' * width}{corner_r}{RST}"


def get_yt_dlp_version():
    try:
        result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def print_qr(url):
    """Best-effort ASCII QR code so the link can be scanned from another device.
    Uses half-block characters (2 QR rows per terminal line) to keep it compact."""
    try:
        import qrcode
        spinner = Spinner("Generating QR code...").start()
        qr = qrcode.QRCode(border=1, box_size=1)
        qr.add_data(url)
        qr.make(fit=True)
        matrix = qr.get_matrix()
        spinner.stop()
        print()
        for y in range(0, len(matrix), 2):
            top_row = matrix[y]
            bottom_row = matrix[y + 1] if y + 1 < len(matrix) else [False] * len(top_row)
            line = ""
            for top, bottom in zip(top_row, bottom_row):
                if top and bottom:
                    line += "█"
                elif top and not bottom:
                    line += "▀"
                elif not top and bottom:
                    line += "▄"
                else:
                    line += " "
            print(f"  {W}{line}{RST}")
        print()
    except ImportError:
        print(f"  {DIM}{W}(Install 'qrcode' for a scannable QR code: pip install qrcode --break-system-packages){RST}")
    except Exception:
        pass  # QR is a nice-to-have; never block the app on it


def count_downloads_left():
    """Count leftover files/folders sitting in downloads/ (not yet cleaned up)."""
    if not os.path.isdir(DOWNLOAD_PATH):
        return 0
    return len(glob.glob(os.path.join(DOWNLOAD_PATH, "*")))


def get_live_stats():
    """Poll the running Flask server for active job stats. Returns None if not running/unreachable."""
    if flask_proc is None or local_url is None:
        return None
    try:
        import urllib.request
        with urllib.request.urlopen(f"{local_url}/api/stats", timeout=2) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


# ---------- process control ----------

def start_tools():
    global flask_proc, local_url

    if flask_proc is not None:
        print(f"\n  {Y}Already running.{RST}")
        input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")
        return

    print()
    spinner = Spinner("Starting Flask backend...").start()
    flask_proc = subprocess.Popen(
        [sys.executable, os.path.join(BASE_DIR, "server.py")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)

    if flask_proc.poll() is not None:
        spinner.stop("Flask failed to start. Run 'python server.py' directly to see the error.", success=False)
        input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")
        flask_proc = None
        return

    spinner.stop("Flask backend is running.")

    lan_ip = get_lan_ip()
    local_url = f"http://{lan_ip}:{FLASK_PORT}"

    width = 56
    print(f"\n{box_border(width)}")
    print(box_line("YOUR LINK IS READY", width, f"{Y}{BLD}"))
    print(box_line(local_url, width, f"{G}{BLD}"))
    print(box_border(width))
    print(f"\n  {DIM}{W}Open that link on any device connected to the SAME WiFi.{RST}")

    print_qr(local_url)

    input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")


def stop_tools(pause=True):
    global flask_proc, local_url

    if flask_proc is not None:
        spinner = Spinner("Stopping server...").start()
        try:
            flask_proc.terminate()
            flask_proc.wait(timeout=5)
        except Exception:
            try:
                flask_proc.kill()
            except Exception:
                pass
        flask_proc = None
        local_url = None
        spinner.stop("Stopped. Server closed.")
    else:
        print(f"\n  {Y}Nothing is running.{RST}")
    if pause:
        input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")


def show_history():
    history_path = os.path.join(BASE_DIR, HISTORY_FILE)
    print()
    if not os.path.exists(history_path):
        print(f"  {Y}No downloads yet.{RST}")
        input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")
        return

    try:
        with open(history_path, "r", encoding="utf-8") as fh:
            history = json.load(fh)
    except Exception:
        print(f"  {R}Could not read history file.{RST}")
        input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")
        return

    if not history:
        print(f"  {Y}No downloads yet.{RST}")
        input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")
        return

    print(f"  {Y}{BLD}Filter history{RST}")
    print(f"  {O}[1]{RST} {W}All")
    print(f"  {O}[2]{RST} {W}Video only")
    print(f"  {O}[3]{RST} {W}Audio only")
    print(f"  {O}[4]{RST} {W}Failed only")
    print(f"  {O}[5]{RST} {W}Successful only")
    choice = input(f"\n  {O}{BLD}> {RST}").strip()

    spinner = Spinner("Loading history...").start()

    def matches(entry):
        mode = entry.get("mode", "video")
        status = entry.get("status", "done")
        if choice == "2":
            return mode == "video"
        if choice == "3":
            return mode == "audio"
        if choice == "4":
            return status == "failed"
        if choice == "5":
            return status == "done"
        return True

    filtered = [e for e in reversed(history) if matches(e)]
    spinner.stop()

    print()
    if not filtered:
        print(f"  {Y}No matching entries.{RST}")
    else:
        print(f"  {Y}{BLD}Recent downloads (latest first) — {len(filtered)} shown{RST}\n")
        for entry in filtered[:25]:
            status_color = G if entry.get("status") == "done" else R
            status_text = "OK" if entry.get("status") == "done" else "FAILED"
            mode = entry.get("mode", "video").upper()
            quality = entry.get("quality", "auto")
            title = entry.get("title") or "Untitled"
            if len(title) > 40:
                title = title[:37] + "..."
            when = entry.get("time", "")
            print(f"  {status_color}[{status_text}]{RST} {DIM}{when}{RST}  {C}{mode}{RST}/{quality}  {W}{title}{RST}")

    print()
    input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")


def clear_downloads():
    print()
    if not os.path.isdir(DOWNLOAD_PATH):
        print(f"  {Y}Downloads folder is already empty.{RST}")
        input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")
        return

    items = glob.glob(os.path.join(DOWNLOAD_PATH, "*"))
    if not items:
        print(f"  {Y}Downloads folder is already empty.{RST}")
        input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")
        return

    print(f"  {Y}{len(items)} item(s) found in downloads/.{RST}")
    confirm = input(f"  {R}Delete all of them? This cannot be undone. (y/N): {RST}").strip().lower()
    if confirm != "y":
        print(f"  {DIM}{W}Cancelled.{RST}")
        input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")
        return

    removed, failed = 0, 0
    spinner = Spinner(f"Removing {len(items)} item(s)...").start()
    for item in items:
        try:
            if os.path.isdir(item):
                import shutil
                shutil.rmtree(item, ignore_errors=True)
            else:
                os.remove(item)
            removed += 1
        except OSError:
            failed += 1

    if failed:
        spinner.stop(f"Removed {removed} item(s), {failed} failed.", success=False)
    else:
        spinner.stop(f"Removed {removed} item(s).")
    input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")


def check_ytdlp_update():
    print()
    current = get_yt_dlp_version()
    if current:
        print(f"  {DIM}{W}Current version: {current}{RST}")
    spinner = Spinner("Checking yt-dlp for updates...").start()
    try:
        result = subprocess.run(
            ["pip", "install", "-U", "--break-system-packages", "yt-dlp"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=90
        )
        if result.returncode == 0:
            new_version = get_yt_dlp_version()
            if "Successfully installed" in result.stdout:
                spinner.stop(f"yt-dlp updated. Now on {new_version}")
            else:
                spinner.stop(f"yt-dlp is already up to date. ({new_version})")
        else:
            spinner.stop("Update check failed (offline or mirror issue).", success=False)
            print(f"  {DIM}{W}{result.stdout[-300:]}{RST}")
    except subprocess.TimeoutExpired:
        spinner.stop("Update check timed out.", success=False)
    except Exception as e:
        spinner.stop(f"Update check failed: {e}", success=False)
    input(f"\n  {DIM}{W}Press Enter to go back to menu...{RST}")


# ---------- settings menu ----------

def show_settings():
    while True:
        clear_screen()
        show_banner()
        current = settings_mod.get_all_settings()
        print(f"  {Y}{BLD}Settings{RST}\n")
        keys = list(settings_mod.DEFAULTS.keys())
        for i, key in enumerate(keys, start=1):
            desc = settings_mod.DESCRIPTIONS.get(key, key)
            print(f"  {O}{BLD}[{i}]{RST} {W}{key}{RST} = {G}{current[key]}{RST}")
            print(f"      {DIM}{W}{desc}{RST}")
        print(f"\n  {O}{BLD}[r]{RST} {W}Reset all to defaults")
        print(f"  {O}{BLD}[0]{RST} {W}Back to main menu\n")

        choice = input(f"  {O}{BLD}> {RST}").strip().lower()
        if choice == "0":
            return
        if choice == "r":
            confirm = input(f"  {R}Reset ALL settings to defaults? (y/N): {RST}").strip().lower()
            if confirm == "y":
                settings_mod.reset_defaults()
                print(f"  {G}Settings reset.{RST}")
                input(f"  {DIM}{W}Press Enter to continue...{RST}")
            continue

        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(keys):
                raise ValueError
        except ValueError:
            print(f"  {R}Invalid option.{RST}")
            input(f"  {DIM}{W}Press Enter to continue...{RST}")
            continue

        key = keys[idx]
        new_value = input(f"  {W}New value for {C}{key}{RST} (current: {current[key]}): {RST}").strip()
        if not new_value:
            continue
        ok, err = settings_mod.set_setting(key, new_value)
        if ok:
            print(f"  {G}Updated {key} -> {new_value}{RST}")
        else:
            print(f"  {R}Could not update: {err}{RST}")
        input(f"  {DIM}{W}Press Enter to continue...{RST}")


def exit_app():
    leftover = count_downloads_left()
    if leftover > 0:
        print(f"\n  {Y}Note: {leftover} item(s) still in downloads/ (not yet cleaned up).{RST}")
    stop_tools(pause=False)
    print(f"  {O}{BLD}Bye - CODEX-M41NUL{RST}\n")
    sys.exit(0)


# ---------- menu ----------

def show_menu():
    clear_screen()
    show_banner()
    status = f"{G}RUNNING{RST}" if flask_proc is not None else f"{DIM}{W}STOPPED{RST}"
    ytdlp_version = get_yt_dlp_version()
    status_line = f"  {W}Status: {status}"
    if ytdlp_version:
        status_line += f"  {DIM}{W}|{RST}  {DIM}{W}yt-dlp {ytdlp_version}{RST}"
    print(status_line)

    if local_url:
        print(f"  {W}Link:   {C}{local_url}{RST}")

    if flask_proc is not None:
        stats = get_live_stats()
        if stats:
            active = stats.get("activeJobs", 0)
            playlists = stats.get("activePlaylistJobs", 0)
            if active > 0:
                extra = f" ({playlists} playlist{'s' if playlists != 1 else ''})" if playlists else ""
                print(f"  {C}Active downloads: {active}{extra}{RST}")

    leftover = count_downloads_left()
    if leftover > 0:
        print(f"\n  {Y}Files pending cleanup: {leftover}{RST}")

    print()
    print(f"  {Y}{BLD}[1]{RST} {W}Start YT Downloader")
    print(f"  {Y}{BLD}[2]{RST} {W}Stop")
    print(f"  {Y}{BLD}[3]{RST} {W}History")
    print(f"  {Y}{BLD}[4]{RST} {W}Settings")
    print(f"  {Y}{BLD}[5]{RST} {W}Clear Downloads")
    print(f"  {Y}{BLD}[6]{RST} {W}Check for yt-dlp Update")
    print(f"  {Y}{BLD}[0]{RST} {W}Exit")
    print()


def main():
    clear_screen()
    show_banner()
    ensure_all_dependencies()
    input(f"  {DIM}{W}Press Enter to continue...{RST}")

    def handle_sigint(sig, frame):
        print()
        exit_app()

    signal.signal(signal.SIGINT, handle_sigint)

    while True:
        show_menu()
        choice = input(f"  {O}{BLD}> {RST}").strip()

        if choice == "1":
            start_tools()
        elif choice == "2":
            stop_tools()
        elif choice == "3":
            show_history()
        elif choice == "4":
            show_settings()
        elif choice == "5":
            clear_downloads()
        elif choice == "6":
            check_ytdlp_update()
        elif choice == "0":
            exit_app()
        else:
            print(f"\n  {R}Invalid option. Choose 0-6.{RST}")
            input(f"  {DIM}{W}Press Enter to continue...{RST}")


if __name__ == "__main__":
    main()
