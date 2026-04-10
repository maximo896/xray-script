import subprocess
import json
import base64
import binascii
import sys
import os
import argparse
import urllib.parse

def run_command(command, check=True):
    """Execute a shell command and handle errors."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error executing command: {command}")
        print(result.stderr)
        exit(1)
    return result

def check_docker():
    """Check if Docker is installed and running."""
    print("Checking Docker installation...")
    try:
        run_command("docker --version")
        run_command("systemctl is-active docker")
        print("Docker is installed and running.")
    except subprocess.CalledProcessError:
        print("Docker is not installed or not running. Please ensure Docker is installed and running.")
        exit(1)

def pull_v2ray_image():
    """Pull the latest V2Ray Docker image."""
    print("Pulling V2Ray Docker image...")
    run_command("sudo docker pull v2fly/v2fly-core:latest")

def decode_vmess(vmess_url):
    """Decode the VMess URL to extract configuration."""
    try:
        vmess_data = vmess_url.replace("vmess://", "")
        decoded_bytes = base64.b64decode(vmess_data)
        config = json.loads(decoded_bytes.decode("utf-8"))
        return config
    except (binascii.Error, json.JSONDecodeError) as e:
        print(f"Error decoding VMess URL: {e}")
        exit(1)

def decode_socks(socks_url):
    """Decode the SOCKS URL to extract configuration."""
    try:
        # Parse the URL: socks://base64_auth@host:port#name
        parsed_url = urllib.parse.urlparse(socks_url)
        
        # Extract host and port
        host = parsed_url.hostname
        port = parsed_url.port
        
        # Extract and decode base64 encoded auth info
        if parsed_url.username:
            # The username part contains base64 encoded username:password
            auth_data = base64.b64decode(parsed_url.username).decode("utf-8")
            username, password = auth_data.split(":", 1)
        else:
            username = password = None
        
        # Extract name from fragment
        name = urllib.parse.unquote(parsed_url.fragment) if parsed_url.fragment else host
        
        config = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "name": name
        }
        
        return config
    except Exception as e:
        print(f"Error decoding SOCKS URL: {e}")
        exit(1)

def decode_http_proxy(http_url):
    """Decode the HTTP proxy URL to extract configuration."""
    try:
        # Parse the URL: http://username:password@host:port
        parsed_url = urllib.parse.urlparse(http_url)
        
        # Extract host and port
        host = parsed_url.hostname
        port = parsed_url.port if parsed_url.port else 8080  # Default HTTP proxy port
        
        # Extract username and password (plain text, not base64 encoded)
        username = parsed_url.username
        password = parsed_url.password
        
        # Use host as name if no fragment
        name = host
        
        config = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "name": name
        }
        
        return config
    except Exception as e:
        print(f"Error decoding HTTP proxy URL: {e}")
        exit(1)

def create_v2ray_config(vmess_config, socks_port, http_port):
    """Create V2Ray configuration file for SOCKS5 and HTTP proxies."""
    v2ray_config = {
        "inbounds": [
            {
                "port": socks_port,
                "protocol": "socks",
                "settings": {
                    "auth": "noauth",
                    "udp": True
                }
            },
            {
                "port": http_port,
                "protocol": "http",
                "settings": {
                    "allowTransparent": False
                }
            }
        ],
        "outbounds": [{
            "protocol": "vmess",
            "settings": {
                "vnext": [{
                    "address": vmess_config["add"],
                    "port": int(vmess_config["port"]),
                    "users": [{
                        "id": vmess_config["id"],
                        "alterId": int(vmess_config["aid"]),
                        "security": vmess_config["scy"]
                    }]
                }]
            },
            "streamSettings": {
                "network": vmess_config["net"],
                "security": vmess_config["tls"],
                "tcpSettings": {} if vmess_config["type"] == "none" else {"type": vmess_config["type"]}
            }
        }],
        "log": {
            "loglevel": "warning"
        }
    }
    config_path = "/tmp/v2ray_config.json"
    with open(config_path, "w") as f:
        json.dump(v2ray_config, f, indent=2)
    return config_path

def create_socks_v2ray_config(socks_config, socks_port, http_port):
    """Create V2Ray configuration file for SOCKS5 proxy with upstream SOCKS5 server."""
    outbound_settings = {
        "servers": [{
            "address": socks_config["host"],
            "port": socks_config["port"]
        }]
    }
    
    # Add authentication if provided
    if socks_config["username"] and socks_config["password"]:
        outbound_settings["servers"][0]["users"] = [{
            "user": socks_config["username"],
            "pass": socks_config["password"]
        }]
    
    v2ray_config = {
        "inbounds": [
            {
                "port": socks_port,
                "protocol": "socks",
                "settings": {
                    "auth": "noauth",
                    "udp": True
                }
            },
            {
                "port": http_port,
                "protocol": "http",
                "settings": {
                    "allowTransparent": False
                }
            }
        ],
        "outbounds": [{
            "protocol": "socks",
            "settings": outbound_settings
        }],
        "log": {
            "loglevel": "warning"
        }
    }
    
    config_path = "/tmp/v2ray_config.json"
    with open(config_path, "w") as f:
        json.dump(v2ray_config, f, indent=2)
    return config_path

def create_http_v2ray_config(http_config, socks_port, http_port):
    """Create V2Ray configuration file for HTTP proxy with upstream HTTP server."""
    outbound_settings = {
        "servers": [{
            "address": http_config["host"],
            "port": http_config["port"]
        }]
    }
    
    # Add authentication if provided
    if http_config["username"] and http_config["password"]:
        outbound_settings["servers"][0]["users"] = [{
            "user": http_config["username"],
            "pass": http_config["password"]
        }]
    
    v2ray_config = {
        "inbounds": [
            {
                "port": socks_port,
                "protocol": "socks",
                "settings": {
                    "auth": "noauth",
                    "udp": True
                }
            },
            {
                "port": http_port,
                "protocol": "http",
                "settings": {
                    "allowTransparent": False
                }
            }
        ],
        "outbounds": [{
            "protocol": "http",
            "settings": outbound_settings
        }],
        "log": {
            "loglevel": "warning"
        }
    }
    
    config_path = "/tmp/v2ray_config.json"
    with open(config_path, "w") as f:
        json.dump(v2ray_config, f, indent=2)
    return config_path

def run_v2ray_container(config_path, socks_port, http_port):
    """Run the V2Ray Docker container."""
    print("Starting V2Ray Docker container...")
    # Stop and remove any existing v2ray container to avoid conflicts
    run_command("sudo docker stop v2ray 2>/dev/null", check=False)
    run_command("sudo docker rm v2ray 2>/dev/null", check=False)
    run_command(f"sudo docker run -d --name v2ray -p {socks_port}:{socks_port} -p {http_port}:{http_port} -v {config_path}:/etc/v2ray/config.json v2fly/v2fly-core:latest run -c /etc/v2ray/config.json")

def main():
    # Check if running as root or with sudo
    if os.geteuid() != 0:
        print("This script must be run as root. Please use sudo.")
        exit(1)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Set up V2Ray Docker container with VMess, SOCKS5, or HTTP proxy configuration.")
    parser.add_argument("proxy_url", nargs='?', default=None, help="Proxy URL (VMess, SOCKS5, or HTTP) for V2Ray configuration")
    parser.add_argument("--socks-port", type=int, default=10828, help="Port for SOCKS5 proxy (default: 10828)")
    parser.add_argument("--http-port", type=int, default=10829, help="Port for HTTP proxy (default: 10829)")

    # Check if no arguments are provided
    if len(sys.argv) == 1:
        parser.print_help()
        exit(0)

    args = parser.parse_args()

    # Ensure proxy_url is provided
    if not args.proxy_url:
        print("Error: Proxy URL is required.")
        parser.print_help()
        exit(1)

    # Determine protocol and decode URL
    if args.proxy_url.startswith("vmess://"):
        print("Detected VMess protocol")
        proxy_config = decode_vmess(args.proxy_url)
        config_type = "vmess"
    elif args.proxy_url.startswith("socks://"):
        print("Detected SOCKS5 protocol")
        proxy_config = decode_socks(args.proxy_url)
        config_type = "socks"
    elif args.proxy_url.startswith("http://"):
        print("Detected HTTP proxy protocol")
        proxy_config = decode_http_proxy(args.proxy_url)
        config_type = "http"
    else:
        print("Error: Unsupported protocol. Only VMess (vmess://), SOCKS5 (socks://), and HTTP (http://) are supported.")
        exit(1)

    # Check Docker installation
    check_docker()

    # Pull V2Ray image
    pull_v2ray_image()

    # Create V2Ray configuration based on protocol type
    if config_type == "vmess":
        config_path = create_v2ray_config(proxy_config, args.socks_port, args.http_port)
    elif config_type == "socks":
        config_path = create_socks_v2ray_config(proxy_config, args.socks_port, args.http_port)
    elif config_type == "http":
        config_path = create_http_v2ray_config(proxy_config, args.socks_port, args.http_port)

    # Run V2Ray container
    run_v2ray_container(config_path, args.socks_port, args.http_port)

    print(f"V2Ray is running! You can use the SOCKS5 proxy at 127.0.0.1:{args.socks_port} and the HTTP proxy at 127.0.0.1:{args.http_port}, both with no authentication.")
    
    if config_type == "socks":
        print(f"Using upstream SOCKS5 server: {proxy_config['host']}:{proxy_config['port']}")
        if proxy_config['username']:
            print(f"Upstream authentication: {proxy_config['username']}:***")
        print(f"Proxy name: {proxy_config['name']}")
    elif config_type == "http":
        print(f"Using upstream HTTP proxy server: {proxy_config['host']}:{proxy_config['port']}")
        if proxy_config['username']:
            print(f"Upstream authentication: {proxy_config['username']}:***")
        print(f"Proxy name: {proxy_config['name']}")

if __name__ == "__main__":
    main()
