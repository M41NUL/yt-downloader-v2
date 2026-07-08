# ─────────────────────────────────────────
#  YT DOWNLOADER — main.py
#  Dev: Md. Mainul Islam (CODEX-M41NUL)
# ─────────────────────────────────────────

import os
import sys
import time
import json
import socket
import signal
import subprocess

from banner import show_banner
from utils import R, G, Y, C, O, W, BLD, DIM, RST, clear_screen
from config import FLASK_HOST, FLASK_PORT, HISTORY_FILE
from setup import ensure_all_dependencies

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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


# ---------- process control ----------

def start_tools():
    global flask_proc, local_url

    if flask_proc is not None:
        print(f"\n  {Y}Already running.{RST}")
        input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")
        return

    print(f"\n  {C}Starting Flask backend...{RST}")
    flask_proc = subprocess.Popen(
        [sys.executable, os.path.join(BASE_DIR, "server.py")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)

    if flask_proc.poll() is not None:
        print(f"  {R}Flask failed to start. Run 'python server.py' directly to see the error.{RST}")
        input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")
        flask_proc = None
        return

    lan_ip = get_lan_ip()
    local_url = f"http://{lan_ip}:{FLASK_PORT}"

    width = 56
    print(f"\n{box_border(width)}")
    print(box_line("YOUR LINK IS READY", width, f"{Y}{BLD}"))
    print(box_line(local_url, width, f"{G}{BLD}"))
    print(box_border(width))
    print(f"\n  {DIM}{W}Open that link on any device connected to the SAME WiFi.{RST}\n")
    input(f"  {DIM}{W}Press Enter to go back to menu...{RST}")


def stop_tools(pause=True):
    global flask_proc, local_url

    if flask_proc is not None:
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
        print(f"\n  {G}Stopped. Server closed.{RST}")
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

    print(f"  {Y}{BLD}Recent downloads (latest first){RST}\n")
    for entry in reversed(history[-25:]):
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


def exit_app():
    stop_tools(pause=False)
    print(f"  {O}{BLD}Bye - CODEX-M41NUL{RST}\n")
    sys.exit(0)


# ---------- menu ----------

def show_menu():
    clear_screen()
    show_banner()
    status = f"{G}RUNNING{RST}" if flask_proc is not None else f"{DIM}{W}STOPPED{RST}"
    print(f"  {W}Status: {status}")
    if local_url:
        print(f"  {W}Link:   {C}{local_url}{RST}")
    print()
    print(f"  {Y}{BLD}[1]{RST} {W}Start YT Downloader")
    print(f"  {Y}{BLD}[2]{RST} {W}Stop")
    print(f"  {Y}{BLD}[3]{RST} {W}History")
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
        elif choice == "0":
            exit_app()
        else:
            print(f"\n  {R}Invalid option. Choose 1, 2, 3, or 0.{RST}")
            input(f"  {DIM}{W}Press Enter to continue...{RST}")


if __name__ == "__main__":
    main()
