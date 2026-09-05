"""SYSU 抢课助手入口。"""

import argparse
import os
import threading
import webbrowser
from pathlib import Path

from sycu_grabber import __version__
from sycu_grabber.server import create_httpd, run_server


def default_data_dir():
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return str(Path(local) / "SYSU-Course-Grabber")
    return str(Path.home() / ".sycu-grabber")


def create_tray_icon(port, httpd):
    """Create the tray icon or return None when pystray is unavailable."""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        return None

    image = Image.new("RGB", (64, 64), (11, 110, 79))
    draw = ImageDraw.Draw(image)
    draw.rectangle((18, 12, 46, 52), fill="white")
    draw.text((30, 27), "S", fill=(11, 110, 79))

    def open_panel(icon, item):
        webbrowser.open(f"http://127.0.0.1:{port}")

    def quit_app(icon, item):
        icon.stop()
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    icon = pystray.Icon(
        "SYSU-Course-Grabber",
        image,
        "SYSU 抢课助手",
        pystray.Menu(
            pystray.MenuItem("打开控制台", open_panel, default=True),
            pystray.MenuItem("退出", quit_app),
        ),
    )
    return icon


def main():
    ap = argparse.ArgumentParser(description="SYSU 抢课助手")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8124)
    ap.add_argument("--data-dir", default=default_data_dir())
    ap.add_argument("--no-open", action="store_true", help="启动后不自动打开浏览器")
    args = ap.parse_args()

    httpd = create_httpd(args.host, args.port, args.data_dir)
    print(f"SYSU 抢课助手 {__version__}")
    print(f"控制台: http://{args.host}:{args.port}")
    print(f"数据目录: {args.data_dir}")

    tray_icon = create_tray_icon(args.port, httpd)
    if tray_icon is None:
        print("未安装 pystray/Pillow，不显示系统托盘")

    if not args.no_open and args.host in ("127.0.0.1", "::1"):
        threading.Timer(0.6, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")).start()

    serve_thread = threading.Thread(target=run_server, args=(httpd,), daemon=True)
    serve_thread.start()
    if tray_icon is not None:
        tray_icon.run()
    else:
        serve_thread.join()


if __name__ == "__main__":
    main()
