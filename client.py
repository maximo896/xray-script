#!/usr/bin/env python3
"""
Deploy an Xray local proxy (HTTP + SOCKS5, no auth) via Docker Compose.

Usage:
  python client.py <proxy_url> [--port 10808] [--config-dir ./xray-client]
  python client.py <proxy_url> --mirror ghcr.nju.edu.cn    # mainland China
  python client.py --stop

Supported proxy URL formats:
  vmess://...
  vless://uuid@host:port?security=reality&pbk=...&sid=...&sni=...&fp=chrome
  vless://uuid@host:port?security=tls&sni=...
  trojan://password@host:443?security=tls&sni=...
  socks://[user:pass@]host:port
  socks5://[user:pass@]host:port
  http://[user:pass@]host:port

Result:
  127.0.0.1:<port>  — serves both SOCKS5 and HTTP proxy, no authentication.

CN mirrors for ghcr.io (image prefix, auto-tried when ghcr.io is blocked):
  NOTE: docker.1panel.live only proxies Docker Hub, NOT ghcr.io.
  ghcr.nju.edu.cn          南京大学  (recommended)
  ghcr.m.daocloud.io       DaoCloud

CN mirrors for Docker Hub (auto-written to /etc/docker/daemon.json on Linux):
  docker.1panel.live  /  registry.cn-hangzhou.aliyuncs.com  /  ccr.ccs.tencentyun.com
  swr.cn-north-4.myhuaweicloud.com  /  hub-mirror.c.163.com
"""

import argparse
import base64
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

CONFIG_DIR = Path("./xray-client")

XRAY_IMAGE = "ghcr.io/xtls/xray-core:latest"

# Mirrors that proxy ghcr.io — used as image-name prefix.
# docker.1panel.live only proxies Docker Hub and does NOT work here.
CN_GHCR_MIRRORS = [
    "ghcr.nju.edu.cn",
    "ghcr.m.daocloud.io",
]

# Docker Hub daemon-level mirrors — written to /etc/docker/daemon.json
CN_DOCKERHUB_MIRRORS = [
    "https://docker.1panel.live",
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://ccr.ccs.tencentyun.com",
    "https://swr.cn-north-4.myhuaweicloud.com",
    "https://hub-mirror.c.163.com",
]


# ── helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list, check=True, capture=False, verbose=True):
    if verbose:
        print(f"  $ {' '.join(cmd)}")
    kwargs = {"check": check}
    if capture:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    return subprocess.run(cmd, **kwargs)


def build_container_name(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4)}"


def host_reachable(host: str, port: int = 443, timeout: float = 4.0) -> bool:
    try:
        conn = socket.create_connection((host, port), timeout=timeout)
        conn.close()
        return True
    except Exception:
        return False


def resolve_image(image: str, mirror: str) -> str:
    """Replace the registry hostname in an image reference with *mirror*."""
    parts = image.split("/", 1)
    if len(parts) == 2 and ("." in parts[0] or ":" in parts[0]):
        return f"{mirror.rstrip('/')}/{parts[1]}"
    return f"{mirror.rstrip('/')}/{image}"


def configure_docker_daemon_mirror() -> bool:
    """
    Write /etc/docker/daemon.json with CN Docker Hub mirrors and reload Docker.
    Returns True if successful, False if skipped (not root or not Linux).
    """
    if sys.platform != "linux" or os.geteuid() != 0:
        return False
    daemon_json = Path("/etc/docker/daemon.json")
    try:
        existing: dict = {}
        if daemon_json.exists():
            try:
                existing = json.loads(daemon_json.read_text())
            except Exception:
                pass
        existing.setdefault("registry-mirrors", [])
        added = [m for m in CN_DOCKERHUB_MIRRORS if m not in existing["registry-mirrors"]]
        if not added:
            return False
        existing["registry-mirrors"] = CN_DOCKERHUB_MIRRORS + [
            m for m in existing["registry-mirrors"] if m not in CN_DOCKERHUB_MIRRORS
        ]
        daemon_json.parent.mkdir(parents=True, exist_ok=True)
        daemon_json.write_text(json.dumps(existing, indent=2))
        subprocess.run(["systemctl", "reload", "docker"], check=False, capture_output=True)
        return True
    except Exception as e:
        print(f"      (daemon.json update skipped: {e})")
        return False


