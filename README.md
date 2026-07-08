# YT DOWNLOADER (Termux — Python)

Banner + menu-driven runner. Backend is Flask + yt-dlp. Frontend is served by Flask itself.

## 1. Install requirements (one-time, in Termux)

```bash
pkg update && pkg upgrade -y
pkg install python ffmpeg -y
pip install -U yt-dlp
pip install flask flask-cors --break-system-packages
pkg install cloudflared -y
```

Check:
```bash
python -V
yt-dlp --version
cloudflared --version
```

## 2. Project files

```
ytdl-tool-v2/
├── main.py           ← run this
├── banner.py         ← banner + info box
├── config.py         ← dev/tool info, edit your links here
├── utils.py          ← colors
├── server.py         ← Flask backend (yt-dlp)
├── requirements.txt
└── public/
    └── index.html    ← frontend UI (your existing design)
```

Copy the whole folder into Termux, then:

```bash
cd ytdl-tool-v2
```

## 3. Run

```bash
python main.py
```

This shows the banner + info box, then a menu:

```
[1] Start YT Downloader
[2] Stop
[0] Exit
```

- **1** → starts Flask (background) + opens a cloudflared tunnel, then prints your public link right in the terminal.
- **2** → stops both Flask and the tunnel, back to the menu.
- **0** → stops everything and exits.

Open the printed link in any browser — that's your full frontend + backend, ready to paste a YouTube URL and download.

## Notes

- Edit `config.py` to put in your real Telegram/GitHub/YouTube/WhatsApp/Email links — that's what shows in the banner's info box.
- Default quality is **Auto** (best available, merged to mp4). 1080/720/480/360 also selectable in the UI.
- Cloudflared's quick-tunnel link changes every time you press **Start** again — that's expected with the free quick-tunnel mode.
- Files are deleted right after being sent, plus hourly cleanup for anything left behind in `downloads/`.
- If some videos fail to download, run `pip install -U yt-dlp --break-system-packages` — YouTube changes often and yt-dlp updates to match.
