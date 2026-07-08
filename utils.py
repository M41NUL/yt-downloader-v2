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


class Spinner:
    """
    Simple threaded loading spinner for the Termux CLI.
    Usage:
        with Spinner("Starting server..."):
            do_slow_thing()
    Or manually:
        s = Spinner("Working...")
        s.start()
        ...
        s.stop("Done!")
    """
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message="Loading...", color=None):
        import threading
        self.message = message
        self.color = color or "\033[36m"  # cyan default
        self._stop_event = threading.Event()
        self._thread = None

    def _spin(self):
        import time as _time
        import sys as _sys
        i = 0
        while not self._stop_event.is_set():
            frame = self.FRAMES[i % len(self.FRAMES)]
            _sys.stdout.write(f"\r  {self.color}{frame}{RST} {W}{self.message}{RST}   ")
            _sys.stdout.flush()
            i += 1
            _time.sleep(0.08)

    def start(self):
        import threading
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def stop(self, final_message=None, success=True):
        import sys as _sys
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
        # clear the spinner line
        _sys.stdout.write("\r" + " " * (len(self.message) + 20) + "\r")
        _sys.stdout.flush()
        if final_message:
            mark_color = G if success else R
            mark = "✓" if success else "✗"
            print(f"  {mark_color}{mark}{RST} {W}{final_message}{RST}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
