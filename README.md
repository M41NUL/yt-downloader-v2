
# 🎬 YT DOWNLOADER

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Backend-000000?logo=flask&logoColor=white)
![yt--dlp](https://img.shields.io/badge/yt--dlp-powered-red?logo=youtube&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Termux-30d158)
![License](https://img.shields.io/badge/License-MIT-blue)

YouTube video & audio downloader — Flask + yt-dlp backend, single-page frontend, runs on your local WiFi (LAN). Supports single videos **and playlists** (auto zipped).

## 🚀 Install & Run

```bash
rm -rf yt-downloader-v2
git clone https://github.com/M41NUL/yt-downloader-v2.git
cd yt-downloader-v2
python main.py
```

First run auto-installs missing dependencies (`ffmpeg`, `yt-dlp`, `flask`, `flask-cors`) — nothing else to set up manually beyond Python itself.

## ✨ Features

- Video (MP4) or Audio (MP3), with quality selector (Auto/1080/720/480/360)
- Playlist support — downloads all tracks, bundles into a zip
- Thumbnail embedded as MP3 album art
- Auto-retry on failed downloads
- Download history + live progress in terminal
- Editable settings (quality, rate limit, cleanup age) — no code edits needed
- Scannable QR code for the LAN link

## 📌 Notes

- Same WiFi network only (LAN). For outside access, a tunnel (cloudflared/ngrok) would be needed.
- Files auto-delete after sending + hourly cleanup.

## 👤 Developer

[![GitHub](https://img.shields.io/badge/-M41NUL-181717?style=flat&logo=github&logoColor=white)](https://github.com/M41NUL)
[![Telegram](https://img.shields.io/badge/-mdmainulislaminfo-26A5E4?style=flat&logo=telegram&logoColor=white)](https://t.me/mdmainulislaminfo)
[![WhatsApp](https://img.shields.io/badge/-Contact-25D366?style=flat&logo=whatsapp&logoColor=white)](https://wa.me/8801308850528)
[![Email](https://img.shields.io/badge/-Email-EA4335?style=flat&logo=gmail&logoColor=white)](mailto:devmainulislam@gmail.com)

---
© 2026 CODEX-M41NUL. All Rights Reserved.
