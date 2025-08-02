#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2Ray 快速启动脚本
支持 SOCKS、HTTP、VMess 代理的快速解析和启动
使用方法: python v2ray.py <proxy_url>
"""

import argparse
import base64
import json
import os
import socket
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

def parse_socks_url(socks_url):
    """解析SOCKS代理URL"""
    if not socks_url.startswith('socks://'):
        raise ValueError("无效的SOCKS URL")
    
    parsed = urllib.parse.urlparse(socks_url)
    username = None
    password = None
    
    # 检查netloc中是否包含认证信息
    if '@' in parsed.netloc:
        auth_part, host_part = parsed.netloc.rsplit('@', 1)
        
        # 解析认证部分
        if ':' in auth_part:
            # 格式: username:password@host:port
            username, password = auth_part.split(':', 1)
        else:
            # 格式: base64_auth@host:port
            username = auth_part
        
        # URL解码
        username = urllib.parse.unquote(username)
        if password:
            password = urllib.parse.unquote(password)
        
        # 尝试base64解码用户名（如果包含%编码）
        if '%' in username or (not password and username):
            try:
                decoded = base64.b64decode(username).decode('utf-8')
                if ':' in decoded:
                    username, password = decoded.split(':', 1)
                else:
                    username = decoded
            except Exception:
                # 如果解码失败，保持原始值
                pass
        
        # 重新解析主机和端口
        host_parsed = urllib.parse.urlparse(f'socks://{host_part}')
        hostname = host_parsed.hostname
        port = host_parsed.port
    else:
        hostname = parsed.hostname
        port = parsed.port
    
    remark = parsed.fragment if parsed.fragment else "SOCKS Proxy"
    
    return {
        'type': 'socks',
        'server': hostname,
        'port': port,
        'username': username,
        'password': password,
        'remark': remark
    }

def parse_http_url(http_url):
    """解析HTTP代理URL"""
    if not http_url.startswith('http://'):
        raise ValueError("无效的HTTP代理URL")
    
    parsed = urllib.parse.urlparse(http_url)
    
    return {
        'type': 'http',
        'server': parsed.hostname,
        'port': parsed.port,
        'username': parsed.username,
        'password': parsed.password,
        'remark': "HTTP Proxy"
    }

def parse_vmess_url(vmess_url):
    """解析VMess URL"""
    if not vmess_url.startswith('vmess://'):
        raise ValueError("无效的VMess URL")
    
    encoded_config = vmess_url[8:]
    try:
        decoded_bytes = base64.b64decode(encoded_config)
        config = json.loads(decoded_bytes.decode('utf-8'))
        config['type'] = 'vmess'
        return config
    except Exception as e:
        raise ValueError(f"解码VMess配置失败: {e}")

def detect_proxy_type(url):
    """自动检测代理类型并解析"""
    if url.startswith('vmess://'):
        return parse_vmess_url(url)
    elif url.startswith('socks://'):
        return parse_socks_url(url)
    elif url.startswith('http://'):
        return parse_http_url(url)
    else:
        raise ValueError(f"不支持的代理类型: {url[:20]}...")

def generate_v2ray_config(proxy_config, http_port=10838, socks_port=10839):
    """生成V2Ray配置"""
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "port": http_port,
                "protocol": "http",
                "settings": {"allowTransparent": False}
            },
            {
                "port": socks_port,
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True}
            }
        ],
        "outbounds": []
    }
    
    if proxy_config['type'] == 'socks':
        outbound = {
            "protocol": "socks",
            "settings": {
                "servers": [{
                    "address": proxy_config['server'],
                    "port": proxy_config['port']
                }]
            }
        }
        if proxy_config.get('username') and proxy_config.get('password'):
            outbound["settings"]["servers"][0]["users"] = [{
                "user": proxy_config['username'],
                "pass": proxy_config['password']
            }]
    
    elif proxy_config['type'] == 'http':
        outbound = {
            "protocol": "http",
            "settings": {
                "servers": [{
                    "address": proxy_config['server'],
                    "port": proxy_config['port']
                }]
            }
        }
        if proxy_config.get('username') and proxy_config.get('password'):
            outbound["settings"]["servers"][0]["users"] = [{
                "user": proxy_config['username'],
                "pass": proxy_config['password']
            }]
    
    elif proxy_config['type'] == 'vmess':
        outbound = {
            "protocol": "vmess",
            "settings": {
                "vnext": [{
                    "address": proxy_config["add"],
                    "port": int(proxy_config["port"]),
                    "users": [{
                        "id": proxy_config["id"],
                        "alterId": int(proxy_config["aid"]),
                        "security": proxy_config["scy"]
                    }]
                }]
            },
            "streamSettings": {"network": proxy_config["net"]}
        }
        
        if proxy_config.get("tls") == "tls":
            outbound["streamSettings"]["security"] = "tls"
            if proxy_config.get("sni"):
                outbound["streamSettings"]["tlsSettings"] = {
                    "serverName": proxy_config["sni"]
                }
        
        if proxy_config["net"] == "ws":
            outbound["streamSettings"]["wsSettings"] = {
                "path": proxy_config.get("path", "/")
            }
            if proxy_config.get("host"):
                outbound["streamSettings"]["wsSettings"]["headers"] = {
                    "Host": proxy_config["host"]
                }
    
    config["outbounds"].append(outbound)
    return config

def check_port_available(port):
    """检查端口是否可用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False

