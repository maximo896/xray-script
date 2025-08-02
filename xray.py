# Import necessary modules
import argparse
import base64
import json
import logging
import os
import socket
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

def decode_vmess_url(vmess_url):
    if not vmess_url.startswith('vmess://'):
        raise ValueError("Invalid vmess URL")
    encoded_config = vmess_url[8:]
    try:
        decoded_bytes = base64.b64decode(encoded_config)
        config = json.loads(decoded_bytes.decode('utf-8'))
        return config
    except Exception as e:
        raise ValueError(f"Failed to decode vmess config: {e}")

def parse_socks_url(socks_url):
    if not socks_url.startswith('socks://'):
        raise ValueError("Invalid socks URL")
    parsed = urllib.parse.urlparse(socks_url)
    username = None
    password = None
    if parsed.username:
        try:
            username = urllib.parse.unquote(parsed.username)
            if '%' not in username and username != parsed.username:
                try:
                    decoded = base64.b64decode(username).decode('utf-8')
                    if ':' in decoded:
                        username, password = decoded.split(':', 1)
                    else:
                        username = decoded
                except:
                    pass
        except:
            username = parsed.username
    if parsed.password and not password:
        password = urllib.parse.unquote(parsed.password)
    remark = parsed.fragment if parsed.fragment else "SOCKS Proxy"
    return {
        'type': 'socks',
        'server': parsed.hostname,
        'port': parsed.port,
        'username': username,
        'password': password,
        'remark': remark
    }

def parse_http_url(http_url):
    if not http_url.startswith('http://'):
        raise ValueError("Invalid http proxy URL")
    parsed = urllib.parse.urlparse(http_url)
    return {
        'type': 'http',
        'server': parsed.hostname,
        'port': parsed.port,
        'username': parsed.username,
        'password': parsed.password,
        'remark': "HTTP Proxy"
    }

def detect_proxy_type(url):
    if url.startswith('vmess://'):
        config = decode_vmess_url(url)
        return {'type': 'vmess', 'config': config}
    elif url.startswith('socks://'):
        config = parse_socks_url(url)
        return {'type': 'socks', 'config': config}
    elif url.startswith('http://'):
        config = parse_http_url(url)
        return {'type': 'http', 'config': config}
    else:
        raise ValueError(f"Unsupported proxy type: {url[:20]}...")

def generate_xray_config(proxy_info, local_port=10808):
    proxy_type = proxy_info['type']
    proxy_config = proxy_info['config']
    xray_config = {
        "log": {"loglevel": "debug"},
        "inbounds": [
            {"port": local_port, "listen": "0.0.0.0", "protocol": "socks", "settings": {"auth": "noauth", "udp": True}}
        ],
        "outbounds": [],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": []
        }
    }
    if proxy_type == 'vmess':
        outbound = {
            "protocol": "vmess",
            "settings": {"vnext": [{"address": proxy_config["add"], "port": int(proxy_config["port"]), "users": [{"id": proxy_config["id"], "alterId": int(proxy_config["aid"]), "security": proxy_config["scy"]}]}]},
            "streamSettings": {"network": proxy_config["net"]},
            "tag": "proxy"
        }
        if proxy_config.get("tls") == "tls":
            outbound["streamSettings"]["security"] = "tls"
            if proxy_config.get("sni"):
                outbound["streamSettings"]["tlsSettings"] = {"serverName": proxy_config["sni"]}
        if proxy_config["net"] == "ws":
            outbound["streamSettings"]["wsSettings"] = {"path": proxy_config.get("path", "/")}
            if proxy_config.get("host"):
                outbound["streamSettings"]["wsSettings"]["headers"] = {"Host": proxy_config["host"]}
        xray_config["outbounds"].append(outbound)
        xray_config["outbounds"].append({"protocol": "blackhole", "tag": "blocked"})
        xray_config["routing"]["rules"].append({"type": "field", "outboundTag": "proxy", "network": "tcp,udp"})
    elif proxy_type == 'socks':
        socks_outbound = {
            "protocol": "socks",
            "settings": {"servers": [{"address": proxy_config["server"], "port": proxy_config["port"], "version": "5"}]},
            "tag": "socks-out"
        }
        if proxy_config.get("username") and proxy_config.get("password"):
            socks_outbound["settings"]["servers"][0]["users"] = [{"user": proxy_config["username"], "pass": proxy_config["password"]}]
        freedom_outbound = {
            "protocol": "freedom",
            "settings": {"domainStrategy": "UseIPv4"},
            "proxySettings": {"tag": "socks-out"},
            "tag": "proxy"
        }
        direct_outbound = {
            "protocol": "freedom",
            "tag": "direct"
        }
        blocked_outbound = {
            "protocol": "blackhole",
            "tag": "blocked"
        }
        xray_config["outbounds"].append(freedom_outbound)
        xray_config["outbounds"].append(socks_outbound)
        xray_config["outbounds"].append(direct_outbound)
        xray_config["outbounds"].append(blocked_outbound)
        xray_config["routing"]["rules"] = [
            {"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"},
            {"type": "field", "outboundTag": "proxy", "network": "tcp,udp"}
        ]
    elif proxy_type == 'http':
        outbound = {
            "protocol": "http",
            "settings": {"servers": [{"address": proxy_config["server"], "port": proxy_config["port"]}]},
            "tag": "proxy"
        }
        if proxy_config.get("username") and proxy_config.get("password"):
            outbound["settings"]["servers"][0]["users"] = [{"user": proxy_config["username"], "pass": proxy_config["password"]}]
        xray_config["outbounds"].append(outbound)
        xray_config["outbounds"].append({"protocol": "blackhole", "tag": "blocked"})
        xray_config["routing"]["rules"].append({"type": "field", "outboundTag": "proxy", "network": "tcp,udp"})
    return xray_config