def select_image(mirror_arg: str | None) -> str:
    """Return the image reference to use, auto-detecting CN environment."""
    if mirror_arg:
        img = resolve_image(XRAY_IMAGE, mirror_arg)
        print(f"      Mirror : {mirror_arg}")
        print(f"      Image  : {img}")
        return img

    print("      Checking ghcr.io connectivity...", end=" ", flush=True)
    if host_reachable("ghcr.io"):
        print("OK")
        return XRAY_IMAGE

    print("UNREACHABLE")
    print("      ghcr.io is blocked. Trying CN ghcr mirrors automatically...")
    for m in CN_GHCR_MIRRORS:
        print(f"      Trying {m}...", end=" ", flush=True)
        if host_reachable(m):
            print("OK")
            img = resolve_image(XRAY_IMAGE, m)
            print(f"      Image  : {img}")
            if configure_docker_daemon_mirror():
                print("      Docker Hub daemon mirrors written to /etc/docker/daemon.json")
            return img
        print("unreachable")

    # All mirrors unreachable — configure daemon mirrors and attempt anyway
    configure_docker_daemon_mirror()
    img = resolve_image(XRAY_IMAGE, CN_GHCR_MIRRORS[0])
    print(f"      All CN mirrors unreachable. Attempting: {img}")
    print(f"      NOTE: docker.1panel.live does NOT proxy ghcr.io images.")
    print(f"      Known ghcr.io mirrors: {', '.join(CN_GHCR_MIRRORS)}")
    return img


# ── URL parsers ───────────────────────────────────────────────────────────────

def _b64decode(s: str) -> bytes:
    """Base64 decode with padding fix."""
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)


def parse_vmess(url: str) -> dict:
    raw = json.loads(_b64decode(url[8:]).decode())
    return {
        "protocol": "vmess",
        "address": raw["add"],
        "port": int(raw["port"]),
        "uuid": raw["id"],
        "alter_id": int(raw.get("aid", 0)),
        "security": raw.get("scy", "auto"),   # encryption method
        "network": raw.get("net", "tcp"),
        "tls": raw.get("tls", ""),            # "tls" or ""
        "sni": raw.get("sni", raw.get("host", "")),
        "fp": raw.get("fp", ""),
        "path": raw.get("path", "/"),
        "host": raw.get("host", ""),
        "header_type": raw.get("type", "none"),
    }


def parse_vless(url: str) -> dict:
    # vless://uuid@host:port?params#remark
    p = urllib.parse.urlparse(url)
    q = dict(urllib.parse.parse_qsl(p.query))
    return {
        "protocol": "vless",
        "address": p.hostname,
        "port": p.port,
        "uuid": urllib.parse.unquote(p.username or ""),
        "flow": q.get("flow", ""),
        "tls": q.get("security", "none"),      # "reality" / "tls" / "none"
        "sni": q.get("sni", ""),
        "fp": q.get("fp", ""),
        "pbk": q.get("pbk", ""),              # REALITY public key
        "sid": q.get("sid", ""),              # REALITY short ID
        "spx": q.get("spx", "/"),
        "network": q.get("type", "tcp"),
        "path": q.get("path", "/"),
        "host": q.get("host", ""),
        "header_type": q.get("headerType", "none"),
        "service_name": q.get("serviceName", ""),
    }


def parse_trojan(url: str) -> dict:
    p = urllib.parse.urlparse(url)
    q = dict(urllib.parse.parse_qsl(p.query))
    return {
        "protocol": "trojan",
        "address": p.hostname,
        "port": p.port,
        "password": urllib.parse.unquote(p.username or ""),
        "tls": q.get("security", "tls"),
        "sni": q.get("sni", p.hostname or ""),
        "fp": q.get("fp", ""),
        "network": q.get("type", "tcp"),
        "path": q.get("path", "/"),
        "host": q.get("host", ""),
        "service_name": q.get("serviceName", ""),
    }


def parse_socks(url: str) -> dict:
    p = urllib.parse.urlparse(url)
    return {
        "protocol": "socks",
        "address": p.hostname,
        "port": p.port,
        "username": urllib.parse.unquote(p.username) if p.username else None,
        "password": urllib.parse.unquote(p.password) if p.password else None,
    }


def parse_http_proxy(url: str) -> dict:
    p = urllib.parse.urlparse(url)
    return {
        "protocol": "http",
        "address": p.hostname,
        "port": p.port,
        "username": urllib.parse.unquote(p.username) if p.username else None,
        "password": urllib.parse.unquote(p.password) if p.password else None,
    }


def parse_proxy_url(url: str) -> dict:
    url = url.strip()
    if url.startswith("vmess://"):
        return parse_vmess(url)
    if url.startswith("vless://"):
        return parse_vless(url)
    if url.startswith("trojan://"):
        return parse_trojan(url)
    if url.startswith("socks5://") or url.startswith("socks://"):
        return parse_socks(url)
    if url.startswith("http://"):
        return parse_http_proxy(url)
    raise ValueError(f"Unsupported proxy scheme. Got: {url[:40]!r}")


# ── Xray config builders ──────────────────────────────────────────────────────

