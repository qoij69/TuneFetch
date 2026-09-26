#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TuneFetch  -  a Material-style YouTube & YouTube Music downloader (powered by yt-dlp)

Just double-click this file. On first launch it installs what it needs
(yt-dlp, customtkinter, Pillow, mutagen, ffmpeg) automatically.

Tip (Windows): rename to  tunefetch.pyw  to hide the console window.
"""
from __future__ import annotations

import io
import os
import re
import sys
import json
import time
import queue
import random
import shutil
import threading
import subprocess
import importlib
import importlib.util
import urllib.request
import urllib.parse
import csv
import base64
import unicodedata
from datetime import datetime
from pathlib import Path

APP_NAME = "TuneFetch"
APP_VERSION = "1.1"
IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DATA_DIR = Path.home() / ".tunefetch"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# pythonw / .pyw has no console streams
for _n in ("stdout", "stderr"):
    if getattr(sys, _n) is None:
        setattr(sys, _n, open(os.devnull, "w"))

# ─────────────────────────────────────────────────────────────────────────────
#  Logging (always on) -> ~/.tunefetch/tunefetch.log
# ─────────────────────────────────────────────────────────────────────────────
import logging                              # noqa: E402
import logging.handlers                     # noqa: E402
import traceback                            # noqa: E402
import faulthandler                         # noqa: E402

LOG_FILE = DATA_DIR / "tunefetch.log"
log = logging.getLogger("tunefetch")
log.setLevel(logging.DEBUG)
try:
    _fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s"))
    log.addHandler(_fh)
except Exception:
    pass
try:  # also mirror to the console when there is one
    _sh = logging.StreamHandler(sys.__stderr__ or sys.stderr)
    _sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    log.addHandler(_sh)
except Exception:
    pass
try:  # hard crashes (segfaults etc.) also land in a file
    _crash_fp = open(DATA_DIR / "crash.log", "a", encoding="utf-8")
    faulthandler.enable(_crash_fp)
except Exception:
    pass


def _excepthook(et, ev, tb):
    log.critical("UNCAUGHT EXCEPTION\n%s", "".join(traceback.format_exception(et, ev, tb)))


def _thread_excepthook(args):
    log.critical("UNCAUGHT EXCEPTION IN THREAD %s\n%s", getattr(args.thread, "name", "?"),
                 "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))


sys.excepthook = _excepthook
threading.excepthook = _thread_excepthook
log.info("=" * 60)
log.info("Starting %s %s | Python %s | %s", APP_NAME, APP_VERSION, sys.version.split()[0], sys.platform)
log.info("Executable: %s | Script: %s", sys.executable, os.path.abspath(__file__))

# ─────────────────────────────────────────────────────────────────────────────
#  First-run bootstrap: install missing packages with a tiny splash window
# ─────────────────────────────────────────────────────────────────────────────
REQUIRED = [
    ("yt_dlp", "yt-dlp"),
    ("customtkinter", "customtkinter"),
    ("PIL", "Pillow"),
    ("mutagen", "mutagen"),
    ("imageio_ffmpeg", "imageio-ffmpeg"),
    ("certifi", "certifi"),
    ("truststore", "truststore"),
]


def _pip(pkg: str) -> bool:
    base = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-q", pkg]
    for extra in ([], ["--user"], ["--user", "--break-system-packages"]):
        try:
            r = subprocess.run(base + extra, capture_output=True, text=True, creationflags=NO_WINDOW)
            if r.returncode == 0:
                log.info("pip installed %s %s", pkg, " ".join(extra))
                return True
            log.error("pip failed for %s %s (code %s): %s", pkg, " ".join(extra), r.returncode,
                      (r.stderr or r.stdout or "")[-1500:])
        except Exception:
            log.exception("pip crashed for %s", pkg)
    return False


def _missing():
    return [p for m, p in REQUIRED if importlib.util.find_spec(m) is None]


def bootstrap():
    missing = _missing()
    if not missing:
        return
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("460x180")
    root.resizable(False, False)
    root.configure(bg="#141218")
    tk.Label(root, text=APP_NAME, bg="#141218", fg="#D0BCFF", font=("Segoe UI", 22, "bold")).pack(pady=(24, 0))
    tk.Label(root, text="First launch - setting things up (one time only)", bg="#141218", fg="#CAC4D0",
             font=("Segoe UI", 10)).pack(pady=(2, 10))
    status = tk.Label(root, text="Preparing...", bg="#141218", fg="#E6E0E9", font=("Segoe UI", 11))
    status.pack()
    state = {"msg": "Preparing...", "fail": None, "done": False}

    def work():
        for i, pkg in enumerate(missing):
            state["msg"] = f"Installing {pkg}  ({i + 1}/{len(missing)})"
            if not _pip(pkg):
                state["fail"] = pkg
                break
        state["done"] = True

    threading.Thread(target=work, daemon=True).start()

    def poll():
        status.config(text=state["msg"])
        if state["done"]:
            root.destroy()
        else:
            root.after(200, poll)

    poll()
    root.mainloop()

    importlib.invalidate_caches()
    try:
        import site
        u = site.getusersitepackages()
        if u not in sys.path:
            sys.path.append(u)
    except Exception:
        pass

    still = _missing()
    log.info("Bootstrap finished. failed=%s still_missing=%s", state["fail"], still)
    if state["fail"] or still:
        r = tk.Tk()
        r.withdraw()
        pk = " ".join(still or [state["fail"]])
        messagebox.showerror(APP_NAME, f"Couldn't install: {pk}\n\nPlease run this in a terminal and start again:\n\n"
                                       f"python -m pip install {pk}")
        sys.exit(1)


if not getattr(sys, "frozen", False):        # a PyInstaller exe already bundles every dependency
    bootstrap()

import tkinter as tk                       # noqa: E402
import tkinter.font as tkfont              # noqa: E402
from tkinter import ttk, filedialog, messagebox  # noqa: E402
import customtkinter as ctk                # noqa: E402
import yt_dlp                              # noqa: E402
from yt_dlp.postprocessor.common import PostProcessor  # noqa: E402
from PIL import Image                      # noqa: E402

try:
    from yt_dlp.utils import DownloadCancelled as _CancelBase
except Exception:  # pragma: no cover
    _CancelBase = Exception


class Cancelled(_CancelBase):
    pass


# ─────────────────────────────────────────────────────────────────────────────
#  Constants & settings
# ─────────────────────────────────────────────────────────────────────────────
AUDIO_FORMATS = {"MP3": "mp3", "M4A": "m4a", "OPUS": "opus", "FLAC": "flac",
                 "OGG": "vorbis", "WAV": "wav", "AAC": "aac", "Original": "best"}
LOSSY = {"MP3", "M4A", "OPUS", "OGG", "AAC"}
AUDIO_Q = ["Best", "320 kbps", "256 kbps", "192 kbps", "128 kbps", "96 kbps"]
VIDEO_FORMATS = ["MP4", "MKV", "WEBM"]
VIDEO_RES = {"Best": None, "4K - 2160p": 2160, "1440p": 1440, "1080p": 1080,
             "720p": 720, "480p": 480, "360p": 360, "240p": 240}
COVER_EMBED_EXT = {"mp3", "m4a", "opus", "vorbis", "flac", "mp4", "mkv"}   # containers yt-dlp can tag with art
TEMPLATES = {
    "Title": "%(title)s",
    "Artist - Title": "%(artist,uploader)s - %(title)s",
    "Title [ID]": "%(title)s [%(id)s]",
    "Uploader - Title": "%(uploader)s - %(title)s",
}
BROWSERS = ["none", "chrome", "firefox", "edge", "brave", "opera", "vivaldi", "chromium", "safari"]
AFTER_ACTIONS = ["Do nothing", "Open folder", "Close app", "Shut down PC"]
FINAL = {"Done", "Skipped", "Error", "Canceled"}
URL_RE = re.compile(r"^(https?://|www\.)", re.I)
YT_RE = re.compile(r"^https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)/\S+", re.I)
LINK_RE = re.compile(r"^(?:https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)/|https?://open\.spotify\.com/|spotify:)\S+", re.I)

DEFAULTS = dict(
    out_dir=str(Path.home() / "Downloads" / "TuneFetch"),
    mode="audio", audio_fmt="MP3", audio_q="320 kbps", video_fmt="MP4", video_res="1080p",
    embed_cover=True, square_cover=True, keep_thumb=False, embed_meta=True, smart_tags=True,
    playlist_album=True, playlist_folder=True, number_tracks=True, m3u=False,
    skip_existing=False, sponsorblock=False, subtitles=False, subs_lang="en", single_video=False,
    template="Title", parallel=2, speed_limit="", cookies_browser="none", cookies_file="", proxy="",
    theme="Dark", accent="Violet", clipboard_watch=True, sound=True, confetti=True,
    after_action="Do nothing", match_source="YouTube Music", spotify_id="", spotify_secret="",
)

ACCENTS = {  # name: (dark(primary, on_primary, container, on_container), light(...))
    "Violet": (("#D0BCFF", "#381E72", "#4F378B", "#EADDFF"), ("#6750A4", "#FFFFFF", "#EADDFF", "#21005D")),
    "Ocean": (("#9ECAFF", "#003258", "#00497D", "#D1E4FF"), ("#0061A4", "#FFFFFF", "#D1E4FF", "#001D36")),
    "Mint": (("#78DC77", "#00390A", "#005313", "#94F990"), ("#006E1C", "#FFFFFF", "#94F990", "#002204")),
    "Rose": (("#FFB1C8", "#650033", "#8E1657", "#FFD9E3"), ("#B4005F", "#FFFFFF", "#FFD9E3", "#3E001D")),
    "Amber": (("#FFB77C", "#4E2600", "#703800", "#FFDCC2"), ("#8B5000", "#FFFFFF", "#FFDCBD", "#2D1600")),
    "Teal": (("#4FD8EB", "#00363D", "#004F58", "#97F0FF"), ("#006874", "#FFFFFF", "#97F0FF", "#001F24")),
}


def mix(a: str, b: str, t: float) -> str:
    a, b = a.lstrip("#"), b.lstrip("#")
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def make_palette(theme: str, accent: str) -> dict:
    dark_a, light_a = ACCENTS.get(accent, ACCENTS["Violet"])
    if theme == "Dark":
        p, onp, c, onc = dark_a
        inv = light_a[0]
        pal = dict(bg="#141218", card="#211F26", high="#2B2930", highest="#36343B", outline="#938F99",
                   outline_var="#49454F", text="#E6E0E9", text2="#CAC4D0", error="#F2B8B5", ok="#8FD98F")
    else:
        p, onp, c, onc = light_a
        inv = dark_a[0]
        pal = dict(bg="#FEF7FF", card="#F3EDF7", high="#ECE6F0", highest="#E6E0E9", outline="#79747E",
                   outline_var="#CAC4D0", text="#1D1B20", text2="#49454F", error="#B3261E", ok="#1B7F2A")
    pal.update(primary=p, on_primary=onp, container=c, on_container=onc, inv_primary=inv, mode=theme)
    pal["primary_hover"] = mix(p, pal["text"], 0.15)
    pal["container_hover"] = mix(c, pal["text"], 0.12)
    return pal


class Config:
    def __init__(self):
        self.path = DATA_DIR / "settings.json"
        self.d = dict(DEFAULTS)
        try:
            self.d.update(json.loads(self.path.read_text("utf-8")))
        except Exception:
            pass

    def __getitem__(self, k):
        return self.d.get(k, DEFAULTS.get(k))

    def __setitem__(self, k, v):
        self.d[k] = v

    def save(self):
        try:
            self.path.write_text(json.dumps(self.d, indent=2), "utf-8")
        except Exception:
            pass

    def snapshot(self):
        return dict(self.d)

    def reset(self):
        self.d = dict(DEFAULTS)
        self.save()


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────
def fmt_dur(s):
    if not s:
        return ""
    s = int(s)
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def fmt_size(n):
    n = float(n or 0)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024


def fmt_speed(v):
    return f"{fmt_size(v)}/s" if v else ""


def fmt_eta(v):
    return fmt_dur(v) if v else ""


def safe_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f%]', "_", name or "").strip(" .")
    return name[:120] or "Playlist"


def clean_err(e) -> str:
    if "CERTIFICATE_VERIFY_FAILED" in str(e):
        return ("Secure connection blocked (certificate check failed). Antivirus HTTPS scanning, a proxy or an "
                "outdated Windows certificate store is usually the cause - see the log")
    s = re.sub(r"\x1b\[[0-9;]*m", "", str(e)).replace("ERROR: ", "").strip()
    return s.splitlines()[-1] if s else "Unknown error"


def open_path(p):
    p = str(p)
    try:
        if IS_WIN:
            os.startfile(p)  # type: ignore[attr-defined]
        elif IS_MAC:
            subprocess.Popen(["open", p])
        else:
            subprocess.Popen(["xdg-open", p])
    except Exception:
        pass


def bar_text(pct, status):
    if status == "Queued":
        return ""
    n = int(round(max(0, min(100, pct or 0)) / 100 * 14))
    return "▰" * n + "▱" * (14 - n) + f" {pct or 0:3.0f}%"


class QuietLogger:
    """Sends yt-dlp output to the log file instead of the console (also keeps pythonw happy)."""
    def __init__(self, tag="yt-dlp"):
        self.tag = tag

    def debug(self, msg):
        log.debug("[%s] %s", self.tag, msg)

    def info(self, msg):
        log.debug("[%s] %s", self.tag, msg)

    def warning(self, msg):
        log.warning("[%s] %s", self.tag, msg)

    def error(self, msg):
        log.error("[%s] %s", self.tag, msg)


def find_ffmpeg():
    """Return a directory containing ffmpeg (or None to let yt-dlp use PATH)."""
    if shutil.which("ffmpeg"):
        return None, True
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        d = DATA_DIR / "ffmpeg"
        d.mkdir(exist_ok=True)
        target = d / ("ffmpeg.exe" if IS_WIN else "ffmpeg")
        if not target.exists():
            shutil.copy2(exe, target)
            if not IS_WIN:
                target.chmod(0o755)
        return str(d), True
    except Exception:
        log.exception("ffmpeg setup failed")
        return None, False


def make_item(e, pl_title, idx, count):
    url = e.get("webpage_url") or e.get("url") or ""
    if not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={e.get('id') or url}"
    thumbs = e.get("thumbnails") or []
    thumb = e.get("thumbnail") or (thumbs[-1].get("url") if thumbs else None)
    dur = e.get("duration")
    return dict(
        url=url, title=e.get("title") or url,
        uploader=(e.get("artist") or e.get("uploader") or e.get("channel") or "").replace(" - Topic", ""),
        duration=int(dur) if isinstance(dur, (int, float)) else None,
        thumb=thumb, pl_title=pl_title, pl_index=idx, pl_count=count, checked=True)


def collect_items(info, items):
    if not info:
        return
    if info.get("_type") == "playlist" or info.get("entries") is not None:
        is_search = "search" in str(info.get("extractor_key", "")).lower()
        title = None if is_search else (info.get("title") or None)
        entries = [e for e in list(info.get("entries") or []) if e]
        for i, e in enumerate(entries, 1):
            if not (e.get("url") or e.get("webpage_url") or e.get("id")):
                continue
            if (e.get("title") or "") in ("[Private video]", "[Deleted video]"):
                continue
            items.append(make_item(e, title, 0 if is_search else i, len(entries)))
    else:
        items.append(make_item(info, None, 0, 1))



# ─────────────────────────────────────────────────────────────────────────────
#  Spotify -> YouTube matching
# ─────────────────────────────────────────────────────────────────────────────
SPOTIFY_RE = re.compile(r"(?:open\.spotify\.com/(?:intl-[a-z\-]+/)?(?:embed/)?(?:user/[^/\s]+/)?|spotify:(?:user:[^:\s]+:)?)"
                        r"(playlist|album|track)[/:]([A-Za-z0-9]{22})", re.I)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9"}
# whole words only - a plain substring test flagged "Alive" as live and "Discover" as cover
BAD_RE = re.compile(r"\b(live|cover|karaoke|instrumental|sped up|slowed|reverb|nightcore|8d audio|remix|mashup)\b", re.I)


_SSL_CTXS = None


def ssl_contexts():
    """Certificate sources to try in order: Python's default, the OS trust store (truststore), certifi's bundle.
    Some Windows / Microsoft-Store Python installs fail with 'unable to get local issuer certificate'."""
    global _SSL_CTXS
    if _SSL_CTXS is None:
        import ssl
        ctxs = [ssl.create_default_context()]
        try:
            import certifi
            ctxs.append(ssl.create_default_context(cafile=certifi.where()))
        except Exception:
            pass
        try:
            import truststore
            ctxs.append(truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT))
        except Exception:
            pass
        _SSL_CTXS = ctxs
    return _SSL_CTXS


def _is_ssl_error(e):
    import ssl
    return isinstance(e, ssl.SSLError) or isinstance(getattr(e, "reason", None), ssl.SSLError) \
        or "CERTIFICATE_VERIFY_FAILED" in str(e)


def http_bytes(url, headers=None, data=None, timeout=20):
    h = dict(UA)
    h.update(headers or {})
    last = None
    for ctx in ssl_contexts():
        req = urllib.request.Request(url, data=data, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return r.read(), r.geturl()
        except Exception as e:
            if not _is_ssl_error(e):
                raise
            last = e
            log.warning("TLS verification failed for %s with one certificate source (%s) - trying the next", url[:60], e)
    raise last


def http_get(url, headers=None, data=None, timeout=20):
    body, final = http_bytes(url, headers, data, timeout)
    return body.decode("utf-8", "replace"), final


def find_dict(obj, pred, depth=0):
    if depth > 14:
        return None
    if isinstance(obj, dict):
        try:
            if pred(obj):
                return obj
        except Exception:
            pass
        for v in obj.values():
            r = find_dict(v, pred, depth + 1)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_dict(v, pred, depth + 1)
            if r:
                return r
    return None


def spotify_ref(line):
    """Return (kind, id) if the line is a Spotify playlist/album/track link or URI."""
    try:
        if re.search(r"spotify\.(link|app\.link)/", line):
            line = http_get(line)[1]
    except Exception:
        log.warning("Couldn't expand Spotify short link %s", line)
    m = SPOTIFY_RE.search(line)
    return (m.group(1).lower(), m.group(2)) if m else None


def _emb_track(t, sid=None):
    title = t.get("title") or t.get("name")
    artist = t.get("subtitle") or ", ".join(a.get("name", "") for a in (t.get("artists") or []) if isinstance(a, dict))
    artist = (artist or "").replace("\u00a0", " ").strip()
    d = t.get("duration") or t.get("duration_ms") or t.get("durationMs")
    sec = int(d / 1000) if isinstance(d, (int, float)) and d > 1000 else (int(d) if isinstance(d, (int, float)) and d else None)
    uri = t.get("uri") or ""
    tid = uri.split(":")[-1] if uri.startswith("spotify:track:") else sid
    return dict(title=title, artist=artist, album=None, duration=sec, id=tid)


def _emb_thumb(ent):
    try:
        srcs = (ent.get("coverArt") or {}).get("sources") or ent.get("images") or []
        return (srcs[-1] if srcs else {}).get("url")
    except Exception:
        return None


def spotify_embed(kind, sid):
    """No-login route: read the public embed page (Spotify only exposes the first ~50-100 tracks this way)."""
    html, _ = http_get(f"https://open.spotify.com/embed/{kind}/{sid}")
    m = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("Spotify's public page had no track data (Spotify may have changed its layout)")
    data = json.loads(m.group(1))
    if kind == "track":
        ent = find_dict(data, lambda d: (d.get("name") or d.get("title")) and (d.get("artists") or d.get("subtitle"))
                        and (d.get("duration") or d.get("duration_ms") or d.get("uri")))
        if not ent:
            raise RuntimeError("Couldn't read that Spotify track")
        return dict(title=None, owner="", thumb=None, tracks=[_emb_track(ent, sid)], partial=False)
    ent = find_dict(data, lambda d: isinstance(d.get("trackList"), list))
    if not ent:
        raise RuntimeError("Couldn't read the track list (private playlist, or Spotify changed its layout)")
    tracks = [_emb_track(t) for t in ent["trackList"] if t and (t.get("title") or t.get("name"))]
    total = ent.get("trackCount") or ent.get("total")
    partial = (total > len(tracks)) if isinstance(total, int) else len(tracks) in (50, 100)
    return dict(title=ent.get("name") or ent.get("title") or "Spotify playlist", owner=ent.get("subtitle") or "",
                thumb=_emb_thumb(ent), tracks=tracks, partial=partial, total=total)


def _api_track(t, album=None):
    return dict(title=t.get("name"), artist=", ".join(a.get("name", "") for a in (t.get("artists") or [])),
                album=album or (t.get("album") or {}).get("name"),
                duration=int(t["duration_ms"] / 1000) if t.get("duration_ms") else None, id=t.get("id"))


def spotify_api(kind, sid, cid, secret):
    """Official route with the user's own developer keys (client-credentials flow)."""
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    tok = json.loads(http_get("https://accounts.spotify.com/api/token", data=b"grant_type=client_credentials",
                              headers={"Authorization": "Basic " + auth,
                                       "Content-Type": "application/x-www-form-urlencoded"})[0])["access_token"]
    H = {"Authorization": "Bearer " + tok}

    def g(path):
        url = path if path.startswith("http") else "https://api.spotify.com/v1" + path
        return json.loads(http_get(url, headers=H)[0])

    if kind == "track":
        t = g(f"/tracks/{sid}")
        return dict(title=None, owner="", thumb=None, tracks=[_api_track(t)], partial=False)
    if kind == "album":
        a = g(f"/albums/{sid}")
        tracks, page = [], a.get("tracks") or {}
        while page:
            tracks += [_api_track(t, a.get("name")) for t in page.get("items", []) if t]
            page = g(page["next"]) if page.get("next") else None
        return dict(title=a.get("name"), owner=", ".join(x["name"] for x in a.get("artists", [])),
                    thumb=(a.get("images") or [{}])[0].get("url"), tracks=tracks, partial=False)
    p = g(f"/playlists/{sid}")
    tracks, offset, base = [], 0, "items"
    while True:
        try:
            page = g(f"/playlists/{sid}/{base}?limit=100&offset={offset}")
        except urllib.error.HTTPError as e:
            if base == "items" and e.code in (400, 404):   # older API path
                base = "tracks"
                continue
            raise
        for it in page.get("items", []):
            tr = it.get("item") or it.get("track")
            if not tr or tr.get("type") == "episode" or tr.get("is_local"):
                continue
            tracks.append(_api_track(tr))
        if not page.get("next"):
            break
        offset += 100
    return dict(title=p.get("name"), owner=(p.get("owner") or {}).get("display_name") or "",
                thumb=(p.get("images") or [{}])[0].get("url"), tracks=tracks, partial=False)


