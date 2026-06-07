#!/usr/bin/env python3
"""
Xray REALITY server — one-command deploy via Docker Compose.

Usage:
  python server.py                        # port 443, steal from www.microsoft.com
  python server.py --port 8443           # use unprivileged port
  python server.py --dest www.apple.com:443 --fp safari
  python server.py --upstream-socks5 'socks5://user:pass@1.2.3.4:1080'
  python server.py --upstream-http 'http://user:pass@1.2.3.4:8080'
  python server.py --mirror ghcr.nju.edu.cn    # use CN mirror for ghcr.io
  python server.py --stop                      # stop the running container

Requirements: Docker (with Compose plugin) installed on the server.
No domain or certificate needed — REALITY uses TLS camouflage.

CN mirrors for ghcr.io (used as image prefix, auto-tried when ghcr.io is blocked):
  NOTE: docker.1panel.live only proxies Docker Hub, NOT ghcr.io.
  ghcr.nju.edu.cn          南京大学  (recommended)
  ghcr.m.daocloud.io       DaoCloud

CN mirrors for Docker Hub (configured via /etc/docker/daemon.json):
  https://docker.1panel.live      1Panel
  https://registry.cn-hangzhou.aliyuncs.com   阿里云
  https://ccr.ccs.tencentyun.com  腾讯云
  https://swr.cn-north-4.myhuaweicloud.com    华为云
  https://hub-mirror.c.163.com    网易云
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
import urllib.request
import uuid
from pathlib import Path

CONFIG_DIR = Path("./xray-server")

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
    kwargs: dict = {"check": False, "capture_output": True, "text": True}
    result = subprocess.run(cmd, **kwargs)
    if not capture and result.stdout:
        print(result.stdout, end="")
    if result.returncode != 0 and not capture:
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
    return result


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


def parse_socks_url(url: str) -> dict:
    url = url.strip()
    if url.startswith("socks5://"):
        url = "socks://" + url[len("socks5://"):]
    if not url.startswith("socks://"):
        raise ValueError("Upstream must be socks5:// or socks://")
    p = urllib.parse.urlparse(url)
    if not p.hostname or not p.port:
        raise ValueError("Upstream socks URL must include host and port")
    return {
        "address": p.hostname,
        "port": int(p.port),
        "username": urllib.parse.unquote(p.username) if p.username else None,
        "password": urllib.parse.unquote(p.password) if p.password else None,
    }


def parse_http_url(url: str) -> dict:
    url = url.strip()
    if not url.startswith("http://"):
        raise ValueError("Upstream must be http://")
    p = urllib.parse.urlparse(url)
    if not p.hostname or not p.port:
        raise ValueError("Upstream HTTP URL must include host and port")
    return {
        "address": p.hostname,
        "port": int(p.port),
        "username": urllib.parse.unquote(p.username) if p.username else None,
        "password": urllib.parse.unquote(p.password) if p.password else None,
    }


def build_socks_outbound(upstream: dict, tag: str = "proxy") -> dict:
    server: dict = {"address": upstream["address"], "port": upstream["port"]}
    if upstream.get("username"):
        server["users"] = [{"user": upstream["username"], "pass": upstream.get("password") or ""}]
    return {"protocol": "socks", "tag": tag, "settings": {"servers": [server]}}


def build_http_outbound(upstream: dict, tag: str = "proxy") -> dict:
    server: dict = {"address": upstream["address"], "port": upstream["port"]}
    if upstream.get("username"):
        server["users"] = [{"user": upstream["username"], "pass": upstream.get("password") or ""}]
    return {"protocol": "http", "tag": tag, "settings": {"servers": [server]}}


def _mask_secret(s: str | None) -> str:
    if not s:
        return ""
    if len(s) <= 4:
        return "*" * len(s)
    return s[:2] + "*" * (len(s) - 4) + s[-2:]


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


def get_public_ip() -> str:
    for url in [
        "https://api4.ipify.org",
        "https://ipinfo.io/ip",
        "https://checkip.amazonaws.com",
        "https://icanhazip.com",
    ]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                ip = r.read().decode().strip()
                if ip:
                    return ip
        except Exception:
            continue
    raise RuntimeError("Cannot determine public IP. Pass --ip manually.")


def generate_reality_keys_python() -> tuple[str, str]:
    """
    Generate an x25519 key pair using the `cryptography` stdlib — no Docker needed.
    Returns (private_key_b64url, public_key_b64url) matching xray's x25519 format.
    """
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    priv = X25519PrivateKey.generate()
    priv_b64 = base64.urlsafe_b64encode(priv.private_bytes_raw()).decode().rstrip("=")
    pub_b64  = base64.urlsafe_b64encode(priv.public_key().public_bytes_raw()).decode().rstrip("=")
    return priv_b64, pub_b64


def generate_reality_keys_docker(image: str) -> tuple[str, str]:
    """Fallback: run `xray x25519` inside a throw-away container."""
    try:
        result = run(
            ["docker", "run", "--rm", image, "x25519"],
            capture=True, verbose=False, check=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        raise RuntimeError(
            f"docker run x25519 failed (exit {e.returncode}).\n"
            f"Docker output: {stderr}\n"
            f"Hint: the image may not have been pulled yet — "
            f"try `docker pull {image}` manually first."
        ) from e
    private_key = public_key = None
    for line in result.stdout.splitlines():
        if "Private key:" in line:
            private_key = line.split(":", 1)[1].strip()
        elif "Public key:" in line:
            public_key = line.split(":", 1)[1].strip()
    if not private_key or not public_key:
        raise RuntimeError(f"Failed to parse x25519 output:\n{result.stdout}")
    return private_key, public_key


def generate_reality_keys(image: str) -> tuple[str, str]:
    """Generate x25519 keys: prefer pure-Python, fall back to Docker."""
    try:
        keys = generate_reality_keys_python()
        print("      (generated via Python cryptography library)")
        return keys
    except ImportError:
        pass
    print("      (cryptography library not found, using Docker fallback)")
    return generate_reality_keys_docker(image)


# ── config builders ───────────────────────────────────────────────────────────

def build_server_config(uid, private_key, short_id, dest, sni, port, upstream_socks: dict | None = None, upstream_http: dict | None = None) -> dict:
    if upstream_socks:
        outbounds = [
            build_socks_outbound(upstream_socks, tag="proxy"),
            {"protocol": "blackhole", "tag": "blocked"},
        ]
        rules = [
            {"type": "field", "ip": ["geoip:private"], "outboundTag": "blocked"},
            {"type": "field", "outboundTag": "proxy", "network": "tcp,udp"},
        ]
    elif upstream_http:
        outbounds = [
            build_http_outbound(upstream_http, tag="proxy"),
            {"protocol": "blackhole", "tag": "blocked"},
        ]
        rules = [
            {"type": "field", "ip": ["geoip:private"], "outboundTag": "blocked"},
            {"type": "field", "outboundTag": "proxy", "network": "tcp,udp"},
        ]
    else:
        outbounds = [
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "blocked"},
        ]
        rules = [
            {"type": "field", "ip": ["geoip:private"], "outboundTag": "blocked"},
            {"type": "field", "outboundTag": "direct", "network": "tcp,udp"},
        ]
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": "reality-in",
                "port": port,
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {"id": uid, "flow": "xtls-rprx-vision"}
                    ],
                    "decryption": "none",
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "show": False,
                        "dest": dest,
                        "xver": 0,
                        "serverNames": [sni],
                        "privateKey": private_key,
                        "shortIds": [short_id],
                    },
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls", "quic"],
                },
            }
        ],
        "outbounds": outbounds,
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": rules,
        },
    }


def build_docker_compose(port: int, image: str, container_name: str) -> str:
    privileged_extras = ""
    if port < 1024:
        privileged_extras = (
            "    user: root\n"
            "    cap_add:\n"
            "      - NET_BIND_SERVICE\n"
        )
    return f"""\
