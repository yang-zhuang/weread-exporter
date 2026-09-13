# -*- coding: utf-8 -*-
"""启动一个常驻 Chrome，开 CDP 调试端口供 weread-exporter 接管。

为什么需要它
------------
weread-exporter 默认模式下每次都自己 launch 一个浏览器，profile 用的是
tempfile.mkdtemp() 建的临时目录，再把 cookie 文件注进去。对微信读书来说
这就是「一台从没见过的设备，突然拿着你的身份把整本书从头翻到尾」——
这是它最大的风控隐患，跟用没用 CDP 无关。

固定 profile + 人工登录后，指纹和登录态都是真实且跨次稳定的。

用法
----
    python launch_chrome.py
    # 在弹出的窗口里扫码登录微信读书（只需一次，登录态存在配置目录里）
    python -m weread_exporter -b <book_id> --cdp-endpoint http://127.0.0.1:9222

安全提示
--------
调试端口没有任何鉴权，本机任何进程都能驱动这个浏览器。所以默认用独立的
profile 目录，不要指向你日常用的 profile。
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request

DEFAULT_PORT = 9222
DEFAULT_PROFILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "weread-profile"
)
WEREAD_URL = "https://weread.qq.com/"

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]


def find_chrome() -> str:
    for path in CHROME_CANDIDATES:
        if os.path.isfile(path):
            return path
    raise FileNotFoundError(
        "没找到 Chrome。请安装 Google Chrome，或者用 --chrome 指定可执行文件位置。"
    )


def port_in_use(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:%d/json/version" % port, timeout=2
        ) as rsp:
            info = json.loads(rsp.read().decode())
    except Exception:
        return False
    print("调试端口 %d 已经在用：%s" % (port, info.get("Browser", "unknown")))
    print("直接用 --cdp-endpoint http://127.0.0.1:%d 接管就行，不再重复启动。" % port)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="启动带 CDP 调试端口的 Chrome")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("WEREAD_CDP_PORT", DEFAULT_PORT)),
        help="调试端口，默认 9222",
    )
    parser.add_argument(
        "--profile-dir",
        default=os.environ.get("WEREAD_CHROME_PROFILE", DEFAULT_PROFILE),
        help="Chrome 配置目录，登录态保存在这里",
    )
    parser.add_argument("--chrome", help="Chrome 可执行文件路径")
    args = parser.parse_args()

    if port_in_use(args.port):
        return 0

    chrome = args.chrome or find_chrome()
    os.makedirs(args.profile_dir, exist_ok=True)

    subprocess.Popen(
        [
            chrome,
            "--remote-debugging-port=%d" % args.port,
            # Chrome 111+ 不放行 Origin 的话，CDP 的 websocket 握手会被 403 拒掉
            "--remote-allow-origins=*",
            "--user-data-dir=%s" % args.profile_dir,
            "--no-first-run",
            "--no-default-browser-check",
            WEREAD_URL,
        ]
    )
    print("Chrome 已启动，调试地址 http://127.0.0.1:%d" % args.port)
    print("配置目录 %s" % args.profile_dir)
    print("首次使用请在这个窗口里扫码登录微信读书，登录态会保存在配置目录里。")
    print(
        "之后运行：python -m weread_exporter -b <book_id> "
        "--cdp-endpoint http://127.0.0.1:%d" % args.port
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
