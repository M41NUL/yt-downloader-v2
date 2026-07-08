# ─────────────────────────────────────────
#  YT DOWNLOADER — setup.py
#  Auto-checks & installs missing dependencies
#  Dev: Md. Mainul Islam (CODEX-M41NUL)
# ─────────────────────────────────────────

import shutil
import subprocess
import importlib.util

from utils import R, G, Y, C, W, DIM, BLD, RST, Spinner

# (pkg_name_for_termux, check_type, check_value)
# check_type: "bin" -> checked via shutil.which
#             "py"  -> checked via importlib
PKG_CHECKS = [
    ("python",   "bin", "python"),
    ("ffmpeg",   "bin", "ffmpeg"),
]

PY_CHECKS = [
    ("yt-dlp",       "bin", "yt-dlp"),
    ("flask",        "py",  "flask"),
    ("flask-cors",   "py",  "flask_cors"),
]

# Optional: enables the ASCII QR code in the CLI. Not fatal if it fails to install.
OPTIONAL_PY_CHECKS = [
    ("qrcode", "py", "qrcode"),
]


def _check_bin(name):
    return shutil.which(name) is not None


def _check_py(module_name):
    return importlib.util.find_spec(module_name) is not None


def _run(cmd, label, is_pkg=False):
    spinner = Spinner(f"Installing {label}...").start()
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if result.returncode != 0:
            # Retry once after refreshing package lists (common cause: stale/broken mirror)
            if is_pkg:
                spinner.stop()
                spinner = Spinner(f"Install failed, refreshing package list and retrying...").start()
                subprocess.run(["pkg", "update", "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            if result.returncode != 0:
                spinner.stop(f"Failed to install {label}.", success=False)
                print(f"  {DIM}{W}{result.stdout[-400:]}{RST}")
                if is_pkg:
                    print(f"  {Y}Tip: your Termux mirror may be broken. Try:{RST}")
                    print(f"  {DIM}{W}  termux-change-repo{RST}")
                    print(f"  {DIM}{W}then pick a different mirror and run this again.{RST}")
                return False
        spinner.stop(f"{label} installed.")
        return True
    except FileNotFoundError:
        spinner.stop(f"Command not found: {cmd[0]}. Are you running this in Termux?", success=False)
        return False


_YTDLP_CHECK_FILE = ".ytdlp_last_check"


def _self_update_ytdlp():
    """
    Startup version check: keeps yt-dlp fresh so YouTube extractor changes
    don't silently break downloads. Skips the network check if it already
    ran today, so it doesn't slow down every single launch.
    """
    import time
    import os as _os

    check_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), _YTDLP_CHECK_FILE)
    today = time.strftime("%Y-%m-%d")

    if _os.path.exists(check_path):
        try:
            with open(check_path, "r") as fh:
                if fh.read().strip() == today:
                    return  # already checked today
        except OSError:
            pass

    spinner = Spinner("Checking for yt-dlp updates...").start()
    try:
        result = subprocess.run(
            ["pip", "install", "-U", "--break-system-packages", "yt-dlp"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60
        )
        if result.returncode == 0:
            if "Successfully installed" in result.stdout:
                spinner.stop("yt-dlp updated to the latest version.")
            else:
                spinner.stop("yt-dlp is already up to date.")
        else:
            spinner.stop("Could not check yt-dlp updates (offline or mirror issue) — continuing.", success=False)
    except Exception:
        spinner.stop("Could not check yt-dlp updates — continuing.", success=False)

    try:
        with open(check_path, "w") as fh:
            fh.write(today)
    except OSError:
        pass


def ensure_all_dependencies():
    """Check every required tool/library; install only what's missing. Returns True if all OK."""
    print(f"\n  {Y}{BLD}Checking dependencies...{RST}\n")

    all_ok = True

    # 1) Termux system packages (pkg)
    for pkg_name, kind, value in PKG_CHECKS:
        installed = _check_bin(value) if kind == "bin" else _check_py(value)
        if installed:
            print(f"  {G}[ok]{RST}    {W}{pkg_name}{RST}")
        else:
            print(f"  {Y}[missing]{RST} {W}{pkg_name}{RST}")
            ok = _run(["pkg", "install", pkg_name, "-y"], pkg_name, is_pkg=True)
            all_ok = all_ok and ok

    # 2) yt-dlp (installed via pip, but it's a CLI binary once installed)
    ytdlp_installed = _check_bin("yt-dlp")
    if ytdlp_installed:
        print(f"  {G}[ok]{RST}    {W}yt-dlp{RST}")
        _self_update_ytdlp()
    else:
        print(f"  {Y}[missing]{RST} {W}yt-dlp{RST}")
        ok = _run(["pip", "install", "-U", "--break-system-packages", "yt-dlp"], "yt-dlp")
        all_ok = all_ok and ok

    # 3) Python libraries (flask, flask-cors)
    for pkg_name, kind, value in PY_CHECKS:
        if pkg_name == "yt-dlp":
            continue  # already handled above
        installed = _check_py(value)
        if installed:
            print(f"  {G}[ok]{RST}    {W}{pkg_name}{RST}")
        else:
            print(f"  {Y}[missing]{RST} {W}{pkg_name}{RST}")
            ok = _run(["pip", "install", "--break-system-packages", pkg_name], pkg_name)
            all_ok = all_ok and ok

    # 4) Optional: qrcode (for the CLI QR link display) — best-effort only
    for pkg_name, kind, value in OPTIONAL_PY_CHECKS:
        installed = _check_py(value)
        if installed:
            print(f"  {G}[ok]{RST}    {W}{pkg_name}{RST} {DIM}(optional){RST}")
        else:
            print(f"  {Y}[missing]{RST} {W}{pkg_name}{RST} {DIM}(optional){RST}")
            _run(["pip", "install", "--break-system-packages", pkg_name], pkg_name)
            # optional: failure here doesn't affect all_ok

    print()
    if all_ok:
        print(f"  {G}{BLD}All dependencies ready.{RST}\n")
    else:
        print(f"  {R}{BLD}Some dependencies failed to install — check messages above.{RST}\n")

    return all_ok


if __name__ == "__main__":
    ensure_all_dependencies()
