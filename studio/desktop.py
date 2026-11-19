"""Launch FramePilot inside a native desktop window with its local web server."""
import html
import importlib
import json
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


PORT = 8765
URL = f"http://127.0.0.1:{PORT}"
APP_DIR = "FramePilot"


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def _user_data() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / APP_DIR


def _prepare_environment() -> None:
    data = _user_data()
    data.mkdir(parents=True, exist_ok=True)
    storage = data / "storage.json"
    if not storage.exists():
        storage.write_text(json.dumps({"path": str(data / "data")}) + "\n", encoding="utf-8")

    os.environ["CLIPKONTRAST_HOST"] = "127.0.0.1"
    os.environ["CLIPKONTRAST_PORT"] = str(PORT)
    os.environ["CLIPKONTRAST_PUBLIC_URL"] = URL
    os.environ["CLIPKONTRAST_STORAGE_FILE"] = str(storage)
    os.environ["CLIPKONTRAST_ACCOUNTS"] = "0"
    os.environ["CLIPKONTRAST_UPDATE_CHECK"] = "0"
    os.environ["CLIPKONTRAST_REPO_URL"] = "https://github.com/salmanak20/FramePilot"
    os.environ["FRAMEPILOT_DESKTOP"] = "1"
    os.environ.setdefault("PYTHONWARNINGS", "ignore::DeprecationWarning")

    ffmpeg = _resource_root() / "ffmpeg" / "bin"
    if (ffmpeg / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")).is_file():
        os.environ["PATH"] = str(ffmpeg) + os.pathsep + os.environ.get("PATH", "")


def _is_listening() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
            return True
    except OSError:
        return False


def _is_framepilot_running() -> bool:
    try:
        with urllib.request.urlopen(URL + "/app", timeout=2) as response:
            return b"FramePilot" in response.read(65536)
    except (OSError, urllib.error.URLError):
        return False


def _error_window(webview, message: str) -> None:
    page = f"""<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
    <body style="margin:0;background:#111208;color:#f5f5ec;font:16px system-ui;padding:36px;max-width:680px">
    <h1 style="color:#c6f432">FramePilot couldn't start</h1><p>{html.escape(message)}</p>
    <p>Close this window and try again. Your saved projects and clips are kept in your user data folder.</p></body></html>"""
    webview.create_window("FramePilot", html=page, width=760, height=440, min_size=(560, 320))
    webview.start(debug=False)


def main() -> None:
    _prepare_environment()
    import webview

    app_server = None
    thread = None
    if not _is_framepilot_running():
        if _is_listening():
            _error_window(webview, f"Port {PORT} is already in use. Close the other program using it, then start FramePilot again.")
            return
        try:
            uvicorn = importlib.import_module("uvicorn")
            app = importlib.import_module("studio.server").app
            app_server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT,
                                                       log_level="error", access_log=False, proxy_headers=False))
            thread = threading.Thread(target=app_server.run, name="framepilot-server", daemon=True)
            thread.start()
            for _ in range(300):
                if _is_framepilot_running():
                    break
                if not thread.is_alive():
                    raise RuntimeError("The local server stopped before the window could open.")
                time.sleep(0.2)
            else:
                raise RuntimeError("The local server did not respond in time. Check that this computer has enough free disk space and memory.")
        except Exception as exc:
            if app_server:
                app_server.should_exit = True
            _error_window(webview, str(exc))
            return

    window = webview.create_window("FramePilot", URL + "/app", width=1440, height=920,
                                   min_size=(960, 640), background_color="#111208")
    if app_server:
        window.events.closed += lambda: setattr(app_server, "should_exit", True)
    webview.start(debug=False)
    if app_server and thread:
        app_server.should_exit = True
        thread.join(timeout=10)


if __name__ == "__main__":
    main()