def find_available_ports(start_port=10838):
    """查找可用端口"""
    http_port = start_port
    socks_port = start_port + 1
    
    # 检查HTTP端口
    while not check_port_available(http_port):
        http_port += 2
    
    # 检查SOCKS端口
    socks_port = http_port + 1
    while not check_port_available(socks_port):
        http_port += 2
        socks_port = http_port + 1
    
    return http_port, socks_port

def create_docker_compose(http_port, socks_port):
    """创建Docker Compose配置"""
    return f"""version: '3.8'
services:
  v2ray:
    image: v2fly/v2fly-core:latest
    container_name: v2ray-quick
    restart: unless-stopped
    ports:
      - "{http_port}:{http_port}"
      - "{socks_port}:{socks_port}"
    volumes:
      - ./config.json:/etc/v2ray/config.json:ro
    command: ["run", "-c", "/etc/v2ray/config.json"]
"""

def run_command(cmd, cwd=None):
    """执行命令"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_docker_environment():
    """检查Docker环境"""
    # 检查docker命令
    success, stdout, stderr = run_command("docker --version")
    if not success:
        return False, "Docker未安装或未启动"
    
    # 检查docker compose命令 (新版本)
    success, stdout, stderr = run_command("docker compose version")
    if success:
        return True, "docker compose"
    
    # 检查docker-compose命令 (旧版本)
    success, stdout, stderr = run_command("docker-compose --version")
    if success:
        return True, "docker-compose"
    
    return False, "Docker Compose未安装"

def main():
    # 设置控制台编码
    if sys.platform == 'win32':
        import os
        os.system('chcp 65001 >nul 2>&1')  # 设置为UTF-8编码
    
    if len(sys.argv) != 2:
        print("使用方法: python v2ray.py <proxy_url>")
        print("支持的格式:")
        print("  socks://user:pass@server:port#remark")
        print("  http://user:pass@server:port")
        print("  vmess://base64_config")
        print("\n示例:")
        print("  python v2ray.py 'socks://cHdqcTU0NzgzLXJlZ2lvbi1TRzpxdTN6YXVjNA%3D%3D@sg.cliproxy.io:3010#cliproxy'")
        sys.exit(1)
    
    proxy_url = sys.argv[1]
    
    try:
        print("V2Ray 快速启动")
        print("=" * 40)
        
        # 1. 解析代理配置
        print("解析代理配置...")
        proxy_config = detect_proxy_type(proxy_url)
        
        if proxy_config['type'] == 'socks':
            print(f"   类型: SOCKS")
            print(f"   服务器: {proxy_config['server']}:{proxy_config['port']}")
            print(f"   备注: {proxy_config['remark']}")
        elif proxy_config['type'] == 'http':
            print(f"   类型: HTTP")
            print(f"   服务器: {proxy_config['server']}:{proxy_config['port']}")
        elif proxy_config['type'] == 'vmess':
            print(f"   类型: VMess")
            print(f"   服务器: {proxy_config['add']}:{proxy_config['port']}")
        
        # 2. 找到可用端口
        print("\n查找可用端口...")
        http_port, socks_port = find_available_ports()
        print(f"   HTTP端口: {http_port}")
        print(f"   SOCKS端口: {socks_port}")
        
        # 3. 生成配置
        print("\n生成V2Ray配置...")
        v2ray_config = generate_v2ray_config(proxy_config, http_port, socks_port)
        
        # 4. 创建工作目录
        work_dir = Path("./v2ray-quick")
        work_dir.mkdir(exist_ok=True)
        
        # 5. 写入配置文件
        config_file = work_dir / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(v2ray_config, f, indent=2, ensure_ascii=False)
        
        compose_file = work_dir / "docker-compose.yml"
        with open(compose_file, 'w', encoding='utf-8') as f:
            f.write(create_docker_compose(http_port, socks_port))
        
        print(f"   配置已保存到: {work_dir.absolute()}")
        
        # 6. 检查Docker环境
        print("\n检查Docker环境...")
        docker_ok, compose_cmd = check_docker_environment()
        
        if not docker_ok:
            print(f"错误: {compose_cmd}")
            print("\n解决方案:")
            print("1. 安装Docker Desktop: https://www.docker.com/products/docker-desktop")
            print("2. 确保Docker服务正在运行")
            print("3. 重新启动终端")
            print("\n配置文件已生成，可手动启动:")
            print(f"   cd {work_dir.absolute()}")
            print(f"   docker compose up -d")
            sys.exit(1)
        
        print(f"   使用命令: {compose_cmd}")
        
        # 7. 启动Docker容器
        print("\n启动Docker容器...")
        
        # 停止可能存在的容器
        run_command(f"{compose_cmd} down", cwd=work_dir)
        
        # 启动新容器
        success, stdout, stderr = run_command(f"{compose_cmd} up -d", cwd=work_dir)
        
        if not success:
            print(f"启动失败: {stderr}")
            print("\n可能的解决方案:")
            print("1. 确保Docker Desktop正在运行")
            print("2. 检查端口是否被占用")
            print("3. 手动执行以下命令:")
            print(f"   cd {work_dir.absolute()}")
            print(f"   {compose_cmd} up -d")
            sys.exit(1)
        
        # 8. 等待启动完成
        print("等待服务启动...")
        time.sleep(5)
        
        # 9. 检查状态
        success, stdout, stderr = run_command(f"{compose_cmd} ps", cwd=work_dir)
        if success:
            # 检查容器是否存在且状态为Up
            lines = stdout.strip().split('\n')
            container_running = False
            for line in lines[1:]:  # 跳过标题行
                if 'v2ray-quick' in line and 'Up' in line:
                    container_running = True
                    break
            
            if container_running:
                print("\n启动成功!")
                print("=" * 40)
                print(f"HTTP代理:  http://127.0.0.1:{http_port}")
                print(f"SOCKS代理: socks5://127.0.0.1:{socks_port}")
                print("\n使用示例:")
                print(f"curl --proxy http://127.0.0.1:{http_port} https://ipinfo.io")
                print(f"curl --proxy socks5://127.0.0.1:{socks_port} https://ipinfo.io")
                print("\n管理命令:")
                print(f"停止: cd {work_dir.absolute()} && {compose_cmd} down")
                print(f"日志: cd {work_dir.absolute()} && {compose_cmd} logs -f")
                print(f"重启: cd {work_dir.absolute()} && {compose_cmd} restart")
            else:
                print("容器启动失败或状态异常")
                print(f"检查状态: cd {work_dir.absolute()} && {compose_cmd} ps")
                print(f"查看日志: cd {work_dir.absolute()} && {compose_cmd} logs")
        else:
            print("无法检查容器状态")
            print(f"检查命令: cd {work_dir.absolute()} && {compose_cmd} ps")
            print(f"\n配置目录: {work_dir.absolute()}")
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()