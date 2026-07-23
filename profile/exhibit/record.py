#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
展品录制器:无头 Chromium 逐帧渲染 scene.html → Pillow 合成动画 WebP。

    python3 profile/exhibit/record.py            # 输出 assets/exhibit.webp
    python3 profile/exhibit/record.py --probe 40 # 只截第 40 帧(调试用)

帧数/时长在 scene.html 里(FPS=20, T=10s → 200 帧,完美循环)。
需要环境变量 CHROME 指向 Chromium 可执行文件(缺省尝试常见路径)。
"""

from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCENE = Path(__file__).resolve().parent / "scene.html"
OUT = ROOT / "assets" / "exhibit.webp"
FPS, T = 20, 10
FRAMES = FPS * T
W, H = 1000, 440
PORT = 9377

CHROME_CANDIDATES = [
    os.environ.get("CHROME", ""),
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome",
]


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if c and Path(c).exists():
            return c
    sys.exit("找不到 Chromium,请设 CHROME=/path/to/chrome")


def main() -> None:
    import websocket  # pip install websocket-client

    probe = None
    if "--probe" in sys.argv:
        probe = int(sys.argv[sys.argv.index("--probe") + 1])

    proc = subprocess.Popen(
        [find_chrome(), "--headless=new", "--no-sandbox", "--disable-gpu-sandbox",
         "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--hide-scrollbars",
         "--remote-allow-origins=*", f"--remote-debugging-port={PORT}",
         f"--window-size={W},{H}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws_url = None
        for _ in range(80):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                page = [t for t in tabs if t["type"] == "page"]
                if page:
                    ws_url = page[0]["webSocketDebuggerUrl"]
                    break
            except Exception:
                pass
            time.sleep(0.25)
        assert ws_url, "no debug target"
        ws = websocket.create_connection(ws_url, timeout=60)
        ws.settimeout(60)
        mid = [0]

        def send(method, **params):
            mid[0] += 1
            ws.send(json.dumps({"id": mid[0], "method": method, "params": params}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == mid[0]:
                    if "error" in msg:
                        raise RuntimeError(msg["error"])
                    return msg.get("result", {})

        send("Emulation.setDeviceMetricsOverride", width=W, height=H,
             deviceScaleFactor=1, mobile=False)
        send("Page.enable")
        send("Page.navigate", url=SCENE.as_uri())
        time.sleep(2.5)  # 等 WebGL 初始化

        def grab(frame: int) -> bytes:
            r = send("Runtime.evaluate", expression=f"seek({frame})")
            assert r["result"]["value"] == f"f{frame}", r
            shot = send("Page.captureScreenshot", format="png")
            return base64.b64decode(shot["data"])

        if probe is not None:
            png = grab(probe)
            out = ROOT / f"exhibit-probe-{probe}.png"
            out.write_bytes(png)
            print(f"probe frame {probe} -> {out}")
            return

        from PIL import Image
        frames = []
        t0 = time.time()
        for i in range(FRAMES):
            frames.append(Image.open(io.BytesIO(grab(i))).convert("RGB"))
            if i % 20 == 0:
                print(f"frame {i}/{FRAMES} ({time.time() - t0:.0f}s)")
        ws.close()

        OUT.parent.mkdir(exist_ok=True)
        frames[0].save(OUT, save_all=True, append_images=frames[1:],
                       duration=int(1000 / FPS), loop=0,
                       format="WEBP", quality=80, method=6)
        print(f"wrote {OUT} · {OUT.stat().st_size / 1024:.0f} KB · {FRAMES} frames @ {FPS}fps")
    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()
