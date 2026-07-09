# YT DOWNLOADER (Termux — Python)

Banner + menu-driven runner. Backend is Flask + yt-dlp. Frontend is served by Flask itself. Runs over your local WiFi network (LAN IP) — no internet tunnel needed.

## 1. One-time requirement (only this needs manual install)

```bash
pkg update && pkg upgrade -y
pkg install python -y
```

That's it. Everything else (`ffmpeg`, `yt-dlp`, `flask`, `flask-cors`) is **checked and auto-installed automatically** every time you run the tool — already-installed packages are skipped, missing ones get installed on the spot.

## 2. Project files

```
ytdl-tool-v2/
├── main.py           ← run this
├── setup.py          ← auto dependency checker/installer
├── settings.py       ← persisted, editable runtime settings (settings.json)
├── banner.py         ← banner + info box
├── config.py         ← dev/tool info, edit your links here
├── utils.py          ← colors
├── server.py         ← Flask backend (yt-dlp)
├── requirements.txt
└── public/
    └── index.html    ← frontend UI
```

Copy the whole folder into Termux, then:

```bash
cd ytdl-tool-v2
```

## 3. Run

```bash
python main.py
```

This shows:
1. The banner + info box
2. A dependency check (`[ok]` for installed, `[missing]` → auto-installs it), plus a daily yt-dlp version check
3. The menu:

```
[1] Start YT Downloader
[2] Stop
[3] History
[4] Settings
[5] Clear Downloads
[6] Check for yt-dlp Update
[0] Exit
```

- **1** → starts Flask in the background, prints your LAN link (e.g. `http://192.168.1.42:3000`), and shows a scannable ASCII QR code for that link.
- **2** → stops the server, back to the menu.
- **3** → shows download history, with a quick filter (all / video only / audio only / failed / successful).
- **4** → edit runtime settings: default quality, filename length limit, retry count, rate limit, and cleanup age. Stored in `settings.json`, no restart needed — the server reads them live.
- **5** → clears everything in `downloads/` on demand (asks for confirmation first).
- **6** → manually force a yt-dlp version check/update right now, instead of waiting for the automatic once-a-day check.
- **0** → stops everything and exits — warns if any files are still sitting in `downloads/` first.

The main menu also shows live status: whether the server is running, the current yt-dlp version, how many downloads are active right now (including playlist jobs), and how many leftover files are pending cleanup.

Open the printed link in any browser **on a device connected to the same WiFi** — that's your full frontend + backend, ready to paste a YouTube URL and download.

## Features

- **Video (MP4) or Audio (MP3)** — pick the format right in the UI. Video also lets you choose Auto/1080/720/480/360 quality.
- **Playlist support** — paste a playlist URL and it downloads every video/audio track, then bundles them into a zip.
- **Thumbnail embed** — MP3 downloads get the video thumbnail embedded as album art automatically.
- **Auto-retry** — a failed download is retried automatically (configurable, default 2 extra attempts) before it's marked failed.
- **Rate limiting** — per-IP limit on download requests to prevent abuse (configurable in Settings).
- **Smart filenames** — saved files use the real video title, automatically shortened if too long, with unsafe characters stripped.
- **Live download status** — while a download runs, the Termux terminal itself prints a live percentage (e.g. `[VIDEO] Song Name — 42%`), not just the web UI's progress bar.
- **Download history** — every completed or failed download is logged (title, format, quality, status, timestamp) in `history.json`, viewable and filterable from the menu's `[3] History` option.
- **Editable settings** — default quality, filename length limit, retry count, rate limit, and file cleanup age can all be changed from `[4] Settings` without touching code.
- **Scannable QR code** — starting the server prints an ASCII QR code of the LAN link so another phone can scan instead of typing it in.

## Notes

- This only works on the same WiFi network. To let devices outside your network use it, you'd need a tunnel service (cloudflared/ngrok) instead — ask if you want that added back.
- Edit `config.py` to put in your real Telegram/GitHub/YouTube/WhatsApp/Email links — that's what shows in the banner's info box.
- Files are deleted right after being sent, plus hourly cleanup for anything left behind in `downloads/`.
- yt-dlp updates itself automatically only when missing — if downloads start failing due to YouTube changes, run `pip install -U yt-dlp --break-system-packages` manually to force an update, or use menu option `[6]`. A background check also runs once per day automatically on startup.
- The QR code needs the optional `qrcode` package; if it's missing, the app still works fine and just shows the link as text instead. `setup.py` tries to install it automatically but won't block startup if that fails.
- If your phone's IP changes (e.g. reconnecting to WiFi), just restart (Stop then Start) to get the new link.
- If `pkg install` fails on ffmpeg (or anything else) even after the automatic retry, your Termux mirror may be broken. Run `termux-change-repo`, pick a different mirror, then try again.