def spotify_fetch(ref, o):
    kind, sid = ref
    cid, sec = str(o["spotify_id"]).strip(), str(o["spotify_secret"]).strip()
    api_err = None
    if cid and sec:
        try:
            res = spotify_api(kind, sid, cid, sec)
            res["source"] = "api"
            return res
        except Exception as e:
            api_err = e
            log.warning("Spotify API failed (%s) - falling back to public preview", e)
    try:
        res = spotify_embed(kind, sid)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Spotify answered {e.code} - that {kind} may be private or removed. Add API keys in "
                           "Settings, or use Import list with an Exportify CSV.") from e
    res["source"] = "embed"
    res["api_error"] = str(api_err) if api_err else None
    return res


def make_sp_item(t, pl_title, idx, count, origin="spotify"):
    tid = t.get("id")
    return dict(url=f"https://open.spotify.com/track/{tid}" if tid else "", title=t["title"],
                uploader=t.get("artist") or "", duration=t.get("duration"), thumb=None, pl_title=pl_title,
                pl_index=idx, pl_count=count, checked=True, origin=origin,
                sp=dict(title=t["title"], artist=t.get("artist") or "", album=t.get("album"),
                        duration=t.get("duration"), id=tid))


TABULAR_EXT = (".csv", ".tsv")
LIST_EXT = (".csv", ".tsv", ".txt")
_ID22 = re.compile(r"(?<![A-Za-z0-9])([A-Za-z0-9]{22})(?![A-Za-z0-9])")
# header names used by Exportify, TuneMyMusic, Soundiiz, Spotify-to-CSV tools ... (all lower-case)
_COLS = dict(
    title=("track name", "track title", "song name", "song title", "song", "title", "track", "name"),
    artist=("artist name(s)", "artist names", "artist name", "artist(s)", "artists", "artist", "performer"),
    album=("album name", "album title", "album"),
    dur=("duration (ms)", "duration_ms", "duration ms", "duration", "length", "time"),
    uri=("track uri", "spotify uri", "spotify - id", "spotify id", "spotify_id", "track id", "uri", "id"),
    plist=("playlist name", "playlist"),
)


def _read_text(path):
    """Decode a text file from Excel / Exportify / Notepad (UTF-8, UTF-16 or Windows-1252)."""
    raw = Path(path).read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "replace")


def _parse_dur(v, ms_hint=False):
    v = str(v or "").strip()
    if not v:
        return None
    if ":" in v:                                    # 3:45 or 1:02:03
        try:
            sec = 0
            for p in v.split(":"):
                sec = sec * 60 + int(p)
            return sec or None
        except ValueError:
            return None
    try:
        f = float(v)
    except ValueError:
        return None
    if f <= 0:
        return None
    return (int(f / 1000) if (ms_hint or f > 20000) else int(f)) or None


def parse_track_list(path):
    """Read an Exportify / TuneMyMusic / Soundiiz style CSV, or a text list.
    Text lines can be 'Artist - Title' or a YouTube / Spotify link.
    Returns dict(tracks=[...], urls=[...], dupes=<number of repeated rows skipped>)."""
    text = _read_text(path).lstrip("\r\n")
    tracks, urls, seen, dupes = [], [], set(), 0

    def add(t):
        nonlocal dupes
        key = (t["title"].lower(), (t.get("artist") or "").lower(), t.get("playlist") or "")
        if key in seen:
            dupes += 1
            return
        seen.add(key)
        tracks.append(t)

    if str(path).lower().endswith(TABULAR_EXT):
        head = next((l for l in text.splitlines() if l.strip()), "")
        delim = max(",;\t|", key=head.count) if any(head.count(d) for d in ",;\t|") else ","
        rd = csv.DictReader(io.StringIO(text), delimiter=delim)
        low = {(k or "").strip().lower(): k for k in (rd.fieldnames or []) if k is not None}

        def col(key):
            return next((low[n] for n in _COLS[key] if n in low), None)
        ct, ca, cal, cd, cu, cp = (col(k) for k in ("title", "artist", "album", "dur", "uri", "plist"))
        if not ct:
            raise ValueError("Couldn't find a 'Track Name' column in that CSV (found: "
                             + (", ".join(list(low)[:6]) or "no header row") + ")")
        ms_hint = bool(cd and "ms" in cd.lower())
        for row in rd:
            title = (row.get(ct) or "").strip()
            if not title:
                continue
            artist = re.sub(r"\s*;\s*", ", ", (row.get(ca) or "").strip()) if ca else ""
            m = _ID22.search(row.get(cu) or "") if cu else None
            add(dict(title=title, artist=artist,
                     album=((row.get(cal) or "").strip() or None) if cal else None,
                     duration=_parse_dur(row.get(cd), ms_hint) if cd else None,
                     id=m.group(1) if m else None,
                     playlist=((row.get(cp) or "").strip() or None) if cp else None))
    else:
        for line in text.splitlines():
            line = line.strip().strip('"')
            if not line or line.startswith("#"):
                continue
            if URL_RE.match(line) or SPOTIFY_RE.search(line):
                urls.append(line)
                continue
            m = re.match(r"^(.+?)\s+[-\u2013\u2014]\s+(.+)$", line)
            artist, title = (m.group(1), m.group(2)) if m else ("", line)
            add(dict(title=title.strip(), artist=artist.strip(), album=None, duration=None, id=None, playlist=None))
    return dict(tracks=tracks, urls=urls, dupes=dupes)


def items_from_list_file(path):
    """-> (items, urls, dupes, playlist_names) ready for the preview / queue.
    A 'Playlist Name' column splits one file into several playlists; otherwise the file name is used."""
    res = parse_track_list(path)
    stem = Path(path).stem
    groups = {}
    for t in res["tracks"]:
        groups.setdefault(t.get("playlist") or stem, []).append(t)
    items = []
    for name, ts in groups.items():
        for i, t in enumerate(ts, 1):
            items.append(make_sp_item(t, name, i, len(ts), origin="list"))
    return items, res["urls"], res["dupes"], list(groups)