def _stream_settings(info: dict) -> dict:
    net = info.get("network", "tcp")
    tls = info.get("tls", "none")
    ss: dict = {"network": net}

    if tls == "reality":
        ss["security"] = "reality"
        ss["realitySettings"] = {
            "fingerprint": info.get("fp", "chrome") or "chrome",
            "serverName": info.get("sni", ""),
            "publicKey": info.get("pbk", ""),
            "shortId": info.get("sid", ""),
            "spiderX": info.get("spx") or "/",
        }
    elif tls == "tls":
        ss["security"] = "tls"
        ss["tlsSettings"] = {
            "serverName": info.get("sni", ""),
            "fingerprint": info.get("fp", "") or "",
            "allowInsecure": False,
        }

    if net == "ws":
        ss["wsSettings"] = {
            "path": info.get("path", "/"),
            "headers": {"Host": info["host"]} if info.get("host") else {},
        }
    elif net == "grpc":
        ss["grpcSettings"] = {"serviceName": info.get("service_name", "")}
    elif net == "tcp" and info.get("header_type") == "http":
        ss["tcpSettings"] = {
            "header": {
                "type": "http",
                "request": {
                    "path": [info.get("path", "/")],
                    "headers": {"Host": [info.get("host", "")]},
                },
            }
        }
    elif net == "h2":
        ss["httpSettings"] = {
            "path": info.get("path", "/"),
            "host": [info["host"]] if info.get("host") else [],
        }
    elif net == "quic":
        ss["quicSettings"] = {}

    return ss


def build_outbound(info: dict) -> dict:
    proto = info["protocol"]

    if proto == "vmess":
        user = {
            "id": info["uuid"],
            "alterId": info.get("alter_id", 0),
            "security": info.get("security", "auto"),
        }
        ob = {
            "protocol": "vmess",
            "settings": {
                "vnext": [{"address": info["address"], "port": info["port"], "users": [user]}]
            },
            "streamSettings": _stream_settings(info),
        }

    elif proto == "vless":
        user: dict = {"id": info["uuid"], "encryption": "none"}
        if info.get("flow"):
            user["flow"] = info["flow"]
        ob = {
            "protocol": "vless",
            "settings": {
                "vnext": [{"address": info["address"], "port": info["port"], "users": [user]}]
            },
            "streamSettings": _stream_settings(info),
        }

    elif proto == "trojan":
        ob = {
            "protocol": "trojan",
            "settings": {
                "servers": [{
                    "address": info["address"],
                    "port": info["port"],
                    "password": info["password"],
                }]
            },
            "streamSettings": _stream_settings(info),
        }

    elif proto == "socks":
        server: dict = {"address": info["address"], "port": info["port"]}
        if info.get("username"):
            server["users"] = [{"user": info["username"], "pass": info.get("password", "")}]
        ob = {
            "protocol": "socks",
            "settings": {"servers": [server]},
        }

    elif proto == "http":
        server = {"address": info["address"], "port": info["port"]}
        if info.get("username"):
            server["users"] = [{"user": info["username"], "pass": info.get("password", "")}]
        ob = {
            "protocol": "http",
            "settings": {"servers": [server]},
        }

    else:
        raise ValueError(f"Unknown protocol: {proto}")

    ob["tag"] = "proxy"
    return ob


def build_xray_config(proxy_info: dict, local_port: int) -> dict:
    """
    Single inbound using the 'mixed' protocol — handles both HTTP and SOCKS5
    on the same port without authentication.
    """
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": "mixed-in",
                "port": local_port,
                "listen": "0.0.0.0",
                "protocol": "mixed",
                "settings": {
                    "auth": "noauth",
                    "udp": True,
                    "userLevel": 0,
                },
            }
        ],
        "outbounds": [
            build_outbound(proxy_info),
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "blocked"},
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {"type": "field", "outboundTag": "proxy", "network": "tcp,udp"},
            ],
        },
    }


def build_docker_compose(local_port: int, image: str, container_name: str) -> str:
    return f"""\
services:
  xray:
    image: {image}
    container_name: {container_name}
    restart: unless-stopped
    ports:
      - "127.0.0.1:{local_port}:{local_port}"
    volumes:
      - ./config.json:/etc/xray/config.json:ro
    command: ["run", "-c", "/etc/xray/config.json"]
"""


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Deploy Xray local HTTP+SOCKS5 proxy (no auth) via Docker Compose",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python client.py vmess://...
  python client.py "vless://uuid@host:443?security=reality&pbk=xxx&sid=yyy&sni=www.microsoft.com&fp=chrome&flow=xtls-rprx-vision&type=tcp"
  python client.py "trojan://mypassword@host:443?security=tls&sni=example.com"
  python client.py "socks5://user:pass@host:1080"
  python client.py "http://host:8080"
  python client.py vmess://... --port 10809
  python client.py vmess://... --mirror ghcr.1panel.live  # mainland China
  python client.py --stop