services:
  xray:
    image: {image}
    container_name: {container_name}
    restart: unless-stopped
    network_mode: host
{privileged_extras}    volumes:
      - ./config.json:/etc/xray/config.json:ro
    command: ["run", "-c", "/etc/xray/config.json"]
"""


def build_vless_link(uid, ip, port, public_key, short_id, sni, fp) -> str:
    params = (
        f"encryption=none"
        f"&flow=xtls-rprx-vision"
        f"&security=reality"
        f"&sni={sni}"
        f"&fp={fp}"
        f"&pbk={public_key}"
        f"&sid={short_id}"
        f"&type=tcp"
        f"&headerType=none"
    )
    tag = f"REALITY-{ip}"
    return f"vless://{uid}@{ip}:{port}?{params}#{tag}"


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Deploy Xray REALITY server via Docker Compose (no domain/cert needed)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python server.py
  python server.py --port 443
  python server.py --dest www.apple.com:443 --fp safari --ip 1.2.3.4
  python server.py --mirror ghcr.1panel.live     # mainland China
  python server.py --stop

CN mirrors for ghcr.io (image prefix, auto-tried when ghcr.io is blocked):
  ghcr.1panel.live         (1Panel — recommended)
  ghcr.nju.edu.cn          (南京大学)
  ghcr.m.daocloud.io       (DaoCloud)

CN mirrors for Docker Hub (auto-written to /etc/docker/daemon.json on Linux):
  docker.1panel.live  /  registry.cn-hangzhou.aliyuncs.com  /  ccr.ccs.tencentyun.com
  swr.cn-north-4.myhuaweicloud.com  /  hub-mirror.c.163.com
""",
    )
    parser.add_argument("--port", type=int, default=443,
                        help="Listening port (default: 443)")
    parser.add_argument("--dest", default="www.microsoft.com:443",
                        help="REALITY camouflage target (default: www.microsoft.com:443)")
    parser.add_argument("--fp", default="chrome",
                        choices=["chrome", "firefox", "safari", "edge", "ios", "android", "random"],
                        help="TLS fingerprint to mimic (default: chrome)")
    parser.add_argument("--ip", default=None,
                        help="Override detected public IP in the generated link")
    parser.add_argument("--mirror", default=None, metavar="HOST",
                        help="Registry mirror for ghcr.io (e.g. ghcr.1panel.live). "
                             "Auto-detected when ghcr.io is unreachable.")
    parser.add_argument("--config-dir", default="./xray-server",
                        help="Directory for generated files (default: ./xray-server)")
    parser.add_argument("--upstream-socks5", default=None, metavar="URL",
                        help="Forward all traffic to an upstream SOCKS5 proxy, e.g. socks5://user:pass@host:1080")
    parser.add_argument("--upstream-http", default=None, metavar="URL",
                        help="Forward all traffic to an upstream HTTP proxy, e.g. http://user:pass@host:8080")
    parser.add_argument("--stop", action="store_true",
                        help="Stop and remove the running container")
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

    port = args.port
    dest = args.dest
    sni = dest.split(":")[0]
    upstream_socks = parse_socks_url(args.upstream_socks5) if args.upstream_socks5 else None
    upstream_http = parse_http_url(args.upstream_http) if args.upstream_http else None

    print("=== Xray REALITY Server Setup ===\n")

    # 1. Public IP
    print("[1/6] Detecting public IP...")
    if args.ip:
        ip = args.ip
        print(f"      (overridden) {ip}")
    else:
        ip = get_public_ip()
        print(f"      {ip}")
    print()

    # 2. Image selection (handles CN mirror auto-detection)
    print("[2/6] Selecting Docker image...")
    image = select_image(args.mirror)
    print()

    # 3. Key generation
    print("[3/6] Generating REALITY keys (runs xray x25519 in Docker)...")
    private_key, public_key = generate_reality_keys(image)
    print(f"      Private key : {private_key}")
    print(f"      Public  key : {public_key}")
    print()

    # 4. UUID + ShortID
    uid = str(uuid.uuid4())
    short_id = secrets.token_hex(4)   # 8 hex chars
    print(f"[4/6] UUID     : {uid}")
    print(f"      ShortID  : {short_id}")
    if upstream_socks:
        u = upstream_socks
        auth = f"{u['username']}:{_mask_secret(u.get('password'))}@" if u.get("username") else ""
        print(f"      Upstream : socks5://{auth}{u['address']}:{u['port']}")
    if upstream_http:
        u = upstream_http
        auth = f"{u['username']}:{_mask_secret(u.get('password'))}@" if u.get("username") else ""
        print(f"      Upstream : http://{auth}{u['address']}:{u['port']}")
    print()

    # 5. Write configs
    print(f"[5/6] Writing config files to {CONFIG_DIR.resolve()} ...")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = build_server_config(uid, private_key, short_id, dest, sni, port, upstream_socks=upstream_socks, upstream_http=upstream_http)
    container_name = build_container_name("xray-reality-server")
    (CONFIG_DIR / "config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    (CONFIG_DIR / "docker-compose.yml").write_text(build_docker_compose(port, image, container_name))
    print(f"      Container: {container_name}")
    print()

    # 6. Start container
    print("[6/6] Starting Docker container...")
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
            print(f"    python server.py --mirror {m}")
        print()
        print("  NOTE: docker.1panel.live only proxies Docker Hub, not ghcr.io.")
        os.chdir(orig_dir)
        sys.exit(1)

    run(["docker", "compose", "up", "-d"])
    print()

    print("      Waiting for container to start...")
    time.sleep(3)
    result = run(["docker", "compose", "ps"], check=False, capture=True, verbose=False)
    print(result.stdout.strip())
    print()

    os.chdir(orig_dir)

    link = build_vless_link(uid, ip, port, public_key, short_id, sni, args.fp)

    print("=" * 65)
    print("VLESS+REALITY link  (paste into v2rayN / Clash.Meta / Shadowrocket):")
    print()
    print(link)
    print()
    print("=" * 65)
    print(f"  Server     : {ip}:{port}")
    print(f"  Protocol   : VLESS + XTLS-Vision + REALITY")
    print(f"  UUID       : {uid}")
    print(f"  PublicKey  : {public_key}")
    print(f"  ShortID    : {short_id}")
    print(f"  SNI / dest : {sni}  (camouflage: {dest})")
    print(f"  Fingerprint: {args.fp}")
    print()
    print(f"  Logs : cd {CONFIG_DIR.resolve()} && docker compose logs -f")
    print(f"  Stop : python server.py --stop")
    print("=" * 65)


if __name__ == "__main__":
    main()
