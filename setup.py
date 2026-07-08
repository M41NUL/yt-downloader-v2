# ─────────────────────────────────────────
#  YT DOWNLOADER — setup.py
#  Auto-checks & installs missing dependencies
#  Dev: Md. Mainul Islam (CODEX-M41NUL)
# ─────────────────────────────────────────

import shutil
import subprocess
import importlib.util

from utils import R, G, Y, C, W, DIM, BLD, RST

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


def _check_bin(name):
    return shutil.which(name) is not None


def _check_py(module_name):
    return importlib.util.find_spec(module_name) is not None


def _run(cmd, label):
    print(f"  {C}Installing {label}...{RST}")
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if result.returncode != 0:
            print(f"  {R}Failed to install {label}.{RST}")
            print(f"  {DIM}{W}{result.stdout[-400:]}{RST}")
            return False
        print(f"  {G}{label} installed.{RST}")
        return True
    except FileNotFoundError:
        print(f"  {R}Command not found: {cmd[0]}. Are you running this in Termux?{RST}")
        return False


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
            ok = _run(["pkg", "install", pkg_name, "-y"], pkg_name)
            all_ok = all_ok and ok

    # 2) yt-dlp (installed via pip, but it's a CLI binary once installed)
    ytdlp_installed = _check_bin("yt-dlp")
    if ytdlp_installed:
        print(f"  {G}[ok]{RST}    {W}yt-dlp{RST}")
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

    print()
    if all_ok:
        print(f"  {G}{BLD}All dependencies ready.{RST}\n")
    else:
        print(f"  {R}{BLD}Some dependencies failed to install — check messages above.{RST}\n")

    return all_ok


if __name__ == "__main__":
    ensure_all_dependencies()