CN mirrors for ghcr.io (auto-tried when ghcr.io is blocked):
  ghcr.1panel.live         (1Panel — recommended)
  ghcr.nju.edu.cn          (南京大学)
  ghcr.m.daocloud.io       (DaoCloud)

Docker Hub daemon mirrors (auto-written to /etc/docker/daemon.json on Linux root):
  docker.1panel.live  /  registry.cn-hangzhou.aliyuncs.com  /  ccr.ccs.tencentyun.com
  swr.cn-north-4.myhuaweicloud.com  /  hub-mirror.c.163.com
""",
    )
    parser.add_argument("url", nargs="?", help="Proxy URL (vmess/vless/trojan/socks5/http)")
    parser.add_argument("--port", type=int, default=10808,
                        help="Local bind port (default: 10808)")
    parser.add_argument("--mirror", default=None, metavar="HOST",
                        help="Registry mirror for ghcr.io (e.g. ghcr.1panel.live). "
                             "Auto-detected when ghcr.io is unreachable.")
    parser.add_argument("--config-dir", default="./xray-client",
                        help="Working directory for generated files (default: ./xray-client)")
    parser.add_argument("--stop", action="store_true",
                        help="Stop and remove the running local proxy container")
    args = parser.parse_args()

    global CONFIG_DIR
    CONFIG_DIR = Path(args.config_dir)

    # ── stop mode ──
    if args.stop:
        if not (CONFIG_DIR / "docker-compose.yml").exists():
            print(f"No docker-compose.yml found in {CONFIG_DIR}")
            sys.exit(1)
        os.chdir(CONFIG_DIR)
        run(["docker", "compose", "down"])
        print("Stopped.")
        return

    if not args.url:
        parser.print_help()
        sys.exit(1)

    local_port = args.port

    print("=== Xray Local Proxy Setup ===\n")

    # 1. Parse
    print("[1/4] Parsing proxy URL...")
    try:
        info = parse_proxy_url(args.url)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print(f"      Protocol : {info['protocol'].upper()}")
    print(f"      Server   : {info['address']}:{info['port']}")
    tls_mode = info.get("tls", "none")
    if tls_mode == "reality":
        print(f"      Security : REALITY  (SNI: {info.get('sni')}, pbk: {info.get('pbk','')[:16]}...)")
    elif tls_mode == "tls":
        print(f"      Security : TLS  (SNI: {info.get('sni')})")
    else:
        print(f"      Security : none")
    print()

    # 2. Image selection (handles CN mirror auto-detection)
    print("[2/4] Selecting Docker image...")
    image = select_image(args.mirror)
    print()

    # 3. Write files
    print(f"[3/4] Writing config files to {CONFIG_DIR.resolve()} ...")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    xray_cfg = build_xray_config(info, local_port)
    container_name = build_container_name("xray-local-proxy")
    (CONFIG_DIR / "config.json").write_text(json.dumps(xray_cfg, indent=2, ensure_ascii=False))
    (CONFIG_DIR / "docker-compose.yml").write_text(build_docker_compose(local_port, image, container_name))
    print(f"      Container: {container_name}")
    print()

    # 4. Start
    print("[4/4] Starting Docker container...")
    orig_dir = Path.cwd()
    os.chdir(CONFIG_DIR)
    run(["docker", "compose", "down"], check=False, capture=True, verbose=False)

    pull_result = run(["docker", "compose", "pull"], check=False)
    if pull_result.returncode != 0:
        print()
        print("ERROR: docker compose pull failed.")
        print(f"  Image tried : {image}")
        print()
        print("  ghcr.io is only accessible via these mirrors in China:")
        for m in CN_GHCR_MIRRORS:
            print(f"    python client.py <url> --mirror {m}")
        print()
        print("  NOTE: docker.1panel.live only proxies Docker Hub, not ghcr.io.")
        os.chdir(orig_dir)
        sys.exit(1)

    run(["docker", "compose", "up", "-d"])
    print()

    print("      Waiting for container...")
    time.sleep(3)
    result = run(["docker", "compose", "ps"], check=False, capture=True, verbose=False)
    print(result.stdout.strip())
    print()

    os.chdir(orig_dir)

    print("=" * 55)
    print(f"  Local proxy ready at  127.0.0.1:{local_port}")
    print(f"  SOCKS5  →  socks5://127.0.0.1:{local_port}")
    print(f"  HTTP    →  http://127.0.0.1:{local_port}")
    print(f"  No username / password required.")
    print()
    print("  Test:")
    print(f"    curl --proxy socks5://127.0.0.1:{local_port} https://ipinfo.io/ip")
    print(f"    curl --proxy http://127.0.0.1:{local_port}   https://ipinfo.io/ip")
    print()
    print(f"  Logs : cd {CONFIG_DIR.resolve()} && docker compose logs -f")
    print(f"  Stop : python client.py --stop")
    print("=" * 55)


if __name__ == "__main__":
    main()
