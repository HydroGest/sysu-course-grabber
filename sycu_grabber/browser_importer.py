"""一键浏览器登录与 Cookie 导入。

Chromium 不允许普通程序静默安装解压扩展，所以这里提供一个替代方案：
启动 Edge/Chrome 的专用登录窗口，通过本地 DevTools 协议读取教务 Cookie。
用户仍然只输一次账号密码，不需要安装扩展或手工粘贴 Cookie。
"""

import base64
import json
import os
import random
import socket
import subprocess
import threading
import time
import urllib.request
from pathlib import Path


EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_browser():
    for path in EDGE_PATHS + CHROME_PATHS:
        if os.path.isfile(path):
            return path
    return None


def _http_json(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse_ws_url(url):
    # ws://127.0.0.1:9223/devtools/page/xxx
    rest = url.split("://", 1)[1]
    hostport, path = rest.split("/", 1)
    host, port = hostport.rsplit(":", 1)
    return host, int(port), "/" + path


def _recv_exact(sock, length):
    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise ConnectionError("websocket closed")
        data += chunk
    return data


def _ws_connect(ws_url, timeout=10):
    host, port, path = _parse_ws_url(ws_url)
    sock = socket.create_connection((host, port), timeout=timeout)
    key = base64.b64encode(os.urandom(16)).decode()
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    sock.sendall(request.encode("ascii"))
    response = b""
    while b"\r\n\r\n" not in response:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("websocket handshake failed")
        response += chunk
    if not response.startswith(b"HTTP/1.1 101"):
        raise ConnectionError(f"websocket handshake failed: {response[:120]!r}")
    return sock


def _send_ws(sock, message):
    payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
    header = bytearray([0x81])
    length = len(payload)
    if length <= 125:
        header.append(0x80 | length)
    elif length <= 65535:
        header.append(0x80 | 126)
        header.extend(length.to_bytes(2, "big"))
    else:
        header.append(0x80 | 127)
        header.extend(length.to_bytes(8, "big"))
    mask = os.urandom(4)
    header.extend(mask)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    sock.sendall(bytes(header) + masked)


def _send_pong(sock, payload=b""):
    header = bytearray([0x8A])
    length = len(payload)
    if length <= 125:
        header.append(0x80 | length)
    else:
        header.append(0x80 | 126)
        header.extend(length.to_bytes(2, "big"))
    mask = os.urandom(4)
    header.extend(mask)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    sock.sendall(bytes(header) + masked)


def _recv_ws(sock):
    first, second = _recv_exact(sock, 2)
    opcode = first & 0x0F
    fin = bool(first & 0x80)
    masked = bool(second & 0x80)
    length = second & 0x7F
    if length == 126:
        length = int.from_bytes(_recv_exact(sock, 2), "big")
    elif length == 127:
        length = int.from_bytes(_recv_exact(sock, 8), "big")
    mask = _recv_exact(sock, 4) if masked else None
    payload = _recv_exact(sock, length) if length else b""
    if mask:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return fin, opcode, payload


def _ws_call(sock, method, params=None, timeout=10):
    msg_id = random.randint(1, 1000000)
    message = {"id": msg_id, "method": method}
    if params is not None:
        message["params"] = params
    _send_ws(sock, message)
    sock.settimeout(timeout)
    partial = None
    while True:
        fin, opcode, payload = _recv_ws(sock)
        if opcode == 8:
            raise ConnectionError("websocket closed by remote")
        if opcode == 9:
            _send_pong(sock, payload)
            continue
        if opcode == 1:
            partial = payload
        elif opcode == 0 and partial is not None:
            partial += payload
        else:
            continue
        if fin and partial is not None:
            data = json.loads(partial.decode("utf-8"))
            if data.get("id") == msg_id:
                return data
            partial = None


class BrowserImporter:
    def __init__(self, data_dir, on_cookie):
        self.profile_dir = Path(data_dir) / "browser-profile"
        self.on_cookie = on_cookie
        self.port = None
        self.process = None
        self._stop = threading.Event()
        self._thread = None
        self.status = "idle"
        self.message = ""
        self.last_error = ""
        self.last_cookie_hash = ""

    def is_active(self):
        return self._thread is not None and self._thread.is_alive()

    def stop(self):
        self._stop.set()
        if self.process is not None and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass

    def snapshot(self):
        return {
            "status": self.status,
            "message": self.message,
            "error": self.last_error,
            "running": self.is_active(),
            "port": self.port,
        }

    @staticmethod
    def _free_port():
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def start_login(self):
        if self.is_active():
            return self.snapshot()
        browser = find_browser()
        if not browser:
            self.status = "error"
            self.last_error = "未找到 Edge 或 Chrome"
            return self.snapshot()
        self.port = self._free_port()
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            browser,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "https://jwxt.sysu.edu.cn/jwxt",
        ]
        self._stop.clear()
        self.last_error = ""
        self.last_cookie_hash = ""
        self.status = "starting"
        self.message = "正在启动浏览器"
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            self.status = "error"
            self.last_error = str(e)
            return self.snapshot()
        self._thread = threading.Thread(target=self._watch, name="browser-login", daemon=True)
        self._thread.start()
        return self.snapshot()

    def _devtools(self, path):
        return _http_json(f"http://127.0.0.1:{self.port}{path}", timeout=3)

    def _read_snapshot(self):
        targets = self._devtools("/json/list")
        pages = [t for t in targets if t.get("type") == "page"]
        candidate = None
        for page in pages:
            url = page.get("url") or ""
            if url.startswith("https://jwxt.sysu.edu.cn") and "/login" not in url.lower():
                candidate = page
                break
        if candidate is None:
            return None
        ws_url = candidate.get("webSocketDebuggerUrl")
        if not ws_url:
            return None
        sock = _ws_connect(ws_url)
        try:
            data = _ws_call(sock, "Network.getAllCookies")
        finally:
            sock.close()
        cookies = (data.get("result") or {}).get("cookies") or []
        keep = [
            c for c in cookies
            if "sysu.edu.cn" in str(c.get("domain") or "")
        ]
        if not keep:
            return None
        header = "; ".join(f"{c.get('name')}={c.get('value')}" for c in keep)
        return {"cookie": header, "url": candidate.get("url") or ""}

    def _watch(self):
        deadline = time.time() + 25
        while time.time() < deadline and not self._stop.is_set():
            try:
                self._devtools("/json/version")
                break
            except Exception:
                time.sleep(0.6)
        else:
            self.status = "error"
            self.last_error = "浏览器调试通道启动超时"
            return

        self.status = "waiting"
        self.message = "请在打开的窗口中登录教务系统"
        while not self._stop.is_set():
            if self.process is not None and self.process.poll() is not None:
                self.status = "closed"
                self.message = "登录窗口已关闭"
                return
            try:
                snapshot = self._read_snapshot()
            except Exception as e:
                self.last_error = str(e)
                time.sleep(1.2)
                continue
            if snapshot and snapshot.get("cookie"):
                cookie_hash = str(hash(snapshot["cookie"]))
                if cookie_hash != self.last_cookie_hash:
                    self.last_cookie_hash = cookie_hash
                    self.status = "captured"
                    self.message = "已捕获登录态，正在保存"
                    try:
                        self.on_cookie(snapshot["cookie"])
                        self.status = "ready"
                        self.message = "登录成功，Cookie 已保存"
                        if self.process is not None and self.process.poll() is None:
                            try:
                                self.process.terminate()
                            except Exception:
                                pass
                        return
                    except Exception as e:
                        self.last_error = str(e)
                        self.status = "error"
                        self.message = "Cookie 保存失败"
                        return
            time.sleep(1.5)


if __name__ == "__main__":
    # Simple integration check with an existing running instance is manual only.
    print(json.dumps({"browser": find_browser()}, ensure_ascii=False))