def create_docker_compose(local_port=10808):
    return f"version: '3.8'\nservices:\n  xray:\n    image: ghcr.io/xtls/xray-core:latest\n    container_name: xray-proxy\n    restart: unless-stopped\n    ports:\n      - \"127.0.0.1:{local_port}:{local_port}\"\n    volumes:\n      - ./config.json:/etc/xray/config.json:ro\n    command: [\"run\", \"-c\", \"/etc/xray/config.json\"]\n"

def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler(), logging.FileHandler('xray_setup.log')])
    return logging.getLogger(__name__)

def check_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False

def run_command(cmd, check=True, logger=None):
    if logger:
        logger.info(f"Executing command: {cmd}")
    else:
        print(f"Executing command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            if logger:
                logger.info(result.stdout.strip())
            else:
                print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed: {e}"
        if e.stderr:
            error_msg += f"\nError: {e.stderr}"
        if logger:
            logger.error(error_msg)
        else:
            print(error_msg)
        if check:
            sys.exit(1)
        return e

def parse_arguments():
    parser = argparse.ArgumentParser(description='Xray Docker Setup Script')
    parser.add_argument('-u', '--url', type=str, required=True, help='Proxy URL (vmess://, socks://, http://)')
    parser.add_argument('-p', '--port', type=int, default=10808, help='Local proxy port (default: 10808)')
    parser.add_argument('--config-dir', type=str, default='./xray-docker', help='Config directory (default: ./xray-docker)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--generate-only', action='store_true', help='Generate config files only, without starting Docker')
    return parser.parse_args()

def main():
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    local_port = args.port
    config_dir_path = args.config_dir
    if not args.generate_only:
        if not check_port_available(local_port):
            print(f"Port {local_port} is occupied")
            sys.exit(1)
        if not check_port_available(local_port + 1):
            print(f"Port {local_port + 1} is occupied")
            sys.exit(1)
    try:
        proxy_info = detect_proxy_type(args.url)
        xray_config = generate_xray_config(proxy_info, local_port)
        config_dir = Path(config_dir_path)
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(xray_config, f, indent=2, ensure_ascii=False)
        compose_file = config_dir / "docker-compose.yml"
        with open(compose_file, 'w', encoding='utf-8') as f:
            f.write(create_docker_compose(local_port))
        if not args.generate_only:
            os.chdir(config_dir)
            run_command("docker-compose down", check=False, logger=logger)
            run_command("docker-compose pull", logger=logger)
            run_command("docker-compose up -d", logger=logger)
            time.sleep(5)
            print(f"Xray container started. Local SOCKS proxy at 127.0.0.1:{local_port} (compatible with HTTP)")
        else:
            print(f"Config files generated in {config_dir_path}. You can start the container later with docker-compose up -d in that directory.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()