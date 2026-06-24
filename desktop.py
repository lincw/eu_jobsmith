"""桌面 App 啟動器：背景跑 FastAPI server，並用系統 WebView 開一個原生視窗。

雙擊即開、不必開終端機或另開瀏覽器；仍是在本機執行、用使用者自己的 Claude Code /
Codex CLI 訂閱（與 run.bat 相同的後端，差別只在改用原生視窗呈現）。

用法：desktop.bat（或 .venv\\Scripts\\python.exe desktop.py）。
需求：先建置前端（cd frontend && npm run build）；Windows 需有 WebView2 執行階段（Win11 內建）。
"""
from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path
from urllib.request import urlopen

import uvicorn
import webview

_ROOT = Path(__file__).parent
_TITLE = "JobCopilot — 台灣 AI 求職 Co-pilot"


def _pick_port(preferred: int = 8000) -> int:
    """優先用 8000；若被佔用（例如同時開了 run.bat）就找一個空閒埠，避免衝突。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2:
        s2.bind(("127.0.0.1", 0))
        return s2.getsockname()[1]


def _wait_until_up(url: str, server: uvicorn.Server, timeout: float = 30.0) -> bool:
    """等 server 起來（poll 首頁）；server 啟動失敗就提早返回 False。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if getattr(server, "started", False):
            try:
                with urlopen(url, timeout=1):
                    return True
            except Exception:
                pass
        time.sleep(0.2)
    return False


def main() -> int:
    dist_index = _ROOT / "frontend" / "dist" / "index.html"
    if not dist_index.exists():
        print("找不到前端建置產物（frontend/dist）。請先執行：")
        print("    cd frontend && npm run build")
        return 1

    port = _pick_port(8000)
    base = f"http://127.0.0.1:{port}"

    config = uvicorn.Config("app.server:app", host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    if not _wait_until_up(base, server):
        print("伺服器啟動逾時，請改用 run.bat 觀察錯誤訊息。")
        server.should_exit = True
        return 1

    # 開原生視窗；webview.start() 會阻塞直到視窗關閉。
    webview.create_window(_TITLE, base, width=1280, height=860, min_size=(960, 640))
    webview.start()

    # 視窗關閉 → 通知 server 收工。
    server.should_exit = True
    return 0


if __name__ == "__main__":
    sys.exit(main())
