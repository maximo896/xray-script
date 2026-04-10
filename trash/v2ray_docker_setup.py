#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2Ray Docker 一键启动脚本
用于在Ubuntu 24.04上启动V2Ray Docker容器并映射到指定端口
"""

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
    """解码vmess URL"""
    if not vmess_url.startswith('vmess://'):
        raise ValueError("无效的vmess URL")
    
    # 移除vmess://前缀并解码base64
    encoded_config = vmess_url[8:]
    try:
        decoded_bytes = base64.b64decode(encoded_config)
        config = json.loads(decoded_bytes.decode('utf-8'))
        return config
    except Exception as e:
        raise ValueError(f"解码vmess配置失败: {e}")

def parse_socks_url(socks_url):
    """解析socks URL"""
    if not socks_url.startswith('socks://'):
        raise ValueError("无效的socks URL")
    
    # 解析URL
    parsed = urllib.parse.urlparse(socks_url)
    
    # 解码用户名和密码
    username = None
    password = None
    
    if parsed.username:
        try:
            # URL解码用户名
            username = urllib.parse.unquote(parsed.username)
            # 如果用户名是base64编码的，尝试解码
            if '%' not in username and username != parsed.username:
                try:
                    decoded = base64.b64decode(username).decode('utf-8')
                    # 检查是否包含冒号分隔的用户名:密码格式
                    if ':' in decoded:
                        username, password = decoded.split(':', 1)
                    else:
                        username = decoded
                except:
                    pass
        except:
            username = parsed.username
    
    # 如果URL中直接包含密码
    if parsed.password and not password:
        password = urllib.parse.unquote(parsed.password)
    
    # 提取fragment作为备注
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
    """解析http代理URL"""
    if not http_url.startswith('http://'):
        raise ValueError("无效的http代理URL")
    
    # 解析URL
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
    """检测代理类型并解析"""
    if url.startswith('vmess://'):
        config = decode_vmess_url(url)
        return {
            'type': 'vmess',
            'config': config
        }
    elif url.startswith('socks://'):
        config = parse_socks_url(url)
        return {
            'type': 'socks',
            'config': config
        }
    elif url.startswith('http://'):
        config = parse_http_url(url)
        return {
            'type': 'http',
            'config': config
        }
    else:
        raise ValueError(f"不支持的代理类型: {url[:20]}...")

def generate_v2ray_config(proxy_info, local_port=10828):
    """生成V2Ray配置文件"""
    proxy_type = proxy_info['type']
    proxy_config = proxy_info['config']
    
    # 基础配置
    v2ray_config = {
        "log": {
            "loglevel": "warning"
        },
        "inbounds": [
            {
                "port": local_port,
                "protocol": "http",
                "settings": {
                    "allowTransparent": False
                }
            },
            {
                "port": local_port + 1,
                "protocol": "socks",
                "settings": {
                    "auth": "noauth",
                    "udp": True
                }
            }
        ],
        "outbounds": []
    }
    
    # 根据代理类型生成outbound配置
    if proxy_type == 'vmess':
        outbound = {
            "protocol": "vmess",
            "settings": {
                "vnext": [
                    {
                        "address": proxy_config["add"],
                        "port": int(proxy_config["port"]),
                        "users": [
                            {
                                "id": proxy_config["id"],
                                "alterId": int(proxy_config["aid"]),
                                "security": proxy_config["scy"]
                            }
                        ]
                    }
                ]
            },
            "streamSettings": {
                "network": proxy_config["net"]
            }
        }
        
        # 如果有TLS配置
        if proxy_config.get("tls") == "tls":
            outbound["streamSettings"]["security"] = "tls"
            if proxy_config.get("sni"):
                outbound["streamSettings"]["tlsSettings"] = {
                    "serverName": proxy_config["sni"]
                }
        
        # 如果是WebSocket
        if proxy_config["net"] == "ws":
            outbound["streamSettings"]["wsSettings"] = {
                "path": proxy_config.get("path", "/")
            }
            if proxy_config.get("host"):
                outbound["streamSettings"]["wsSettings"]["headers"] = {
                    "Host": proxy_config["host"]
                }
    
    elif proxy_type == 'socks':
        outbound = {
            "protocol": "socks",
            "settings": {
                "servers": [
                    {
                        "address": proxy_config["server"],
                        "port": proxy_config["port"]
                    }
                ]
            }
        }
        
        # 如果有用户名和密码
        if proxy_config.get("username") and proxy_config.get("password"):
            outbound["settings"]["servers"][0]["users"] = [
                {
                    "user": proxy_config["username"],
                    "pass": proxy_config["password"]
                }
            ]
    
    elif proxy_type == 'http':
        outbound = {
            "protocol": "http",
            "settings": {
                "servers": [
                    {
                        "address": proxy_config["server"],
                        "port": proxy_config["port"]
                    }
                ]
            }
        }
        
        # 如果有用户名和密码
        if proxy_config.get("username") and proxy_config.get("password"):
            outbound["settings"]["servers"][0]["users"] = [
                {
                    "user": proxy_config["username"],
                    "pass": proxy_config["password"]
                }
            ]
    
    v2ray_config["outbounds"].append(outbound)
    return v2ray_config

def create_docker_compose(local_port=10828):
    """创建Docker Compose配置"""
    docker_compose = f"""version: '3.8'
