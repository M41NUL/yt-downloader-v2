# ─────────────────────────────────────────
#  YT DOWNLOADER — utils.py
#  ANSI color codes for terminal UI
# ─────────────────────────────────────────

R   = "\033[31m"   # Red
G   = "\033[32m"   # Green
Y   = "\033[33m"   # Yellow
B   = "\033[34m"   # Blue
M   = "\033[35m"   # Magenta
C   = "\033[36m"   # Cyan
W   = "\033[37m"   # White
O   = "\033[38;5;208m"  # Orange
PK  = "\033[38;5;213m"  # Pink
LG  = "\033[92m"   # Light Green

BLD = "\033[1m"
DIM = "\033[2m"
RST = "\033[0m"


def clear_screen():
    import os
    os.system("clear" if os.name != "nt" else "cls")