_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")


def _norm(s):
    s = s or ""
    if not _CJK.search(s):                  # 'Bésame' == 'Besame' (but leave kana / hanzi alone)
        s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s.lower())).strip()


def _core_title(t):
    """'Song (feat. X) - Remastered 2011' -> 'Song' (only used for matching)."""
    t = t or ""
    core = re.split(r"\s+[-\u2013\u2014]\s+", re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", " ", t))[0].strip()
    return core or t.strip()


def score_match(sp, e):
    """Rate how well a YouTube result matches a Spotify track (higher = better)."""
    s = 0.0
    dur, sd = e.get("duration"), sp.get("duration")
    if sd and isinstance(dur, (int, float)) and dur:
        d = abs(dur - sd)
        s += 60 if d <= 2 else 45 if d <= 5 else 25 if d <= 10 else 0 if d <= 20 else -40
    title = _norm(e.get("title"))
    chan_raw = e.get("uploader") or e.get("channel") or ""
    chan = _norm(chan_raw)
    st = _norm(_core_title(sp["title"]))
    if st and re.search(rf"(?<!\w){re.escape(st)}(?!\w)", title):
        s += 25
    elif st:
        tt = set(st.split())
        s += 25 * len(tt & set(title.split())) / max(1, len(tt))
    arts = [_norm(a) for a in re.split(r"[,;]|\s&\s", sp.get("artist") or "")]
    if any(a and (a in title or a in chan) for a in arts):
        s += 15
    if chan_raw.endswith("- Topic"):
        s += 12
    yt_bad = {m.lower() for m in BAD_RE.findall(e.get("title") or "")}
    sp_bad = {m.lower() for m in BAD_RE.findall(f"{sp['title']} {sp.get('album') or ''}")}
    s -= 30 * len(yt_bad - sp_bad)
    return s


class SmartTags(PostProcessor):
    """Cleans titles, splits 'Artist - Title', adds album / track number from the playlist."""
    NOISE = re.compile(r"\s*[\(\[][^\)\]]*\b(official|lyrics?|lyric video|audio|video|visuali[sz]er|hd|hq|4k|music video)\b[^\)\]]*[\)\]]", re.I)

    def __init__(self, dl, job):
        super().__init__(dl)
        self.job = job

    def run(self, info):
        o = self.job.opts
        sp = getattr(self.job, "sp", None)
        try:
            if sp:
                info["title"] = sp["title"]
                info["track"] = sp["title"]
                if sp.get("artist"):
                    info["artist"] = sp["artist"]
                if sp.get("album"):
                    info["album"] = sp["album"]
            elif o["smart_tags"]:
                title = info.get("title") or ""
                clean = self.NOISE.sub("", title).strip(" -–—") or title
                m = re.match(r"^(.{1,80}?)\s+[-–—]\s+(.+)$", clean)
                if m and not info.get("artist") and not info.get("track"):
                    info["artist"] = m.group(1).strip()
                    info["title"] = m.group(2).strip()
                    info["track"] = info["title"]
                else:
                    info["title"] = clean
                if not info.get("artist"):
                    up = info.get("uploader") or info.get("channel") or ""
                    info["artist"] = re.sub(r"\s*-\s*Topic$", "", up)
            if o["playlist_album"] and self.job.pl_title:
                if not info.get("album"):
                    info["album"] = self.job.pl_title
                if self.job.pl_index:
                    info["track_number"] = self.job.pl_index
        except Exception:
            pass
        return [], info


class Job:
    _n = 0

    def __init__(self, item, opts, width):
        Job._n += 1
        self.id = f"j{Job._n}"
        self.no = Job._n
        self.url = item["url"]
        self.title = item["title"]
        self.sp = item.get("sp")
        self.match_url = None
        if self.sp and self.sp.get("artist"):
            self.title = f"{self.sp['artist']} - {self.sp['title']}"
        self.pl_title = item["pl_title"]
        self.pl_index = item["pl_index"]
        self.pl_width = width
        self.opts = opts
        self.status = "Queued"
        self.pct = 0.0
        self.speed = None
        self.eta = None
        self.path = None
        self.error = ""
        self.counted = False
        self.fin = 0          # finished streams (video + audio download separately)
        self.cancel = threading.Event()
        if opts["mode"] == "audio":
            f = opts["audio_fmt"]
            self.label = f"{f} · {opts['audio_q']}" if f in LOSSY else f
        else:
            self.label = f"{opts['video_fmt']} · {opts['video_res']}"


# ─────────────────────────────────────────────────────────────────────────────
#  Small Material-ish widgets
# ─────────────────────────────────────────────────────────────────────────────
class Chips(ctk.CTkFrame):
    """Material 'filter chips' - a single-choice group."""

    def __init__(self, master, app, values, value, command, cols=4):
        super().__init__(master, fg_color="transparent")
        self.app, self.values, self.command, self.value = app, values, command, value
        self.btns = {}
        for i, v in enumerate(values):
            b = ctk.CTkButton(self, text=v, height=34, width=60, corner_radius=10, font=app.F(12, "bold"),
                              command=lambda v=v: self._pick(v))
            b.grid(row=i // cols, column=i % cols, padx=3, pady=3, sticky="ew")
            self.btns[v] = b
        for c in range(min(cols, len(values))):
            self.grid_columnconfigure(c, weight=1)
        self._paint()

    def _paint(self):
        P = self.app.P
        for v, b in self.btns.items():
            if v == self.value:
                b.configure(fg_color=P["container"], hover_color=P["container_hover"], text_color=P["on_container"],
                            border_width=0)
            else:
                b.configure(fg_color="transparent", hover_color=P["high"], text_color=P["text2"],
                            border_width=1, border_color=P["outline_var"])

    def _pick(self, v):
        self.value = v
        self._paint()
        self.command(v)


# ─────────────────────────────────────────────────────────────────────────────
#  The application
# ─────────────────────────────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg = Config()
        fams = set(tkfont.families())
        self.ff = next((f for f in ("Roboto", "Google Sans", "Segoe UI Variable Text", "Segoe UI", "SF Pro Text",
                                    "Helvetica Neue", "Ubuntu", "Cantarell", "DejaVu Sans") if f in fams), "Arial")
        try:                                   # 1.0 normally, 1.25 / 1.5 ... on scaled Windows displays
            self.sc = max(0.75, float(self._get_window_scaling()))
        except Exception:
            self.sc = 1.0
        sw, sh = self.winfo_screenwidth() / self.sc, self.winfo_screenheight() / self.sc
        self.geometry(f"{int(min(1140, sw * 0.94))}x{int(min(760, sh * 0.88))}")   # never taller than the screen
        self.minsize(int(min(860, sw * 0.9)), int(min(600, sh * 0.8)))
        self.title(APP_NAME)

        self.ui_q = queue.Queue()
        self.work_q = queue.Queue()
        self.lock = threading.Lock()
        self.match_sem = threading.Semaphore(2)     # be gentle: only 2 YouTube searches at a time
        self.cookie_lock = threading.Lock()
        self.cookie_cache = {}                       # browser name -> path of exported cookies.txt (or None)
        self.workers = 0
        self.jobs = {}
        self.job_order = []
        self.batch_jobs = []
        self.batch_ok = 0
        self.preview_items = []
        self.preview_meta = {}
        self.pv_thumb_data = None
        self.url_text = ""
        self.page = "download"
        self._stacked = None
        self._snack_job = None
        self.history = self._load_history()
        self._h_n, self._h_map, self._hist_job, self._badge_txt = 0, {}, None, None
        self.ffmpeg_dir, self.ffmpeg_ok = None, False
        self.ffmpeg_ready = threading.Event()
        threading.Thread(target=self._prep_ffmpeg, daemon=True).start()
        try:
            self.last_clip = self.clipboard_get().strip()
        except Exception:
            self.last_clip = ""

        self.build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Control-Return>", lambda e: self.fab_action())
        for i, k in enumerate(("download", "queue", "history", "settings"), 1):
            self.bind(f"<Control-Key-{i}>", lambda e, k=k: self.show_page(k))
        self.after(120, self.pump)
        self.after(1500, self.watch_clipboard)

    # ── infrastructure ───────────────────────────────────────────────────────
    def report_callback_exception(self, exc, val, tb):
        log.error("Tk callback exception\n%s", "".join(traceback.format_exception(exc, val, tb)))
        try:
            self.toast("Something went wrong - details saved to the log", "Open log", lambda: open_path(LOG_FILE), 9000)
        except Exception:
            pass

    def _prep_ffmpeg(self):
        self.ffmpeg_dir, self.ffmpeg_ok = find_ffmpeg()
        log.info("ffmpeg dir=%s ok=%s", self.ffmpeg_dir, self.ffmpeg_ok)
        self.ffmpeg_ready.set()

    def _load_history(self):
        try:
            return json.loads((DATA_DIR / "history.json").read_text("utf-8"))
        except Exception:
            return []

    def _save_history(self, now=False):
        """Writing 500 rows after every finished track is slow on big playlists - batch the writes."""
        if not now:
            if not self._hist_job:
                self._hist_job = self.after(2000, self._save_history, True)
            return
        self._hist_job = None
        try:
            (DATA_DIR / "history.json").write_text(json.dumps(self.history[:500], indent=1), "utf-8")
        except Exception:
            pass

    def F(self, size=13, weight="normal"):
        return ctk.CTkFont(family=self.ff, size=size, weight=weight)

    # ── widget factories ─────────────────────────────────────────────────────
    def autowrap(self, label, host, pad=40, maxw=None):
        """Keep a label's wraplength in step with its container's width."""
        def fit(_e=None):
            try:
                w = host.winfo_width()
                if w <= 1:
                    return
                wl = max(120, int((w - pad) / self.sc))       # CTk scales wraplength itself
                if maxw:
                    wl = min(wl, maxw)
                if getattr(label, "_wl", None) != wl:
                    label._wl = wl
                    label.configure(wraplength=wl)
            except Exception:
                pass
        host.bind("<Configure>", fit, add="+")
        self.after(80, fit)

    def mk_card(self, parent, **kw):
        return ctk.CTkFrame(parent, corner_radius=26, fg_color=self.P["card"], **kw)

    def mk_lbl(self, parent, text, size=13, weight="normal", color=None, **kw):
        return ctk.CTkLabel(parent, text=text, font=self.F(size, weight), text_color=color or self.P["text"], **kw)

    def mk_btn(self, parent, text, cmd, kind="filled", **kw):
        P = self.P
        styles = {
            "filled": dict(fg_color=P["primary"], hover_color=P["primary_hover"], text_color=P["on_primary"]),
            "tonal": dict(fg_color=P["container"], hover_color=P["container_hover"], text_color=P["on_container"]),
            "text": dict(fg_color="transparent", hover_color=P["high"], text_color=P["primary"]),
            "outline": dict(fg_color="transparent", hover_color=P["high"], text_color=P["primary"],
                            border_width=1, border_color=P["outline"]),
        }
        s = dict(styles[kind])
        s.update(kw)
        height = s.pop("height", 40)
        radius = s.pop("corner_radius", 20)
        return ctk.CTkButton(parent, text=text, command=cmd, height=height, corner_radius=radius,
                             font=self.F(13, "bold"), **s)

    def mk_menu(self, parent, values, current, cmd):
        P = self.P
        m = ctk.CTkOptionMenu(parent, values=values, command=cmd, height=38, corner_radius=16, font=self.F(13),
                              dropdown_font=self.F(13), fg_color=P["high"], button_color=P["highest"],
                              button_hover_color=P["outline_var"], text_color=P["text"],
                              dropdown_fg_color=P["high"], dropdown_text_color=P["text"],
                              dropdown_hover_color=P["container"], anchor="w")
        m.set(current if current in values else values[0])
        return m

    def mk_switch(self, parent, text, key, after=None):
        P = self.P
        sw = ctk.CTkSwitch(parent, text=text, font=self.F(13), text_color=P["text"], progress_color=P["primary"],
                           fg_color=P["highest"], button_color=P["outline"], button_hover_color=P["text2"],
                           switch_width=44, switch_height=22)
        if self.cfg[key]:
            sw.select()

        def cb():
            self.cfg[key] = bool(sw.get())
            self.cfg.save()
            if after:
                after()
        sw.configure(command=cb)
        return sw

    def mk_entry(self, parent, key, placeholder="", width=220, show=None):
        P = self.P
        var = tk.StringVar(value=str(self.cfg[key]))

        def w(*_):
            self.cfg[key] = var.get()
            self.cfg.save()
        var.trace_add("write", w)
        e = ctk.CTkEntry(parent, textvariable=var, placeholder_text=placeholder, height=38, corner_radius=16,
                         fg_color=P["bg"], border_color=P["outline_var"], border_width=1, text_color=P["text"],
                         font=self.F(13), width=width, **({"show": show} if show else {}))
        e.tf_var = var
        return e

    def style_tree(self):
        P = self.P
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Tune.Treeview", background=P["card"], fieldbackground=P["card"], foreground=P["text"],
                    rowheight=int(34 * self.sc), borderwidth=0, relief="flat", font=(self.ff, 11))
        s.configure("Tune.Treeview.Heading", background=P["high"], foreground=P["text2"], relief="flat",
                    font=(self.ff, 10, "bold"), borderwidth=0, padding=(8, 8))
        s.map("Tune.Treeview", background=[("selected", P["container"])], foreground=[("selected", P["on_container"])])
        s.map("Tune.Treeview.Heading", background=[("active", P["highest"])])
        s.layout("Tune.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    def mk_tree(self, parent, cols, heads, widths, stretch_col, narrow=(), **kw):
        """narrow = ((frame_width, (column, ...)), ...): those columns hide when the table gets narrower."""
        P = self.P
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        t = ttk.Treeview(frame, columns=cols, show="headings", style="Tune.Treeview", **kw)
        for c, h, w in zip(cols, heads, widths):
            t.heading(c, text=h, anchor="w")
            t.column(c, width=w, minwidth=120 if c == stretch_col else 30, anchor="w", stretch=(c == stretch_col))
        sb = ctk.CTkScrollbar(frame, command=t.yview, button_color=P["highest"], button_hover_color=P["outline"])
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        t.tag_configure("done", foreground=P["ok"])
        t.tag_configure("error", foreground=P["error"])
        t.tag_configure("muted", foreground=P["outline"])
        if narrow:
            seen = {"key": None}

            def fit(e):
                hide = set()
                for thr, names in narrow:
                    if e.width < thr * self.sc:
                        hide.update(names)
                key = tuple(sorted(hide))
                if key != seen["key"]:
                    seen["key"] = key
                    t.configure(displaycolumns=[c for c in cols if c not in hide])
            frame.bind("<Configure>", fit, add="+")
        return frame, t

    # ── UI construction ──────────────────────────────────────────────────────
    def build_ui(self):
        if hasattr(self, "shell"):
            try:
                self.shell.destroy()
            except Exception:
                pass
        self.P = P = make_palette(self.cfg["theme"], self.cfg["accent"])
        ctk.set_appearance_mode("dark" if self.cfg["theme"] == "Dark" else "light")
        self.configure(fg_color=P["bg"])
        self.style_tree()
        self._stacked = None
        self._badge_txt = None
        self.shell = ctk.CTkFrame(self, fg_color=P["bg"], corner_radius=0)
        self.shell.pack(fill="both", expand=True)
        self.shell.grid_rowconfigure(1, weight=1)
        self.shell.grid_columnconfigure(1, weight=1)
        self.build_appbar()
        self.build_rail()
        self.body = ctk.CTkFrame(self.shell, fg_color=P["bg"], corner_radius=0)
        self.body.grid(row=1, column=1, sticky="nsew", padx=(0, 16), pady=(0, 16))
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        self.pages = {
            "download": self.build_download_page(self.body),
            "queue": self.build_queue_page(self.body),
            "history": self.build_history_page(self.body),
            "settings": self.build_settings_page(self.body),
        }
        for p in self.pages.values():
            p.grid(row=0, column=0, sticky="nsew")

        self.fab = ctk.CTkButton(self.body, text="⬇   Download", height=56, corner_radius=18, font=self.F(15, "bold"),
                                 fg_color=P["container"], hover_color=P["container_hover"],
                                 text_color=P["on_container"], command=self.fab_action)
        self.snack = ctk.CTkFrame(self.body, corner_radius=12, fg_color=P["text"])
        self.snack_lbl = ctk.CTkLabel(self.snack, text="", font=self.F(13), text_color=P["bg"])
        self.snack_lbl.pack(side="left", padx=(18, 10), pady=14)
        self.snack_btn = ctk.CTkButton(self.snack, text="", width=10, height=32, corner_radius=16,
                                       fg_color="transparent", hover_color=P["outline"],
                                       text_color=P["inv_primary"], font=self.F(13, "bold"))
        self._snack_job = None

        self.render_preview()
        for jid in self.job_order:
            self.update_job_row(jid)
        self.update_queue_summary()
        self.show_page(self.page)

    def build_appbar(self):
        P = self.P
        sc = self.sc
        bar = tk.Canvas(self.shell, height=int(72 * sc), bg=P["bg"], highlightthickness=0)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.bar = bar
        h = datetime.now().hour
        greet = "Good morning" if h < 12 else "Good afternoon" if h < 18 else "Good evening"
        bar.create_text(int(28 * sc), int(27 * sc), text=APP_NAME, anchor="w", fill=P["text"], font=(self.ff, 21, "bold"))
        bar.create_text(int(28 * sc), int(52 * sc), text=f"{greet}. Paste a link, get the music.", anchor="w", fill=P["text2"],
                        font=(self.ff, 10))
        icon = "☀" if self.cfg["theme"] == "Dark" else "☾"
        self.mk_btn(bar, icon, self.toggle_theme, "tonal", width=46, height=46, corner_radius=23).place(
            relx=1, x=-int(22 * sc), rely=0.5, anchor="e")

    def build_rail(self):
        P = self.P
        rail = ctk.CTkFrame(self.shell, width=92, fg_color=P["bg"], corner_radius=0)
        rail.grid(row=1, column=0, sticky="ns", padx=(8, 6))
        self.nav = {}
        for key, icon, label in (("download", "⬇", "Download"), ("queue", "☰", "Queue"),
                                 ("history", "⟲", "History"), ("settings", "⚙", "Settings")):
            b = ctk.CTkButton(rail, text=f"{icon}\n{label}", width=78, height=66, corner_radius=18,
                              font=self.F(11, "bold"), fg_color="transparent", hover_color=P["high"],
                              text_color=P["text2"], command=lambda k=key: self.show_page(k))
            b.pack(pady=5, padx=6)
            self.nav[key] = (b, icon, label)

    def show_page(self, key):
        P = self.P
        self.page = key
        log.info("Show page: %s", key)
        self.pages[key].tkraise()
        for k, (b, icon, label) in self.nav.items():
            if k == key:
                b.configure(fg_color=P["container"], text_color=P["on_container"])
            else:
                b.configure(fg_color="transparent", text_color=P["text2"])
        if key == "download":
            self.fab.place(relx=1, rely=1, x=-6, y=-4, anchor="se")
            self.fab.lift()
        else:
            self.fab.place_forget()
        if self.snack.winfo_ismapped():
            self.snack.lift()

    def toggle_theme(self):
        self.cfg["theme"] = "Light" if self.cfg["theme"] == "Dark" else "Dark"
        self.cfg.save()
        self.after(40, self.rebuild)

    def rebuild(self):
        try:
            self.url_text = self.url_box.get("1.0", "end-1c")
        except Exception:
            pass
        self.build_ui()

    # ── Download page ────────────────────────────────────────────────────────
    def build_download_page(self, parent):
        P = self.P
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_rowconfigure(2, minsize=int(74 * self.sc))
        left_box = ctk.CTkFrame(page, fg_color="transparent")
        left = ctk.CTkScrollableFrame(left_box, fg_color="transparent", corner_radius=0,
                                      scrollbar_button_color=P["high"], scrollbar_button_hover_color=P["outline_var"])
        left.pack(fill="both", expand=True)
        right = self.mk_card(page)
        # the table asks for a big natural width; without this it starves the left column (text got clipped)
        left_box.pack_propagate(False)
        right.pack_propagate(False)
        self.dl_page, self.dl_left, self.dl_right = page, left_box, right
        page.bind("<Configure>", self.relayout_download)

        # Links card
        c1 = self.mk_card(left)
        c1.pack(fill="x", pady=(0, 12))
        self.mk_lbl(c1, "What do you want to grab?", 16, "bold").pack(anchor="w", padx=20, pady=(18, 2))
        d1 = self.mk_lbl(c1, "YouTube, YouTube Music or Spotify links, or just type a song name. One per line. "
                             "Spotify playlists also work from a CSV.", 12, color=P["text2"], wraplength=300,
                         justify="left")
        d1.pack(anchor="w", padx=20)
        self.autowrap(d1, c1, 40)
        self.url_box = ctk.CTkTextbox(c1, height=96, corner_radius=14, fg_color=P["bg"], border_width=1,
                                      border_color=P["outline_var"], text_color=P["text"], font=self.F(13), wrap="word")
        self.url_box.pack(fill="x", padx=20, pady=12)
        self.url_box.insert("1.0", self.url_text)
        row = ctk.CTkFrame(c1, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 8))
        self.mk_btn(row, "Paste", self.paste_links, "tonal", width=80).pack(side="left", padx=4)
        self.an_btn = self.mk_btn(row, "Analyze  ▸", lambda: self.analyze(False), "filled", width=120)
        self.an_btn.pack(side="left", padx=4)
        self.mk_btn(row, "Clear", self.clear_links, "text", width=70).pack(side="left", padx=4)
        self.mk_btn(c1, "Import list (CSV / TXT)...", self.import_list, "outline").pack(fill="x", padx=20, pady=(0, 18))

        # Format card
        c2 = self.mk_card(left)
        c2.pack(fill="x", pady=(0, 12))
        self.mk_lbl(c2, "Format & quality", 16, "bold").pack(anchor="w", padx=20, pady=(18, 8))
        inner = ctk.CTkFrame(c2, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=(0, 18))
        Chips(inner, self, ["Audio", "Video"], self.cfg["mode"].capitalize(), self.on_mode, cols=2).pack(fill="x")
        self.fmt_holder = ctk.CTkFrame(inner, fg_color="transparent")
        self.fmt_holder.pack(fill="x", pady=(8, 0))
        self.build_format_controls()

        # Extras card
        c3 = self.mk_card(left)
        c3.pack(fill="x", pady=(0, 12))
        self.mk_lbl(c3, "Tags & extras", 16, "bold").pack(anchor="w", padx=20, pady=(18, 8))
        for text, key in (("Embed cover art", "embed_cover"), ("Crop covers to a square (audio)", "square_cover"),
                          ("Write metadata tags", "embed_meta"), ("Smart tags (clean titles, Artist - Title)", "smart_tags"),
                          ("Album + track number from playlist", "playlist_album"),
                          ("Put playlists in their own folder", "playlist_folder"),
                          ("Number tracks in file names", "number_tracks"),
                          ("Create .m3u8 playlist file", "m3u"),
                          ("Skip already downloaded", "skip_existing"),
                          ("Remove sponsor / off-topic parts", "sponsorblock")):
            self.mk_switch(c3, text, key).pack(anchor="w", padx=22, pady=5)
        d3 = self.mk_lbl(c3, "Covers are embedded in MP3, M4A, OPUS, FLAC, OGG, MP4 and MKV. Other formats get the "
                             "cover saved as a .jpg next to the file.", 11, color=P["text2"], wraplength=300,
                         justify="left")
        d3.pack(anchor="w", padx=22, pady=(8, 18))
        self.autowrap(d3, c3, 44)

        # Preview card
        r = self.dl_right
        head = ctk.CTkFrame(r, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=(18, 8))
        self.pv_thumb = ctk.CTkLabel(head, text="♪", width=120, height=68, corner_radius=12, fg_color=P["high"],
                                     font=self.F(28), text_color=P["text2"])
        self.pv_thumb.pack(side="left")
        info = ctk.CTkFrame(head, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=14)
        self.pv_title = self.mk_lbl(info, "Nothing analyzed yet", 16, "bold", anchor="w", justify="left", wraplength=300)
        self.pv_title.pack(anchor="w")
        self.pv_sub = self.mk_lbl(info, "Paste a link and press Analyze to preview the tracks here.", 12,
                                  color=P["text2"], anchor="w", justify="left", wraplength=300)
        self.pv_sub.pack(anchor="w", pady=(2, 0))
        self.autowrap(self.pv_title, info, 4)
        self.autowrap(self.pv_sub, info, 4)

        tf, self.pv_tree = self.mk_tree(r, ("sel", "n", "title", "by", "dur"),
                                        ("☑", "#", "Title", "Artist / channel", "Time"),
                                        (42, 46, 260, 150, 64), "title", narrow=((500, ("by",)),),
                                        selectmode="extended")
        self.pv_tree.column("sel", anchor="center")
        tf.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.pv_tree.bind("<Button-1>", self.pv_click)
        self.pv_tree.bind("<space>", self.pv_space)

        bottom = ctk.CTkFrame(r, fg_color="transparent")
        bottom.pack(fill="x", padx=12, pady=(0, 14))
        self.mk_btn(bottom, "All", lambda: self.pv_set_all(True), "text", width=54).pack(side="left")
        self.mk_btn(bottom, "None", lambda: self.pv_set_all(False), "text", width=58).pack(side="left")
        self.mk_btn(bottom, "Invert", self.pv_invert, "text", width=64).pack(side="left")
        self.mk_btn(bottom, "Copy links", self.pv_copy, "text", width=92).pack(side="left")
        self.pv_count = self.mk_lbl(bottom, "", 12, color=P["text2"])
        self.pv_count.pack(side="right", padx=10)
        return page

    def relayout_download(self, e):
        stacked = e.width < 940 * self.sc
        if stacked == self._stacked:
            return
        self._stacked = stacked
        page, sc = self.dl_page, self.sc
        if stacked:
            page.grid_columnconfigure(0, weight=1, minsize=0)
            page.grid_columnconfigure(1, weight=0, minsize=0)
            page.grid_rowconfigure(0, weight=3, minsize=int(240 * sc))
            page.grid_rowconfigure(1, weight=2, minsize=int(180 * sc))
            self.dl_left.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 8))
            self.dl_right.grid(row=1, column=0, sticky="nsew", padx=0, pady=(8, 0))
        else:
            page.grid_columnconfigure(0, weight=2, minsize=int(390 * sc))
            page.grid_columnconfigure(1, weight=3, minsize=int(520 * sc))
            page.grid_rowconfigure(0, weight=1, minsize=0)
            page.grid_rowconfigure(1, weight=0, minsize=0)
            self.dl_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
            self.dl_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)

    def build_format_controls(self):
        for w in self.fmt_holder.winfo_children():
            w.destroy()
        P = self.P
        audio = self.cfg["mode"] == "audio"
        vals = list(AUDIO_FORMATS) if audio else VIDEO_FORMATS
        key = "audio_fmt" if audio else "video_fmt"
        if self.cfg[key] not in vals:
            self.cfg[key] = vals[0]
        Chips(self.fmt_holder, self, vals, self.cfg[key], self.on_fmt, cols=4).pack(fill="x")
        self.mk_lbl(self.fmt_holder, "Quality", 12, color=P["text2"]).pack(anchor="w", pady=(10, 2), padx=4)
        if audio:
            if self.cfg["audio_fmt"] in LOSSY:
                vals_q, cur = AUDIO_Q, self.cfg["audio_q"]
            else:
                vals_q, cur = ["Lossless / original"], "Lossless / original"
        else:
            vals_q, cur = list(VIDEO_RES), self.cfg["video_res"]
        m = self.mk_menu(self.fmt_holder, vals_q, cur, self.on_quality)
        m.pack(fill="x", padx=4)
        if len(vals_q) == 1:
            m.configure(state="disabled")

    def on_mode(self, v):
        self.cfg["mode"] = v.lower()
        self.cfg.save()
        self.after(10, self.build_format_controls)

    def on_fmt(self, v):
        self.cfg["audio_fmt" if self.cfg["mode"] == "audio" else "video_fmt"] = v
        self.cfg.save()
        self.after(10, self.build_format_controls)

    def on_quality(self, v):
        if self.cfg["mode"] == "audio":
            if self.cfg["audio_fmt"] in LOSSY:
                self.cfg["audio_q"] = v
        else:
            self.cfg["video_res"] = v
        self.cfg.save()

    def paste_links(self):
        try:
            txt = self.clipboard_get().strip()
        except Exception:
            self.toast("Clipboard is empty")
            return
        cur = self.url_box.get("1.0", "end-1c")
        self.url_box.insert("end", ("\n" if cur.strip() else "") + txt)
        if LINK_RE.match(txt):
            self.last_clip = txt

    def import_list(self):
        paths = filedialog.askopenfilenames(title="Import track lists (Exportify CSV, text file...)",
                                            filetypes=[("Track lists", "*.csv *.tsv *.txt"), ("All files", "*.*")])
        if paths:
            self.load_lists(list(paths))

    def load_lists(self, paths):
        items, urls, dupes, names, errs = [], [], 0, [], []
        for path in paths:
            try:
                its, us, dp, nm = items_from_list_file(path)
            except Exception as e:
                log.exception("Import failed for %s", path)
                errs.append(f"{Path(path).name}: {clean_err(e)[:100]}")
                continue
            items += its
            urls += us
            dupes += dp
            names += nm
        if urls:                                    # links found inside a text file go through Analyze
            cur = self.url_box.get("1.0", "end-1c")
            self.url_box.insert("end", ("\n" if cur.strip() else "") + "\n".join(urls))
        if not items:
            if urls:
                self.toast(f"Added {len(urls)} link{'s' if len(urls) != 1 else ''} - press Analyze")
                self.analyze(False)
            else:
                self.toast("Couldn't import: " + errs[0] if errs else "No tracks found in that file", ms=7000)
            return
        total = sum(i["duration"] or 0 for i in items)
        title = names[0] if len(names) == 1 else f"{len(names)} playlists" if len(names) > 1 else "Imported list"
        self.preview_items = items
        self.preview_meta = dict(title=title, sub=" · ".join(
            x for x in (f"{len(items)} track{'s' if len(items) != 1 else ''}", fmt_dur(total) if total else "",
                        "imported list") if x))
        self.pv_thumb_data = None
        self.pv_thumb.configure(image=None, text="♪")
        self.render_preview()
        msg = f"Imported {len(items)} tracks - they'll be matched on YouTube when downloading"
        if dupes:
            msg += f" ({dupes} duplicate{'s' if dupes != 1 else ''} skipped)"
        if errs:
            msg += f". Couldn't read: {errs[0]}"
        elif urls:
            msg += f". {len(urls)} link{'s' if len(urls) != 1 else ''} in the file - press Analyze for those"
        self.toast(msg, ms=8000)

    def clear_links(self):
        self.url_box.delete("1.0", "end")
        self.preview_items, self.preview_meta, self.pv_thumb_data = [], {}, None
        self.pv_thumb.configure(image=None, text="♪")
        self.render_preview()

    # ── analyze ──────────────────────────────────────────────────────────────
    def get_cookiefile(self, browser):
        """Export a browser's cookies to a cookies.txt ONCE and reuse that file.

        Re-reading the live browser's cookie DB (cookiesfrombrowser) on every
        single search/download call is what was causing the repeated
        'Could not copy Chrome cookie database' PermissionError: Chrome/Edge
        keep an exclusive OS-level lock on Network/Cookies while the browser
        process is running, so most copy attempts fail unless the browser
        happens to be closed at that exact instant. Exporting once to a plain
        cookies.txt sidesteps the lock entirely and is also far faster.
        """
        if browser == "none":
            return None
        with self.cookie_lock:
            if browser in self.cookie_cache:
                return self.cookie_cache[browser]
            path = str(DATA_DIR / f"cookies_{browser}.txt")
            try:
                with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                                       "cookiesfrombrowser": (browser,),
                                       "cookiefile": path}) as ydl:
                    ydl.cookiejar.save(path, ignore_discard=True, ignore_expires=True)
                log.info("Exported %s cookies -> %s", browser, path)
                self.cookie_cache[browser] = path
            except Exception as e:
                log.warning("Could not export cookies from %s (close the browser and retry, "
                            "or use a cookies.txt file instead): %s", browser, clean_err(e))
                self.cookie_cache[browser] = None    # remember the failure, don't retry every job
            return self.cookie_cache[browser]

    def net_opts(self, o):
        d = {
            # 'web' needs a JS runtime to solve YouTube's signature/'n' challenge
            # (that's the "Signature solving failed" / EJS warning in the log).
            # android/ios/tv_embedded formats don't need that solving step, so
            # listing them first lets yt-dlp fall back to a working client
            # instead of hard-failing with "Requested format is not available".
            "extractor_args": {"youtube": {"player_client": ["android", "ios", "web", "tv"]}},
        }
        if str(o["proxy"]).strip():
            d["proxy"] = str(o["proxy"]).strip()
        if str(o["cookies_file"]).strip() and Path(str(o["cookies_file"]).strip()).exists():
            d["cookiefile"] = str(o["cookies_file"]).strip()
        elif o["cookies_browser"] != "none":
            cf = self.get_cookiefile(o["cookies_browser"])
            if cf:
                d["cookiefile"] = cf
        return d

    def analyze(self, auto=False):
        lines = [l.strip() for l in self.url_box.get("1.0", "end-1c").splitlines() if l.strip()]
        if not lines:
            self.toast("Paste a link or type a song name first")
            return
        self.an_btn.configure(state="disabled", text="Analyzing...")
        opts = self.cfg.snapshot()
        threading.Thread(target=self._analyze_worker, args=(lines, auto, opts), daemon=True).start()

    def _analyze_worker(self, lines, auto, o):
        items, errors, notes = [], [], []
        st = dict(first_info=None, sp_meta=None)
        pending, n_lines = list(lines), len(lines)
        ydl_opts = dict(quiet=True, no_warnings=True, extract_flat="in_playlist", skip_download=True,
                        logger=QuietLogger(), socket_timeout=20, noplaylist=bool(o["single_video"]))
        ydl_opts.update(self.net_opts(o))
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                while pending:
                    line = pending.pop(0)
                    fpath = line.strip("\"'")           # "Copy as path" in Explorer adds quotes
                    if not URL_RE.match(line) and fpath.lower().endswith(LIST_EXT) and Path(fpath).expanduser().is_file():
                        try:                            # a path to a CSV / TXT typed or pasted in the box
                            its, us, dp, _ = items_from_list_file(Path(fpath).expanduser())
                            items.extend(its)
                            pending.extend(us)
                            if dp:
                                notes.append(f"{dp} duplicate track{'s' if dp != 1 else ''} skipped.")
                            if not its and not us:
                                errors.append(f"No tracks found in {Path(fpath).name}")
                        except Exception as e:
                            log.exception("List import failed for %r", fpath)
                            errors.append(f"{Path(fpath).name}: " + clean_err(e)[:120])
                        continue
                    ref = spotify_ref(line)
                    if ref:
                        try:
                            res = spotify_fetch(ref, o)
                            n = len(res["tracks"])
                            pl = res["title"] if ref[0] != "track" else None
                            for i, t in enumerate(res["tracks"], 1):
                                if t.get("title"):
                                    items.append(make_sp_item(t, pl, i if pl else 0, n))
                            if pl:
                                st["sp_meta"] = dict(title=pl, owner=res.get("owner"), thumb=res.get("thumb"))
                            if res.get("api_error"):
                                notes.append("Spotify API keys didn't work here - used the public preview instead.")
                            if res.get("partial"):
                                notes.append(f"Spotify only shows the first {n} tracks without login. For the full list add "
                                             "API keys in Settings, or use Import list with an Exportify CSV.")
                        except Exception as e:
                            log.exception("Spotify fetch failed for %r", line)
                            errors.append("Spotify: " + clean_err(e)[:140])
                        continue
                    q = line if URL_RE.match(line) else f"ytsearch1:{line}"
                    if q.startswith("www."):
                        q = "https://" + q
                    try:
                        info = ydl.extract_info(q, download=False)
                        if st["first_info"] is None:
                            st["first_info"] = info
                        collect_items(info, items)
                    except Exception as e:
                        log.exception("Analyze failed for %r", q)
                        errors.append(clean_err(e)[:140])
        except Exception as e:
            log.exception("Analyze crashed")
            errors.append(clean_err(e)[:140])

        try:
            meta = self._analyze_meta(items, st["first_info"], st["sp_meta"], notes, n_lines)
        except Exception:                               # never leave the Analyze button stuck on "Analyzing..."
            log.exception("Building the preview summary failed")
            meta = dict(title=f"{len(items)} items", sub="") if items else {}
        self.ui_q.put(("analyzed", items, meta, errors, auto))
        if meta.get("thumb"):
            try:
                self.ui_q.put(("thumb", http_bytes(meta["thumb"], timeout=10)[0]))
            except Exception:
                pass

    @staticmethod
    def _analyze_meta(items, first_info, sp_meta, notes, n_lines):
        meta = {}
        if not items:
            return meta
        pls = {i["pl_title"] for i in items}
        if len(pls) == 1 and items[0]["pl_title"]:
            meta["title"] = items[0]["pl_title"]
        elif len(items) == 1:
            meta["title"] = items[0]["title"]
        else:
            meta["title"] = f"{len(items)} items"
        total = sum(i["duration"] or 0 for i in items)
        who = ""
        if first_info and first_info.get("_type") == "playlist":
            who = first_info.get("uploader") or first_info.get("channel") or ""
        elif items[0]["uploader"]:
            who = items[0]["uploader"]
        count = f"{len(items)} track{'s' if len(items) != 1 else ''}"
        meta["sub"] = " · ".join(x for x in (count, fmt_dur(total) if total else "", who) if x)
        thumb = None
        if first_info and first_info.get("thumbnails"):
            thumb = first_info["thumbnails"][-1].get("url")
        meta["thumb"] = thumb or items[0]["thumb"]
        origins = {i.get("origin") for i in items if i.get("sp")}
        if sp_meta and n_lines == 1:
            meta["title"] = sp_meta["title"] or meta["title"]
            meta["sub"] = " · ".join(x for x in (count, fmt_dur(total) if total else "", "Spotify",
                                                 sp_meta.get("owner") or "") if x)
            meta["thumb"] = sp_meta.get("thumb") or meta.get("thumb")
        elif "spotify" in origins:
            meta["sub"] += " · Spotify"
        elif "list" in origins:
            meta["sub"] += " · imported list"
        if notes:
            meta["note"] = "  ".join(dict.fromkeys(notes))
        return meta

    def on_analyzed(self, items, meta, errors, auto):
        self.an_btn.configure(state="normal", text="Analyze  ▸")
        self.preview_items, self.preview_meta = items, meta
        self.pv_thumb_data = None
        self.pv_thumb.configure(image=None, text="♪")
        self.render_preview()
        if errors:
            self.toast("Couldn't read: " + errors[0], ms=7000)
        elif not items:
            self.toast("Nothing found for that")
        elif meta.get("note"):
            self.toast(meta["note"], ms=10000)
        if auto and items:
            self.queue_selected()

    def set_thumb(self, data):
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
            w, h = img.size
            target = 120 / 68
            if w / h > target:
                nw = int(h * target)
                img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
            else:
                nh = int(w / target)
                img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
            img = img.resize((240, 136))
            self.pv_thumb_data = data
            self._pv_img = ctk.CTkImage(light_image=img, dark_image=img, size=(120, 68))
            self.pv_thumb.configure(image=self._pv_img, text="")
        except Exception:
            pass

    def render_preview(self):
        t = self.pv_tree
        t.delete(*t.get_children())
        for i, it in enumerate(self.preview_items):
            t.insert("", "end", iid=str(i), values=("☑" if it["checked"] else "☐", it["pl_index"] or i + 1,
                                                     it["title"], it["uploader"], fmt_dur(it["duration"])))
        if self.preview_items:
            self.pv_title.configure(text=self.preview_meta.get("title", ""))
            self.pv_sub.configure(text=self.preview_meta.get("sub", ""))
            if self.pv_thumb_data:
                self.set_thumb(self.pv_thumb_data)
        else:
            self.pv_title.configure(text="Nothing analyzed yet")
            self.pv_sub.configure(text="Paste a link and press Analyze to preview the tracks here.")
        self.update_pv_count()

    def update_pv_count(self):
        n = sum(1 for i in self.preview_items if i["checked"])
        self.pv_count.configure(text=f"{n} of {len(self.preview_items)} selected" if self.preview_items else "")

    def _pv_mark(self, idx):
        it = self.preview_items[idx]
        self.pv_tree.set(str(idx), "sel", "☑" if it["checked"] else "☐")

    def pv_click(self, e):
        t = self.pv_tree
        region = t.identify_region(e.x, e.y)
        col = t.identify_column(e.x)
        if region == "heading":
            if col == "#1":
                self.pv_set_all(not all(i["checked"] for i in self.preview_items))
            return
        row = t.identify_row(e.y)
        if row and col == "#1":
            i = int(row)
            self.preview_items[i]["checked"] = not self.preview_items[i]["checked"]
            self._pv_mark(i)
            self.update_pv_count()
            return "break"

    def pv_space(self, e):
        for row in self.pv_tree.selection():
            i = int(row)
            self.preview_items[i]["checked"] = not self.preview_items[i]["checked"]
            self._pv_mark(i)
        self.update_pv_count()
        return "break"

    def pv_set_all(self, val):
        for i, it in enumerate(self.preview_items):
            it["checked"] = val
            self._pv_mark(i)
        self.update_pv_count()

    def pv_invert(self):
        for i, it in enumerate(self.preview_items):
            it["checked"] = not it["checked"]
            self._pv_mark(i)
        self.update_pv_count()

    def pv_copy(self):
        urls = [i["url"] for i in self.preview_items if i["checked"] and i["url"]]
        if urls:
            self.clipboard_clear()
            self.clipboard_append("\n".join(urls))
            self.toast(f"Copied {len(urls)} link{'s' if len(urls) != 1 else ''}")

    # ── Queue page ───────────────────────────────────────────────────────────
    def build_queue_page(self, parent):
        P = self.P
        page = ctk.CTkFrame(parent, fg_color="transparent")
        top = self.mk_card(page)
        top.pack(fill="x", pady=(0, 12))
        self.q_summary = self.mk_lbl(top, "No downloads yet", 16, "bold")
        self.q_summary.pack(anchor="w", padx=20, pady=(18, 8))
        self.q_prog = ctk.CTkProgressBar(top, height=8, corner_radius=4, fg_color=P["highest"], progress_color=P["primary"])
        self.q_prog.pack(fill="x", padx=20)
        self.q_prog.set(0)
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(10, 14))
        self.mk_btn(row, "Cancel all", self.cancel_all, "tonal", width=100).pack(side="left", padx=4)
        self.mk_btn(row, "Retry failed", self.retry_failed, "tonal", width=110).pack(side="left", padx=4)
        self.mk_btn(row, "Clear finished", self.clear_finished, "text", width=120).pack(side="left", padx=4)
        self.mk_btn(row, "Open folder", lambda: self.open_out(), "text", width=110).pack(side="left", padx=4)

        lc = self.mk_card(page)
        lc.pack(fill="both", expand=True)
        tf, self.q_tree = self.mk_tree(lc, ("n", "title", "fmt", "status", "prog", "speed", "eta"),
                                       ("#", "Title", "Format", "Status", "Progress", "Speed", "ETA"),
                                       (40, 240, 120, 190, 235, 90, 60), "title",     # 235px fits a full progress bar
                                       narrow=((880, ("speed", "eta")), (700, ("fmt",))), selectmode="extended")
        tf.pack(fill="both", expand=True, padx=14, pady=14)
        self.q_tree.bind("<Double-1>", self.q_dbl)
        self.q_tree.bind("<Button-3>", self.q_menu)
        if IS_MAC:
            self.q_tree.bind("<Button-2>", self.q_menu)
        return page

    def q_dbl(self, e):
        row = self.q_tree.identify_row(e.y)
        job = self.jobs.get(row)
        if not job:
            return
        if job.status == "Error":
            messagebox.showinfo(APP_NAME, f"{job.title}\n\n{job.error}")
        elif job.status == "Done" and job.path:
            open_path(job.path)

    def q_menu(self, e):
        row = self.q_tree.identify_row(e.y)
        if row and row not in self.q_tree.selection():
            self.q_tree.selection_set(row)
        P = self.P
        m = tk.Menu(self, tearoff=0, bg=P["high"], fg=P["text"], activebackground=P["container"],
                    activeforeground=P["on_container"], bd=0, font=(self.ff, 10))
        m.add_command(label="Cancel", command=lambda: self.cancel_jobs(self.q_tree.selection()))
        m.add_command(label="Retry", command=lambda: self.retry_jobs(self.q_tree.selection()))
        m.add_command(label="Show in folder", command=self.q_show_in_folder)
        m.add_command(label="Remove from list", command=lambda: self.remove_jobs(self.q_tree.selection()))
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def q_show_in_folder(self):
        for jid in self.q_tree.selection():
            j = self.jobs.get(jid)
            if j and j.path:
                open_path(Path(j.path).parent)
                return
        self.open_out()

    def open_out(self):
        p = Path(self.cfg["out_dir"]).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        open_path(p)

    # ── History page ─────────────────────────────────────────────────────────
    def build_history_page(self, parent):
        P = self.P
        page = ctk.CTkFrame(parent, fg_color="transparent")
        top = self.mk_card(page)
        top.pack(fill="x", pady=(0, 12))
        self.h_stats = self.mk_lbl(top, "", 16, "bold")
        self.h_stats.pack(anchor="w", padx=20, pady=(18, 4))
        self.mk_lbl(top, "Double-click a row to play the file.", 12, color=P["text2"]).pack(anchor="w", padx=20)
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(8, 14))
        self.mk_btn(row, "Show in folder", self.h_folder, "tonal", width=130).pack(side="left", padx=4)
        self.mk_btn(row, "Clear history", self.h_clear, "text", width=120).pack(side="left", padx=4)
        lc = self.mk_card(page)
        lc.pack(fill="both", expand=True)
        tf, self.h_tree = self.mk_tree(lc, ("title", "fmt", "size", "when"),
                                       ("Title", "Format", "Size", "Downloaded"), (300, 120, 90, 150), "title",
                                       narrow=((520, ("size",)),), selectmode="browse")
        tf.pack(fill="both", expand=True, padx=14, pady=14)
        self.h_tree.bind("<Double-1>", lambda e: self.h_open())
        self.render_history()
        return page

    def render_history(self):
        t = self.h_tree
        t.delete(*t.get_children())
        self._h_map = {}
        for h in self.history:
            self._h_insert(h, "end")
        self._h_stats()

    def _h_insert(self, h, index):
        self._h_n += 1
        iid = f"h{self._h_n}"
        self._h_map[iid] = h
        self.h_tree.insert("", index, iid=iid, values=(h.get("title", ""), h.get("fmt", ""),
                                                       fmt_size(h.get("size", 0)), h.get("when", "")))

    def _h_stats(self):
        total = sum(h.get("size", 0) for h in self.history)
        self.h_stats.configure(text=f"{len(self.history)} download{'s' if len(self.history) != 1 else ''} · {fmt_size(total)}")

    def _h_sel(self):
        s = self.h_tree.selection()
        return self._h_map.get(s[0]) if s else None

    def h_open(self):
        h = self._h_sel()
        if h and Path(h.get("path") or "").is_file():
            open_path(h["path"])
        elif h:
            self.toast("That file has been moved or deleted")

    def h_folder(self):
        h = self._h_sel()
        if h and h.get("path"):
            open_path(Path(h["path"]).parent)
        else:
            self.open_out()

    def h_clear(self):
        if self.history and messagebox.askyesno(APP_NAME, "Clear the download history? (Files are not deleted.)"):
            self.history = []
            self._save_history(now=True)
            self.render_history()

    def add_history(self, job):
        try:
            size = os.path.getsize(job.path)
        except Exception:
            size = 0
        h = dict(title=job.title, path=job.path, fmt=job.label, size=size,
                 when=datetime.now().strftime("%Y-%m-%d %H:%M"), url=job.url)
        self.history.insert(0, h)
        del self.history[500:]
        self._save_history()
        self._h_insert(h, 0)
        kids = self.h_tree.get_children()
        for extra in kids[500:]:
            self.h_tree.delete(extra)
            self._h_map.pop(extra, None)
        self._h_stats()

    # ── Settings page ────────────────────────────────────────────────────────
    def build_settings_page(self, parent):
        P = self.P
        outer = ctk.CTkFrame(parent, fg_color="transparent")
        page = ctk.CTkScrollableFrame(outer, fg_color="transparent", corner_radius=0,
                                      scrollbar_button_color=P["high"], scrollbar_button_hover_color=P["outline_var"])
        page.pack(fill="both", expand=True)

        # Page header
        head = ctk.CTkFrame(page, fg_color="transparent")
        head.pack(fill="x", padx=2, pady=(2, 20))
        self.mk_lbl(head, "Settings", 26, "bold").pack(anchor="w")
        self.mk_lbl(head, "Appearance, downloads and matching - tuned your way.", 12,
                    color=P["text2"]).pack(anchor="w", pady=(2, 0))

        def section(icon, title, desc=None):
            """An expressive M3-style settings card: a tonal icon badge + title/subtitle header."""
            c = self.mk_card(page)
            c.pack(fill="x", pady=(0, 16))
            top = ctk.CTkFrame(c, fg_color="transparent")
            top.pack(fill="x", padx=20, pady=(20, 6 if desc else 12))
            badge = ctk.CTkLabel(top, text=icon, width=40, height=40, corner_radius=14, fg_color=P["container"],
                                 text_color=P["on_container"], font=self.F(17, "bold"))
            badge.pack(side="left", padx=(0, 14))
            tcol = ctk.CTkFrame(top, fg_color="transparent")
            tcol.pack(side="left", fill="x", expand=True)
            self.mk_lbl(tcol, title, 16, "bold").pack(anchor="w")
            if desc:
                self.mk_lbl(tcol, desc, 11, color=P["text2"]).pack(anchor="w", pady=(1, 0))
            return c

        def row(card, label, widget_fn):
            r = ctk.CTkFrame(card, fg_color="transparent")
            r.pack(fill="x", padx=20, pady=6)
            self.mk_lbl(r, label, 13, color=P["text2"], width=170, anchor="w").pack(side="left")
            w = widget_fn(r)
            w.pack(side="left", fill="x", expand=True)
            return w

        def caption(card, text):
            """A small tonal group label, for splitting a big section into sub-groups."""
            f = ctk.CTkFrame(card, fg_color="transparent")
            f.pack(fill="x", padx=20, pady=(12, 2))
            self.mk_lbl(f, text.upper(), 10, "bold", color=P["primary"]).pack(anchor="w")

        def note(card, text):
            d = self.mk_lbl(card, text, 11, color=P["text2"], wraplength=520, justify="left")
            d.pack(anchor="w", padx=22, pady=(6, 18))
            self.autowrap(d, card, 44)

        def end(card, pad=12):
            ctk.CTkFrame(card, height=pad, fg_color="transparent").pack()

        # ── Appearance ──────────────────────────────────────────────────────
        c = section("◐", "Appearance", "Theme and accent colour")
        r = ctk.CTkFrame(c, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=(0, 6))
        Chips(r, self, ["Dark", "Light"], self.cfg["theme"], self.set_theme, cols=2).pack(fill="x")
        self.mk_lbl(c, "Accent colour", 12, color=P["text2"]).pack(anchor="w", padx=22, pady=(10, 6))
        sw = ctk.CTkFrame(c, fg_color="transparent")
        sw.pack(anchor="w", padx=18, pady=(0, 20))
        for name, (dark, light) in ACCENTS.items():
            col = dark[0] if self.cfg["theme"] == "Dark" else light[0]
            sel = name == self.cfg["accent"]
            b = ctk.CTkButton(sw, text="", width=40, height=40, corner_radius=20 if sel else 14,
                              fg_color=col, hover_color=col, command=lambda n=name: self.set_accent(n))
            b.pack(side="left", padx=5)
            if sel:   # a glyph inside the button itself would make it wider than tall (CTk pads text by the radius)
                tick = ctk.CTkLabel(b, text="✓", width=20, height=20, fg_color="transparent", font=self.F(15, "bold"),
                                    text_color=dark[1] if self.cfg["theme"] == "Dark" else light[1])
                tick.place(relx=0.5, rely=0.5, anchor="center")
                tick.bind("<Button-1>", lambda e, n=name: self.set_accent(n))

        # ── Downloads ────────────────────────────────────────────────────────
        c = section("⬇", "Downloads", "Where files go and how fast")

        def outdir(p):
            f = ctk.CTkFrame(p, fg_color="transparent")
            e = self.mk_entry(f, "out_dir", width=260)
            e.pack(side="left", fill="x", expand=True)

            def browse():
                d = filedialog.askdirectory(initialdir=self.cfg["out_dir"])
                if d:
                    e.tf_var.set(d)
            self.mk_btn(f, "Browse", browse, "tonal", width=80).pack(side="left", padx=(8, 0))
            return f
        row(c, "Save to", outdir)
        row(c, "File name", lambda p: self.mk_menu(p, list(TEMPLATES), self.cfg["template"], self.set_template))

        def par(p):
            f = ctk.CTkFrame(p, fg_color="transparent")
            lab = self.mk_lbl(f, str(self.cfg["parallel"]), 13, "bold", width=24)

            def cmd(v):
                self.cfg["parallel"] = int(round(v))
                self.cfg.save()
                lab.configure(text=str(self.cfg["parallel"]))
                self.ensure_workers()
            s = ctk.CTkSlider(f, from_=1, to=4, number_of_steps=3, command=cmd, progress_color=P["primary"],
                              button_color=P["primary"], button_hover_color=P["primary_hover"], fg_color=P["highest"])
            s.set(self.cfg["parallel"])
            s.pack(side="left", fill="x", expand=True)
            lab.pack(side="left", padx=8)
            return f
        row(c, "Parallel downloads", par)
        row(c, "Speed limit (MB/s)", lambda p: self.mk_entry(p, "speed_limit", "unlimited", 140))
        end(c)

        # ── Behaviour ────────────────────────────────────────────────────────
        c = section("⚡", "Behaviour", "Notifications, files and playback extras")
        caption(c, "Notifications")
        for text, key in (("Play a sound when everything is done", "sound"),
                          ("Confetti when everything is done", "confetti")):
            self.mk_switch(c, text, key).pack(anchor="w", padx=22, pady=5)
        caption(c, "Files & tags")
        for text, key in (("Watch clipboard for YouTube links", "clipboard_watch"),
                          ("Keep the cover image as a separate file too", "keep_thumb"),
                          ("Download subtitles (video)", "subtitles"),
                          ("Links with video + list = single video only", "single_video")):
            self.mk_switch(c, text, key).pack(anchor="w", padx=22, pady=5)
        row(c, "Subtitle language", lambda p: self.mk_entry(p, "subs_lang", "en", 100))
        row(c, "When finished", lambda p: self.mk_menu(p, AFTER_ACTIONS, self.cfg["after_action"], self.set_after))
        end(c)

        # ── Spotify & matching ──────────────────────────────────────────────
        c = section("♫", "Spotify & matching", "How Spotify links get turned into YouTube audio")
        row(c, "Match songs on", lambda p: self.mk_menu(p, ["YouTube Music", "YouTube"], self.cfg["match_source"],
                                                        self.set_match_source))
        row(c, "Spotify Client ID", lambda p: self.mk_entry(p, "spotify_id", "optional", 260))
        row(c, "Spotify Client secret", lambda p: self.mk_entry(p, "spotify_secret", "optional", 260, show="•"))
        note(c, "Without keys, TuneFetch reads the public preview of a Spotify link (usually only the first "
               "50-100 tracks; private playlists don't work). For full playlists, add your own free developer "
               "app keys (Spotify currently asks for a Premium account to create one) or use Import list with an "
               "Exportify CSV.")

        # ── Account & network ───────────────────────────────────────────────
        c = section("⛨", "Account & network", "Cookies and proxy for restricted or private content")
        row(c, "Cookies from browser", lambda p: self.mk_menu(p, BROWSERS, self.cfg["cookies_browser"], self.set_browser))

        def cookiefile(p):
            f = ctk.CTkFrame(p, fg_color="transparent")
            e = self.mk_entry(f, "cookies_file", "cookies.txt (optional)", 220)
            e.pack(side="left", fill="x", expand=True)

            def browse():
                d = filedialog.askopenfilename(title="cookies.txt")
                if d:
                    e.tf_var.set(d)
            self.mk_btn(f, "Browse", browse, "tonal", width=80).pack(side="left", padx=(8, 0))
            return f
        row(c, "Cookies file", cookiefile)
        row(c, "Proxy", lambda p: self.mk_entry(p, "proxy", "http://host:port", 260))
        note(c, "Cookies help with age-restricted videos and private playlists (e.g. your own YouTube Music "
               "library). TuneFetch exports browser cookies to a file once and reuses it, so you don't need to "
               "keep the browser open.")

        # ── Advanced ─────────────────────────────────────────────────────────
        c = section("⚙", "Advanced", "Updates, logs and troubleshooting")
        try:
            ver = yt_dlp.version.__version__
        except Exception:
            ver = "?"
        self.ff_lbl = self.mk_lbl(c, "", 12, color=P["text2"])
        self.ff_lbl.pack(anchor="w", padx=22)
        self.mk_lbl(c, f"{APP_NAME} {APP_VERSION}   ·   yt-dlp {ver}", 12, color=P["text2"]).pack(anchor="w", padx=22, pady=(2, 12))
        r = ctk.CTkFrame(c, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=(0, 20))
        self.upd_btn = self.mk_btn(r, "Update yt-dlp", self.update_ytdlp, "tonal", width=130)
        self.upd_btn.pack(side="left", padx=4, pady=4)
        self.mk_btn(r, "Open log", lambda: open_path(LOG_FILE), "tonal", width=100).pack(side="left", padx=4, pady=4)
        self.mk_btn(r, "Copy log path", self.copy_log_path, "text", width=120).pack(side="left", padx=4, pady=4)
        self.mk_btn(r, "Open data folder", lambda: open_path(DATA_DIR), "text", width=140).pack(side="left", padx=4, pady=4)
        self.mk_btn(r, "Reset settings", self.reset_settings, "text", width=130).pack(side="left", padx=4, pady=4)
        self.after(300, self.refresh_ff_label)

        # ── About ────────────────────────────────────────────────────────────
        c = self.mk_card(page)
        c.pack(fill="x", pady=(0, 24))
        top = ctk.CTkFrame(c, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(24, 10))
        badge = ctk.CTkLabel(top, text="♪", width=56, height=56, corner_radius=20, fg_color=P["primary"],
                             text_color=P["on_primary"], font=self.F(24, "bold"))
        badge.pack(side="left", padx=(0, 16))
        tcol = ctk.CTkFrame(top, fg_color="transparent")
        tcol.pack(side="left", fill="x", expand=True)
        self.mk_lbl(tcol, APP_NAME, 20, "bold").pack(anchor="w")
        self.mk_lbl(tcol, f"Version {APP_VERSION}", 12, color=P["text2"]).pack(anchor="w", pady=(1, 0))

        d = self.mk_lbl(c, "Pull tracks and playlists off Spotify links (or a pasted list) and land clean, "
                           "tagged audio or video files - no account needed.", 12, color=P["text2"],
                           wraplength=520, justify="left")
        d.pack(anchor="w", padx=24, pady=(0, 16))
        self.autowrap(d, c, 48)

        credit = ctk.CTkFrame(c, corner_radius=16, fg_color=P["container"])
        credit.pack(fill="x", padx=24, pady=(0, 14))
        cr = ctk.CTkFrame(credit, fg_color="transparent")
        cr.pack(fill="x", padx=16, pady=12)
        self.mk_lbl(cr, "Made by", 11, color=P["on_container"]).pack(side="left")
        self.mk_lbl(cr, "qoij", 13, "bold", color=P["on_container"]).pack(side="left", padx=(6, 0))
        self.mk_lbl(cr, "♥", 12, color=P["on_container"]).pack(side="right")

        note(c, "Built with yt-dlp, FFmpeg and CustomTkinter. TuneFetch doesn't host or stream any media itself - "
               "please only download what you have the right to.")
        return outer

    def copy_log_path(self):
        self.clipboard_clear()
        self.clipboard_append(str(LOG_FILE))
        self.toast("Log path copied")

    def refresh_ff_label(self):
        try:
            if self.ffmpeg_ready.is_set():
                self.ff_lbl.configure(text="ffmpeg: ready ✓" if self.ffmpeg_ok else "ffmpeg: NOT found - audio conversion and covers won't work")
            else:
                self.after(400, self.refresh_ff_label)
        except Exception:
            pass

    def set_theme(self, v):
        self.cfg["theme"] = v
        self.cfg.save()
        self.after(40, self.rebuild)

    def set_accent(self, v):
        self.cfg["accent"] = v
        self.cfg.save()
        self.after(40, self.rebuild)

    def set_template(self, v):
        self.cfg["template"] = v
        self.cfg.save()

    def set_after(self, v):
        self.cfg["after_action"] = v
        self.cfg.save()

    def set_match_source(self, v):
        self.cfg["match_source"] = v
        self.cfg.save()

    def set_browser(self, v):
        self.cfg["cookies_browser"] = v
        self.cfg.save()

    def reset_settings(self):
        if messagebox.askyesno(APP_NAME, "Reset all settings to defaults?"):
            self.cfg.reset()
            self.after(40, self.rebuild)

    def update_ytdlp(self):
        self.upd_btn.configure(state="disabled", text="Updating...")

        def work():
            ok = self._pip_upgrade()
            self.ui_q.put(("toast", "yt-dlp updated - restart TuneFetch to use it" if ok else "Update failed (are you online?)", None, None, 7000))
            self.ui_q.put(("upd_done",))
        threading.Thread(target=work, daemon=True).start()

    @staticmethod
    def _pip_upgrade():
        base = [sys.executable, "-m", "pip", "install", "-U", "--disable-pip-version-check", "-q", "yt-dlp"]
        for extra in ([], ["--user"], ["--user", "--break-system-packages"]):
            try:
                if subprocess.run(base + extra, capture_output=True, creationflags=NO_WINDOW).returncode == 0:
                    return True
            except Exception:
                pass
        return False

    # ── snackbar / fun ───────────────────────────────────────────────────────
    def toast(self, text, action=None, cb=None, ms=5000):
        if self._snack_job:
            try:
                self.after_cancel(self._snack_job)
            except Exception:
                pass
        try:
            avail = max(220, int((self.body.winfo_width() - 300) / self.sc))
        except Exception:
            avail = 460
        self.snack_lbl.configure(text=text, wraplength=min(560, avail), justify="left")
        self.snack_btn.pack_forget()
        if action:
            self.snack_btn.configure(text=action, command=lambda: (self.hide_snack(), cb() if cb else None))
            self.snack_btn.pack(side="right", padx=(0, 8))
        self.snack.place(relx=0, x=4, rely=1, y=-20, anchor="sw")
        self.snack.lift()
        self._snack_job = self.after(ms, self.hide_snack)

    def hide_snack(self):
        try:
            self.snack.place_forget()
        except Exception:
            pass

    def confetti(self):
        if not self.cfg["confetti"]:
            return
        try:
            bar, P = self.bar, self.P
            w = max(bar.winfo_width(), 500)
            cols = [P["primary"], P["container"], "#FFD166", "#EF476F", "#06D6A0", "#118AB2"]
            parts = []
            for _ in range(100):
                x, y, s = random.uniform(0, w), random.uniform(-200, 0), random.uniform(4, 8)
                it = bar.create_rectangle(x, y, x + s, y + s * 1.6, fill=random.choice(cols), outline="")
                parts.append((it, random.uniform(-0.7, 0.7), random.uniform(1.8, 3.8)))

            def step(n=0):
                alive = False
                try:
                    for it, vx, vy in parts:
                        bar.move(it, vx, vy)
                        if bar.coords(it)[1] < 80 * self.sc:
                            alive = True
                except Exception:
                    return
                if alive and n < 160:
                    self.after(28, lambda: step(n + 1))
                else:
                    try:
                        for it, _, _ in parts:
                            bar.delete(it)
                    except Exception:
                        pass
            step()
        except Exception:
            pass

    def chime(self):
        try:
            if IS_WIN:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            elif IS_MAC:
                subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"])
            else:
                self.bell()
        except Exception:
            pass

    def watch_clipboard(self):
        try:
            if self.cfg["clipboard_watch"]:
                try:
                    txt = self.clipboard_get().strip()
                except Exception:
                    txt = ""
                if txt and txt != self.last_clip and LINK_RE.match(txt):
                    self.last_clip = txt
                    if txt not in self.url_box.get("1.0", "end-1c"):
                        kind = "Spotify" if "spotify" in txt.lower() else "YouTube"
                        self.toast(f"{kind} link copied", "Add it", lambda t=txt: self.add_link(t), 8000)
        finally:
            self.after(1500, self.watch_clipboard)

    def add_link(self, txt):
        cur = self.url_box.get("1.0", "end-1c")
        self.url_box.insert("end", ("\n" if cur.strip() else "") + txt)
        self.show_page("download")

    # ── queue / jobs ─────────────────────────────────────────────────────────
    def fab_action(self):
        if self.page != "download":
            return
        if self.preview_items and any(i["checked"] for i in self.preview_items):
            self.queue_selected()
        elif self.url_box.get("1.0", "end-1c").strip():
            self.analyze(auto=True)
        else:
            self.toast("Add a link or a song name first")

    def queue_selected(self):
        sel = [i for i in self.preview_items if i["checked"]]
        if not sel:
            self.toast("Nothing selected")
            return
        snap = self.cfg.snapshot()
        for it in sel:
            width = max(2, len(str(it["pl_count"] or 1)))
            job = Job(it, dict(snap), width)
            self.jobs[job.id] = job
            self.job_order.append(job.id)
            self.batch_jobs.append(job)
            self.update_job_row(job.id)
            self.work_q.put(job.id)
        self.preview_items, self.preview_meta, self.pv_thumb_data = [], {}, None
        self.pv_thumb.configure(image=None, text="♪")
        self.url_box.delete("1.0", "end")
        self.render_preview()
        self.ensure_workers()
        self.update_queue_summary()
        self.show_page("queue")
        self.toast(f"Added {len(sel)} to the queue")

    def ensure_workers(self):
        with self.lock:
            n = max(1, int(self.cfg["parallel"])) - self.workers
            for _ in range(max(0, min(n, self.work_q.qsize()))):
                self.workers += 1
                threading.Thread(target=self.worker_loop, daemon=True).start()

    def worker_loop(self):
        last = False
        while True:
            try:
                jid = self.work_q.get_nowait()
            except queue.Empty:
                with self.lock:
                    if self.work_q.empty():
                        self.workers -= 1
                        last = self.workers == 0
                        break
                continue
            job = self.jobs.get(jid)
            if job is None or job.status != "Queued" or job.cancel.is_set():
                continue
            self.run_job(job)
        if last:
            self.ui_q.put(("batch_done",))

    def build_opts(self, job):
        o = job.opts
        base = Path(o["out_dir"]).expanduser()
        if o["playlist_folder"] and job.pl_title:
            base = base / safe_name(job.pl_title)
        base.mkdir(parents=True, exist_ok=True)
        prefix = ""
        if o["number_tracks"] and job.pl_title and job.pl_index:
            prefix = f"{job.pl_index:0{job.pl_width}d} - "
        audio = o["mode"] == "audio"

        def hook(d):
            if job.cancel.is_set():
                raise Cancelled()
            st = d.get("status")
            n = max(1, len((d.get("info_dict") or {}).get("requested_formats") or ()))   # video + audio = 2 streams
            if st == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                done = d.get("downloaded_bytes") or 0
                if total:
                    job.pct = min(99.0, (job.fin + min(1.0, done / total)) / n * 100)
                job.speed, job.eta, job.status = d.get("speed"), d.get("eta"), "Downloading"
            elif st == "finished":
                job.fin += 1
                if job.fin >= n:
                    job.pct, job.status, job.speed, job.eta = 100.0, "Processing", None, None
                else:
                    job.pct = job.fin / n * 100
            self.ui_q.put(("job", job.id))

        names = {"ExtractAudio": "Converting audio", "Merger": "Merging streams", "MoveFiles": "Finishing",
                 "EmbedThumbnail": "Embedding cover", "Metadata": "Writing tags", "ModifyChapters": "Removing sponsors",
                 "SponsorBlock": "SponsorBlock", "ThumbnailsConvertor": "Preparing cover",
                 "EmbedSubtitle": "Embedding subtitles"}

        def pphook(d):
            if d.get("status") == "started":
                pp = d.get("postprocessor") or ""
                job.status = next((v for k, v in names.items() if k in pp), "Processing")
                job.pct = 100.0
                self.ui_q.put(("job", job.id))

        def posthook(path):
            job.path = path

        opts = {
            "quiet": True, "no_warnings": True, "noprogress": True, "logger": QuietLogger(),
            "noplaylist": True, "retries": 10, "fragment_retries": 10, "concurrent_fragment_downloads": 4,
            "progress_hooks": [hook], "postprocessor_hooks": [pphook], "post_hooks": [posthook],
            "paths": {"home": str(base)}, "outtmpl": prefix + TEMPLATES.get(o["template"], "%(title)s") + ".%(ext)s",
            "windowsfilenames": IS_WIN, "socket_timeout": 30,
        }
        if self.ffmpeg_dir:
            opts["ffmpeg_location"] = self.ffmpeg_dir
        opts.update(self.net_opts(o))
        try:
            if str(o["speed_limit"]).strip():
                opts["ratelimit"] = float(o["speed_limit"]) * 1024 * 1024
        except ValueError:
            pass
        if o["skip_existing"]:
            opts["download_archive"] = str(DATA_DIR / "archive.txt")

        pps, ppargs = [], {}
        sponsor_cats = ["sponsor", "selfpromo", "interaction"] + (["music_offtopic"] if audio else [])
        codec = None
        if audio:
            codec = AUDIO_FORMATS.get(o["audio_fmt"], "mp3")
            opts["format"] = "bestaudio[ext=m4a]/bestaudio/best" if codec == "best" else "bestaudio/best"
            if codec != "best":
                pp = {"key": "FFmpegExtractAudio", "preferredcodec": codec}
                if o["audio_fmt"] in LOSSY:
                    q = o["audio_q"]
                    if q != "Best":
                        pp["preferredquality"] = q.split()[0]
                    elif codec == "mp3":
                        pp["preferredquality"] = "0"
                pps.append(pp)
            container = codec
        else:
            h = VIDEO_RES.get(o["video_res"])
            opts["format"] = f"bv*[height<={h}]+ba/b[height<={h}]/bv*+ba/b" if h else "bv*+ba/b"
            vf = o["video_fmt"].lower()
            opts["merge_output_format"] = vf
            if vf == "mp4":
                opts["format_sort"] = ["res", "vcodec:h264", "acodec:aac", "ext:mp4:m4a"]
            elif vf == "webm":
                opts["format_sort"] = ["res", "vcodec:vp9", "acodec:opus"]
            container = vf
            if o["subtitles"]:
                lang = [s.strip() for s in str(o["subs_lang"] or "en").split(",") if s.strip()]
                opts.update(writesubtitles=True, writeautomaticsub=True, subtitleslangs=lang)
                pps.append({"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False})
        if o["sponsorblock"]:
            pps.insert(0, {"key": "SponsorBlock", "categories": sponsor_cats, "when": "after_filter"})
            pps.append({"key": "ModifyChapters", "remove_sponsor_segments": sponsor_cats})
        if o["embed_meta"]:
            pps.append({"key": "FFmpegMetadata", "add_chapters": True, "add_metadata": True})
        if o["embed_cover"]:
            opts["writethumbnail"] = True
            pps.append({"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"})
            if audio and o["square_cover"]:
                ppargs["thumbnailsconvertor+ffmpeg_o"] = ["-vf", "crop='min(iw,ih)':'min(iw,ih)'"]
            if container in COVER_EMBED_EXT:
                pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": bool(o["keep_thumb"])})
        opts["postprocessors"] = pps
        if ppargs:
            opts["postprocessor_args"] = ppargs
        return opts

    MIN_MATCH = 20      # below this the best YouTube result is probably a different song

    def _search_candidates(self, ydl, src, q, job):
        url = ("https://music.youtube.com/search?q=" + urllib.parse.quote_plus(q)) if src == "ytm" \
            else f"ytsearch6:{q}"
        info = None
        for attempt in (1, 2):                      # one retry for a hiccup / rate limit
            if job.cancel.is_set():
                raise Cancelled()
            try:
                info = ydl.extract_info(url, download=False)
                break
            except Exception:
                if attempt == 2:
                    log.warning("Match search via %s failed for %r", src, q, exc_info=True)
                else:
                    time.sleep(1.5)
        out = []
        for e in list((info or {}).get("entries") or [])[:8]:
            if not e:
                continue
            eu = e.get("url") or e.get("webpage_url") or e.get("id") or ""
            m = re.search(r"(?:[?&]v=|youtu\.be/|^)([\w-]{11})(?:[&?#]|$)", eu)
            if m:                                   # always download from the plain watch page
                out.append((e, f"https://www.youtube.com/watch?v={m.group(1)}"))
        return out

    def resolve_match(self, job):
        """Find the best YouTube Music / YouTube result for a Spotify or CSV track."""
        sp, o = job.sp, job.opts
        artist = sp.get("artist") or ""
        queries = [f"{artist} {sp['title']}".strip()]
        alt = f"{re.split(r'[,;]', artist)[0].strip()} {_core_title(sp['title'])}".strip()
        if alt.lower() != queries[0].lower():
            queries.append(alt)                     # simpler second attempt: first artist + clean title
        yopts = dict(quiet=True, no_warnings=True, extract_flat="in_playlist", skip_download=True,
                     logger=QuietLogger(job.id), socket_timeout=20)
        yopts.update(self.net_opts(o))
        order = ["ytm", "yt"] if o["match_source"] == "YouTube Music" else ["yt"]
        best, seen_dur = (-999.0, None), False
        with self.match_sem, yt_dlp.YoutubeDL(yopts) as ydl:
            for q in queries:
                good = False
                for src in order:
                    for e, eu in self._search_candidates(ydl, src, q, job):
                        if isinstance(e.get("duration"), (int, float)):
                            seen_dur = True
                        sc = score_match(sp, e) + (5 if src == "ytm" else 0)
                        log.debug("Match candidate [%s] %.0f  %s | %s", src, sc, e.get("title"), eu)
                        if sc > best[0]:
                            best = (sc, eu)
                    # with durations on both sides 60+ means a confident hit; without them ~40 is the ceiling
                    if best[1] and best[0] >= (60 if (seen_dur and sp.get("duration")) else 40):
                        good = True
                        break
                if good or (best[1] and best[0] >= self.MIN_MATCH):
                    break
        if not best[1] or best[0] < self.MIN_MATCH:
            raise RuntimeError(f"No confident YouTube match for '{queries[0]}'")
        log.info("Job %s matched '%s' -> %s (score %.0f)", job.id, queries[0], best[1], best[0])
        return best[1]

    def run_job(self, job):
        self.ffmpeg_ready.wait(60)
        job.status = "Starting"
        self.ui_q.put(("job", job.id))
        log.info("Job %s start: %s | %s | %s", job.id, job.title, job.url, job.label)
        try:
            if job.sp and not job.match_url:
                job.status = "Matching"
                self.ui_q.put(("job", job.id))
                job.match_url = self.resolve_match(job)
                job.status = "Starting"
                self.ui_q.put(("job", job.id))
            opts = self.build_opts(job)
            log.debug("Job %s options: %s", job.id, {k: v for k, v in opts.items()
                                                    if k not in ("progress_hooks", "postprocessor_hooks", "post_hooks", "logger")})
            opts["logger"] = QuietLogger(job.id)
            with yt_dlp.YoutubeDL(opts) as ydl:
                if job.sp or job.opts["smart_tags"] or job.opts["playlist_album"]:
                    try:
                        ydl.add_post_processor(SmartTags(ydl, job), when="pre_process")
                    except Exception:
                        pass
                ydl.download([job.match_url or job.url])
            if job.cancel.is_set():
                job.status = "Canceled"
            elif job.path:
                log.info("Job %s done: %s", job.id, job.path)
                job.status, job.pct = "Done", 100.0
                self.ui_q.put(("history", job))
            else:
                job.status, job.pct = "Skipped", 100.0
        except Cancelled:
            job.status = "Canceled"
        except Exception as e:
            if job.cancel.is_set():
                job.status = "Canceled"
            else:
                log.exception("Job %s failed", job.id)
                job.status, job.error = "Error", clean_err(e)
        job.speed = job.eta = None
        self.ui_q.put(("job", job.id))

    def cancel_jobs(self, ids):
        for jid in ids:
            j = self.jobs.get(jid)
            if not j or j.status in FINAL:
                continue
            j.cancel.set()
            if j.status == "Queued":
                j.status = "Canceled"
            self.update_job_row(jid)
        self.update_queue_summary()

    def cancel_all(self):
        self.cancel_jobs(list(self.jobs))

    def retry_jobs(self, ids):
        n = 0
        for jid in ids:
            j = self.jobs.get(jid)
            if j and j.status in ("Error", "Canceled"):
                j.cancel = threading.Event()
                j.status, j.pct, j.error, j.counted, j.path = "Queued", 0.0, "", False, None
                j.fin = 0
                self.batch_jobs.append(j)
                self.work_q.put(jid)
                self.update_job_row(jid)
                n += 1
        if n:
            self.ensure_workers()
        self.update_queue_summary()

    def retry_failed(self):
        self.retry_jobs([j for j, x in self.jobs.items() if x.status in ("Error", "Canceled")])

    def remove_jobs(self, ids):
        for jid in ids:
            j = self.jobs.get(jid)
            if j and j.status in FINAL:
                self.jobs.pop(jid, None)
                if jid in self.job_order:
                    self.job_order.remove(jid)
                try:
                    self.q_tree.delete(jid)
                except Exception:
                    pass
        self.update_queue_summary()

    def clear_finished(self):
        self.remove_jobs([j for j, x in self.jobs.items() if x.status in ("Done", "Skipped")])

    def update_job_row(self, jid):
        job, t = self.jobs.get(jid), getattr(self, "q_tree", None)
        if job is None or t is None:
            return
        st = job.status
        if st == "Error":
            st = "Failed: " + job.error[:70]
        vals = (job.no, job.title, job.label, st, bar_text(job.pct, job.status),
                fmt_speed(job.speed), fmt_eta(job.eta))
        tag = {"Done": "done", "Error": "error", "Canceled": "muted", "Skipped": "muted"}.get(job.status, "")
        try:
            if t.exists(jid):
                t.item(jid, values=vals, tags=(tag,))
            else:
                t.insert("", "end", iid=jid, values=vals, tags=(tag,))
        except tk.TclError:
            pass

    def update_queue_summary(self):
        js = list(self.jobs.values())
        total = len(js)
        if not total:
            self.q_summary.configure(text="No downloads yet")
            self.q_prog.set(0)
            self._set_nav_badge(0)
            return
        done = sum(1 for j in js if j.status in ("Done", "Skipped"))
        err = sum(1 for j in js if j.status == "Error")
        queued = sum(1 for j in js if j.status == "Queued")
        active = sum(1 for j in js if j.status not in FINAL and j.status != "Queued")
        prog = sum(100 if j.status in FINAL else j.pct for j in js) / (total * 100)
        parts = [f"{done}/{total} done"]
        if active:
            parts.append(f"{active} active")
        if queued:
            parts.append(f"{queued} waiting")
        if err:
            parts.append(f"{err} failed")
        self.q_summary.configure(text="  ·  ".join(parts))
        self.q_prog.set(min(1, prog))
        self._set_nav_badge(active + queued)
        self.title(f"{APP_NAME} - {active} downloading" if active else APP_NAME)

    def _set_nav_badge(self, n):
        b, icon, label = self.nav["queue"]
        txt = f"{icon}\n{label}" + (f" ({n})" if n else "")
        if txt != self._badge_txt:
            self._badge_txt = txt
            b.configure(text=txt)

    def flush_jobs(self, ids):
        for jid in ids:
            self.update_job_row(jid)
            j = self.jobs.get(jid)
            if j and j.status == "Done" and not j.counted:
                j.counted = True
                self.batch_ok += 1
        if ids:
            self.update_queue_summary()

    def write_playlists(self, jobs):
        groups, failed = {}, {}
        for j in jobs:
            if j.status == "Done" and j.path and j.pl_title and j.opts["m3u"]:
                groups.setdefault((j.pl_title, str(Path(j.path).parent)), []).append(j)
            elif j.status == "Error" and j.sp:
                failed.setdefault(j.pl_title or "Songs", []).append(j)
        for (name, folder), js in groups.items():
            js.sort(key=lambda j: j.pl_index or 0)
            lines = ["#EXTM3U"]
            for j in js:
                lines.append(f"#EXTINF:-1,{j.title}")
                lines.append(os.path.relpath(j.path, folder))
            try:
                Path(folder, safe_name(name) + ".m3u8").write_text("\n".join(lines), "utf-8")
            except Exception:
                pass
        for name, js in failed.items():             # same columns as Exportify, so it can be imported again
            try:
                first = js[0].opts
                folder = Path(first["out_dir"]).expanduser()
                if first["playlist_folder"] and js[0].pl_title:
                    folder = folder / safe_name(js[0].pl_title)
                folder.mkdir(parents=True, exist_ok=True)
                with open(folder / f"{safe_name(name)} - failed tracks.csv", "w", newline="", encoding="utf-8-sig") as f:
                    w = csv.writer(f)
                    w.writerow(["Track Name", "Artist Name(s)", "Album Name", "Duration (ms)", "Error"])
                    for j in sorted(js, key=lambda x: x.pl_index or 0):
                        w.writerow([j.sp["title"], j.sp.get("artist") or "", j.sp.get("album") or "",
                                    (j.sp.get("duration") or 0) * 1000 or "", j.error])
            except Exception:
                log.exception("Couldn't write the failed-tracks list")

    def on_batch_done(self):
        n, jobs = self.batch_ok, list({id(j): j for j in self.batch_jobs}.values())
        self.batch_ok, self.batch_jobs = 0, []
        self.title(APP_NAME)
        try:
            self.write_playlists(jobs)
        except Exception:
            log.exception("write_playlists failed")
        nfail = sum(1 for j in jobs if j.status == "Error")
        if n <= 0:
            if nfail:
                self.toast(f"{nfail} download{'s' if nfail != 1 else ''} failed - double-click a row in the Queue for details",
                           ms=8000)
            return
        if self.cfg["sound"]:
            self.chime()
        self.confetti()
        msg = f"All done - {n} file{'s' if n != 1 else ''} saved"
        if nfail:
            msg += f", {nfail} failed"
            if any(j.status == "Error" and j.sp for j in jobs):
                msg += " (listed in a CSV you can import again)"
        self.toast(msg, "Open folder", self.open_out, 9000)
        act = self.cfg["after_action"]
        if act == "Open folder":
            self.open_out()
        elif act == "Close app":
            self.after(1500, self.destroy)
        elif act == "Shut down PC":
            self.shutdown_prompt()

    def shutdown_prompt(self):
        if not messagebox.askyesno(APP_NAME, "All downloads are finished.\n\nShut down the computer in one minute?\n"
                                             "(Choose No to cancel.)"):
            return
        try:
            if IS_WIN:
                subprocess.Popen(["shutdown", "/s", "/t", "60"], creationflags=NO_WINDOW)
            elif IS_MAC:
                subprocess.Popen(["sh", "-c", "sleep 60; osascript -e 'tell app \"System Events\" to shut down'"])
            else:
                subprocess.Popen(["shutdown", "-h", "+1"])
        except Exception:
            pass

    # ── event pump (worker threads -> UI) ────────────────────────────────────
    def pump(self):
        dirty = set()
        try:
            for _ in range(600):
                try:
                    ev = self.ui_q.get_nowait()
                except queue.Empty:
                    break
                k = ev[0]
                if k == "job":
                    dirty.add(ev[1])
                elif k == "analyzed":
                    self.on_analyzed(*ev[1:])
                elif k == "thumb":
                    self.set_thumb(ev[1])
                elif k == "toast":
                    self.toast(*ev[1:])
                elif k == "history":
                    self.add_history(ev[1])
                elif k == "upd_done":
                    try:
                        self.upd_btn.configure(state="normal", text="Update yt-dlp")
                    except Exception:
                        pass
                elif k == "batch_done":
                    self.flush_jobs(dirty)
                    dirty.clear()
                    self.on_batch_done()
            self.flush_jobs(dirty)
        except Exception:
            log.exception("pump error")
        self.after(120, self.pump)

    def on_close(self):
        busy = [j for j in self.jobs.values() if j.status not in FINAL]
        if busy and not messagebox.askyesno(APP_NAME, "Downloads are still running. Quit anyway?"):
            return
        for j in self.jobs.values():
            j.cancel.set()
        self.cfg.save()
        self._save_history(now=True)
        self.destroy()


def main():
    try:
        App().mainloop()
        log.info("Exited normally")
    except BaseException as e:  # last-resort error box
        log.critical("FATAL\n%s", traceback.format_exc())
        try:
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror(APP_NAME, f"TuneFetch crashed:\n\n{e}\n\nA full log was saved to:\n{LOG_FILE}")
        except Exception:
            pass
        if not isinstance(e, (SystemExit, KeyboardInterrupt)):
            sys.exit(1)


if __name__ == "__main__":
    main()
