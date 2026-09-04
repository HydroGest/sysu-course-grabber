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

    if not args.no_open and args.host in ("127.0.0.1", "::1"):
        threading.Timer(0.6, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")).start()
    run_server(httpd)


if __name__ == "__main__":
    main()