services:
  v2ray:
    image: v2fly/v2fly-core:latest
    container_name: v2ray-proxy
    restart: unless-stopped
    ports:
      - "{local_port}:{local_port}"
      - "{local_port + 1}:{local_port + 1}"
    volumes:
      - ./config.json:/etc/v2ray/config.json:ro
    command: ["run", "-c", "/etc/v2ray/config.json"]
"""
    return docker_compose

def setup_logging(verbose=False):
    """设置日志记录"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('v2ray_setup.log')
        ]
    )
    return logging.getLogger(__name__)

def check_port_available(port):
    """检查端口是否可用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False

def test_proxy_connection(port, timeout=10):
    """测试代理连接"""
    try:
        import requests
        proxies = {
            'http': f'http://127.0.0.1:{port}',
            'https': f'http://127.0.0.1:{port}'
        }
        response = requests.get('https://ipinfo.io/json', 
                              proxies=proxies, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            return True, data.get('ip', 'Unknown')
        return False, None
    except Exception as e:
        return False, str(e)

def run_command(cmd, check=True, logger=None):
    """执行命令"""
    if logger:
        logger.info(f"执行命令: {cmd}")
    else:
        print(f"执行命令: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=check, 
                              capture_output=True, text=True)
        if result.stdout:
            if logger:
                logger.info(result.stdout.strip())
            else:
                print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        error_msg = f"命令执行失败: {e}"
        if e.stderr:
            error_msg += f"\n错误信息: {e.stderr}"
        
        if logger:
            logger.error(error_msg)
        else:
            print(error_msg)
        
        if check:
            sys.exit(1)
        return e

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='V2Ray Docker 一键启动脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  python3 v2ray_docker_setup.py -u "vmess://your_vmess_url_here"
  python3 v2ray_docker_setup.py -u "socks://user:pass@server:port#remark"
  python3 v2ray_docker_setup.py -u "http://user:pass@server:port"
  python3 v2ray_docker_setup.py --url "vmess://your_vmess_url_here" --port 8080
  python3 v2ray_docker_setup.py --verbose --test-connection
        '''
    )
    
    parser.add_argument(
        '-u', '--url',
        type=str,
        help='代理配置链接 (支持 vmess://, socks://, http://)'
    )
    
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=10828,
        help='本地代理端口 (默认: 10828, SOCKS端口为此端口+1)'
    )
    
    parser.add_argument(
        '--config-dir',
        type=str,
        default='./v2ray-docker',
        help='配置文件目录 (默认: ./v2ray-docker)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='启用详细日志记录'
    )
    
    parser.add_argument(
        '--test-connection',
        action='store_true',
        help='启动后测试代理连接'
    )
    
    return parser.parse_args()

def main():
    # 解析命令行参数
    args = parse_arguments()
    
    # 设置日志记录
    logger = setup_logging(args.verbose if hasattr(args, 'verbose') else False)
    
    # 默认的V2Ray配置URL（如果没有通过参数提供）
    default_vmess_url = "vmess://ew0KICAidiI6ICIyIiwNCiAgInBzIjogIjUuMFggXHVEODNDXHVEREU4XHVEODNDXHVEREYzIFx1NjVFNVx1NUZEN1x1OEJCMFx1NUY1NSBcdTdFQ0RcdTUxNzQyIFx1NTM1N1x1NEU5QVx1NEUyRFx1OEY2QyIsDQogICJhZGQiOiAibGlnaHRzYWlsc2cuZWRub3Zhcy5saWZlIiwNCiAgInBvcnQiOiAiNDM5MTYiLA0KICAiaWQiOiAiMzgwY2ZhMDQtZTQwMC00ZGYwLTg0MDAtNGFkNmY4YWYyNTc1IiwNCiAgImFpZCI6ICIwIiwNCiAgInNjeSI6ICJhdXRvIiwNCiAgIm5ldCI6ICJ0Y3AiLA0KICAidHlwZSI6ICJub25lIiwNCiAgImhvc3QiOiAiIiwNCiAgInBhdGgiOiAiIiwNCiAgInRscyI6ICIiLA0KICAic25pIjogIiIsDQogICJhbHBuIjogIiIsDQogICJmcCI6ICIiDQp9"
    
    # 使用参数中的URL，如果没有提供则使用默认值
    vmess_url = args.url if args.url else default_vmess_url
    local_port = args.port
    config_dir_path = args.config_dir
    
    if not args.url:
        print("⚠️  警告: 未提供代理URL，使用默认配置")
        print("   建议使用: python3 v2ray_docker_setup.py -u \"your_proxy_url\"")
        print("   支持格式: vmess://, socks://, http://")
        print("   或查看帮助: python3 v2ray_docker_setup.py -h\n")
    
    print("=== V2Ray Docker 一键启动脚本 ===")
    print(f"目标端口: {local_port} (HTTP代理), {local_port + 1} (SOCKS代理)")
    
    # 检查端口是否可用
    if not check_port_available(local_port):
        print(f"❌ 端口 {local_port} 已被占用，请选择其他端口")
        sys.exit(1)
    
    if not check_port_available(local_port + 1):
        print(f"❌ 端口 {local_port + 1} 已被占用，请选择其他端口")
        sys.exit(1)
    
    try:
        # 1. 解析代理配置
        print("\n1. 解析代理配置...")
        proxy_info = detect_proxy_type(vmess_url)
        proxy_type = proxy_info['type']
        proxy_config = proxy_info['config']
        
        if proxy_type == 'vmess':
            print(f"代理类型: VMess")
            print(f"服务器: {proxy_config['add']}:{proxy_config['port']}")
            print(f"协议: {proxy_config['net']}")
        elif proxy_type == 'socks':
            print(f"代理类型: SOCKS")
            print(f"服务器: {proxy_config['server']}:{proxy_config['port']}")
            print(f"备注: {proxy_config['remark']}")
            if proxy_config.get('username'):
                print(f"认证: {proxy_config['username']}")
        elif proxy_type == 'http':
            print(f"代理类型: HTTP")
            print(f"服务器: {proxy_config['server']}:{proxy_config['port']}")
            if proxy_config.get('username'):
                print(f"认证: {proxy_config['username']}")
        
        # 2. 生成V2Ray配置文件
        print("\n2. 生成V2Ray配置文件...")
        v2ray_config = generate_v2ray_config(proxy_info, local_port)
        
        # 创建配置目录
        config_dir = Path(config_dir_path)
        config_dir.mkdir(exist_ok=True)
        
        # 写入配置文件
        config_file = config_dir / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(v2ray_config, f, indent=2, ensure_ascii=False)
        print(f"配置文件已保存: {config_file}")
        
        # 3. 生成Docker Compose文件
        print("\n3. 生成Docker Compose配置...")
        docker_compose_content = create_docker_compose(local_port)
        compose_file = config_dir / "docker-compose.yml"
        with open(compose_file, 'w', encoding='utf-8') as f:
            f.write(docker_compose_content)
        print(f"Docker Compose文件已保存: {compose_file}")
        
        # 4. 检查Docker是否安装
        print("\n4. 检查Docker环境...")
        result = run_command("docker --version", check=False, logger=logger)
        if result.returncode != 0:
            print("Docker未安装，正在安装...")
            run_command("sudo apt update", logger=logger)
            run_command("sudo apt install -y docker.io docker-compose", logger=logger)
            run_command("sudo systemctl start docker", logger=logger)
            run_command("sudo systemctl enable docker", logger=logger)
            run_command("sudo usermod -aG docker $USER", logger=logger)
            print("Docker安装完成，请重新登录后再次运行此脚本")
            return
        
        # 5. 启动Docker容器
        print("\n5. 启动V2Ray Docker容器...")
        os.chdir(config_dir)
        
        # 停止可能存在的容器
        run_command("docker-compose down", check=False, logger=logger)
        
        # 拉取最新镜像
        run_command("docker-compose pull", logger=logger)
        
        # 启动容器
        run_command("docker-compose up -d", logger=logger)
        
        # 6. 等待容器启动并检查状态
        print("\n6. 等待容器启动...")
        time.sleep(5)  # 等待容器完全启动
        
        run_command("docker-compose ps", logger=logger)
        run_command("docker-compose logs --tail=20", logger=logger)
        
        # 7. 健康检查
        print("\n7. 进行健康检查...")
        max_retries = 3
        for i in range(max_retries):
            result = run_command("docker-compose ps --format json", check=False, logger=logger)
            if result.returncode == 0:
                try:
                    containers = json.loads(result.stdout)
                    if isinstance(containers, dict):
                        containers = [containers]
                    
                    v2ray_container = next((c for c in containers if 'v2ray' in c.get('Name', '')), None)
                    if v2ray_container and v2ray_container.get('State') == 'running':
                        print("✅ V2Ray容器运行正常")
                        break
                    else:
                        print(f"⚠️  容器状态异常，重试 {i+1}/{max_retries}")
                        if i < max_retries - 1:
                            time.sleep(10)
                except json.JSONDecodeError:
                    print(f"⚠️  无法解析容器状态，重试 {i+1}/{max_retries}")
                    if i < max_retries - 1:
                        time.sleep(10)
        
        # 8. 测试连接（如果启用）
        if hasattr(args, 'test_connection') and args.test_connection:
            print("\n8. 测试代理连接...")
            time.sleep(5)  # 额外等待时间确保代理就绪
            
            success, result = test_proxy_connection(local_port)
            if success:
                print(f"✅ HTTP代理连接成功，外部IP: {result}")
            else:
                print(f"❌ HTTP代理连接失败: {result}")
        
        print(f"\n=== 启动完成 ===")
        print(f"HTTP代理地址: http://127.0.0.1:{local_port}")
        print(f"SOCKS代理地址: socks5://127.0.0.1:{local_port + 1}")
        print("\n使用示例:")
        print(f"curl --proxy http://127.0.0.1:{local_port} https://ipinfo.io")
        print(f"curl --proxy socks5://127.0.0.1:{local_port + 1} https://ipinfo.io")
        print("\n管理命令:")
        print(f"停止: cd {config_dir.absolute()} && docker-compose down")
        print(f"重启: cd {config_dir.absolute()} && docker-compose restart")
        print(f"查看日志: cd {config_dir.absolute()} && docker-compose logs -f")
        print(f"测试连接: python3 {Path(__file__).absolute()} -u {vmess_url} --test-connection")
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()