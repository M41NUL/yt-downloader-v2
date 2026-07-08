# ─────────────────────────────────────────
#  YT DOWNLOADER — main.py
#  Dev: Md. Mainul Islam (CODEX-M41NUL)
# ─────────────────────────────────────────

import os
import re
import sys
import time
import signal
import subprocess

from banner import show_banner
from utils import R, G, Y, C, O, W, BLD, DIM, RST, clear_screen
from config import FLASK_HOST, FLASK_PORT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

flask_proc = None
tunnel_proc = None
public_url = None


# ---------- process control ----------

def start_tools():
    global flask_proc, tunnel_proc, public_url

    if flask_proc is not None:
        print(f"\n  {Y}Already running.{RST}\n")
        return

    print(f"\n  {C}Starting Flask backend...{RST}")
    flask_proc = subprocess.Popen(
        [sys.executable, os.path.join(BASE_DIR, "server.py")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)

    if flask_proc.poll() is not None:
        print(f"  {R}Flask failed to start. Run 'python server.py' directly to see the error.{RST}\n")
        flask_proc = None
        return

    print(f"  {G}Flask backend running on http://{FLASK_HOST}:{FLASK_PORT}{RST}")
    print(f"  {C}Opening tunnel (cloudflared)...{RST}")

    try:
        tunnel_proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://{FLASK_HOST}:{FLASK_PORT}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        print(f"  {R}cloudflared not found. Install it: pkg install cloudflared{RST}\n")
        stop_tools()
        return

    print(f"  {DIM}{W}waiting for public link...{RST}")
    url_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
    deadline = time.time() + 25
    found = False

    while time.time() < deadline:
        line = tunnel_proc.stdout.readline()
        if not line:
            if tunnel_proc.poll() is not None:
                break
            continue
        match = url_pattern.search(line)
        if match:
            public_url = match.group(0)
            found = True
            break

    if found:
        print(f"\n  {O}{BLD}+{'─'*54}+{RST}")
        print(f"  {O}{BLD}|{RST}  {Y}{BLD}YOUR LINK IS READY{RST}{' '*35}{O}{BLD}|{RST}")
        print(f"  {O}{BLD}|{RST}  {G}{public_url}{RST}{' '*max(54-len(public_url)-2,0)}{O}{BLD}|{RST}")
        print(f"  {O}{BLD}+{'─'*54}+{RST}")
        print(f"\n  {DIM}{W}Open that link in any browser to use the downloader.{RST}\n")
    else:
        print(f"\n  {R}Could not detect the public link in time.{RST}")
        print(f"  {DIM}{W}The tunnel may still be starting — check manually or restart.{RST}\n")


def stop_tools():
    global flask_proc, tunnel_proc, public_url

    stopped_any = False

    if tunnel_proc is not None:
        try:
            tunnel_proc.terminate()
            tunnel_proc.wait(timeout=5)
        except Exception:
            try:
                tunnel_proc.kill()
            except Exception:
                pass
        tunnel_proc = None
        stopped_any = True

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
        stopped_any = True

    public_url = None

    if stopped_any:
        print(f"\n  {G}Stopped. Server and tunnel closed.{RST}\n")
    else:
        print(f"\n  {Y}Nothing is running.{RST}\n")


def exit_app():
    stop_tools()
    print(f"  {O}{BLD}Bye — CODEX-M41NUL{RST}\n")
    sys.exit(0)


# ---------- menu ----------

def show_menu():
    status = f"{G}● RUNNING{RST}" if flask_proc is not None else f"{DIM}{W}○ STOPPED{RST}"
    print(f"  {W}Status: {status}")
    if public_url:
        print(f"  {W}Link:   {C}{public_url}{RST}")
    print()
    print(f"  {Y}{BLD}[1]{RST} {W}Start YT Downloader")
    print(f"  {Y}{BLD}[2]{RST} {W}Stop")
    print(f"  {Y}{BLD}[0]{RST} {W}Exit")
    print()


def main():
    clear_screen()
    show_banner()

    def handle_sigint(sig, frame):
        print()
        exit_app()

    signal.signal(signal.SIGINT, handle_sigint)

    while True:
        show_menu()
        choice = input(f"  {O}{BLD}➜ {RST}").strip()

        if choice == "1":
            start_tools()
        elif choice == "2":
            stop_tools()
        elif choice == "0":
            exit_app()
        else:
            print(f"\n  {R}Invalid option. Choose 1, 2, or 0.{RST}\n")


if __name__ == "__main__":
    main()
