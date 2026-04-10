#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2Ray 极简服务器一键搭建脚本
支持随机端口和Docker镜像源配置

作者: Assistant
版本: 2.0
"""

import base64
import json
import os
import subprocess
import sys
import time
import uuid
import random
import socket
import argparse
from pathlib import Path


def run_command(cmd):
    """执行命令"""
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0 and result.stderr:
        print(f"错误: {result.stderr.strip()}")
    return result


def generate_random_port():
    """生成随机可用端口 (10000-65535)"""
    while True:
        port = random.randint(10000, 65535)
        if is_port_available(port):
            return port

def is_port_available(port):
    """检查端口是否可用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            return True
    except OSError:
        return False

def get_public_ip():
    """获取公网IP"""
    try:
        result = subprocess.run(['curl', '-s', 'ipinfo.io/ip'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return "YOUR_SERVER_IP"


def generate_vmess_link(server_ip, port, uuid_str):
    """生成vmess链接"""
    config = {
        "v": "2",
        "ps": "SimpleV2Ray",
        "add": server_ip,
        "port": str(port),
        "id": uuid_str,
        "aid": "0",
        "scy": "auto",
        "net": "tcp",
        "type": "none",
        "host": "",
        "path": "",
        "tls": "",
        "sni": "",
        "alpn": "",
        "fp": ""
    }
    
    json_str = json.dumps(config, separators=(',', ':'))
    encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    return f"vmess://{encoded}"


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='V2Ray 极简服务器一键搭建脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""使用示例:
  python3 simple_v2ray_server.py                                    # 默认配置
  python3 simple_v2ray_server.py --mirror registry.cn-hangzhou.aliyuncs.com  # 使用阿里云镜像源
  python3 simple_v2ray_server.py --port 8080                       # 指定端口
  python3 simple_v2ray_server.py --no-input                        # 非交互模式

常用Docker镜像源:
  - 1panel: docker.1panel.live
  - 阿里云: registry.cn-hangzhou.aliyuncs.com
  - 腾讯云: ccr.ccs.tencentyun.com
  - 华为云: swr.cn-north-4.myhuaweicloud.com
  - 网易云: hub-mirror.c.163.com"""
    )
    
    parser.add_argument('--port', type=int, 
                       help='指定端口号 (默认随机生成)')
    parser.add_argument('--mirror', '--registry-mirror', 
                       help='Docker镜像源地址')
    parser.add_argument('--no-input', action='store_true',
                       help='非交互模式，不提示用户输入')
    parser.add_argument('--config-dir', default='./v2ray-simple',
                       help='配置文件目录 (默认: ./v2ray-simple)')
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    print("🚀 V2Ray 极简服务器一键搭建 v2.0")
    print("=" * 45)
    print()
    
    # 生成随机配置
    print("🎲 生成随机配置...")
    if args.port:
        if not is_port_available(args.port):
            print(f"❌ 端口 {args.port} 已被占用，使用随机端口")
            port = generate_random_port()
        else:
            port = args.port
    else:
        port = generate_random_port()
    
    uuid_str = str(uuid.uuid4())
    
    print(f"📋 服务器配置:")
    print(f"   端口: {port}")
    print(f"   UUID: {uuid_str}")
    print()
    
    # 创建配置目录
    config_dir = Path(args.config_dir)
    config_dir.mkdir(exist_ok=True)
    
    # 生成V2Ray配置
    v2ray_config = {
        "log": {"loglevel": "info"},
        "inbounds": [{
            "port": port,
            "protocol": "vmess",
            "settings": {
                "clients": [{"id": uuid_str, "alterId": 0}]
            },
            "streamSettings": {"network": "tcp"}
        }],
        "outbounds": [{
            "protocol": "freedom",
            "settings": {}
        }]
    }
    
    # 保存配置文件
    with open(config_dir / 'config.json', 'w') as f:
        json.dump(v2ray_config, f, indent=2)
    
    # 处理镜像源配置
    registry_mirror = args.mirror
    
    if not registry_mirror and not args.no_input:
        try:
            # 尝试检测网络环境
            try:
                import requests
            except ImportError:
                print("⚠️  未安装requests库，跳过网络检测")
                print("   建议安装: pip3 install requests")
            else:
                print("🌐 检测网络环境...")
                response = requests.get("https://registry-1.docker.io", timeout=3)
                print("   ✅ Docker Hub 访问正常")
        except Exception as e:
            print("⚠️  检测到网络访问Docker Hub较慢，建议使用国内镜像源")
            print("   常用镜像源:")
            print("   - 阿里云: registry.cn-hangzhou.aliyuncs.com")
            print("   - 腾讯云: ccr.ccs.tencentyun.com")
            print("   - 华为云: swr.cn-north-4.myhuaweicloud.com")
            print("   - 网易云: hub-mirror.c.163.com")
            try:
                mirror_input = input("   请输入镜像源地址 (直接回车跳过): ").strip()
                if mirror_input:
                    registry_mirror = mirror_input
            except KeyboardInterrupt:
                print("\n\n❌ 用户取消操作")
                sys.exit(1)
    
    if registry_mirror:
        print(f"🐳 使用Docker镜像源: {registry_mirror}")
    else:
        print("🐳 使用默认Docker Hub")
    
    # 构建镜像配置
    image_config = "v2fly/v2fly-core:latest"
    if registry_mirror:
        # 如果指定了镜像源，添加镜像源前缀
        if not registry_mirror.endswith('/'):
            registry_mirror += '/'
        image_config = f"{registry_mirror}v2fly/v2fly-core:latest"
    
    # 生成Docker Compose
    docker_compose = f"""version: '3.8'
services:
  v2ray:
    image: {image_config}
    container_name: simple-v2ray
    restart: unless-stopped
    ports:
      - "{port}:{port}"
    volumes:
      - ./config.json:/etc/v2ray/config.json:ro
    command: ["run", "-config", "/etc/v2ray/config.json"]
"""
    
    with open(config_dir / 'docker-compose.yml', 'w') as f:
        f.write(docker_compose)
    
    print("1. 配置文件已生成")
    
    # 检查Docker
    print("2. 检查Docker环境...")
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Docker未安装或无法访问")
            print("   请先安装Docker: https://docs.docker.com/get-docker/")
            return
        print("   ✅ Docker已安装")
    except FileNotFoundError:
        print("❌ 未找到docker命令，请确保Docker已正确安装")
        return
    
    # 启动服务
    os.chdir(config_dir)
    
    print("3. 停止旧容器...")
    run_command("docker-compose down")
    
    print("4. 启动V2Ray服务器...")
    try:
        result = subprocess.run(['docker-compose', 'up', '-d'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ 服务启动成功")
        else:
            print(f"   ❌ 启动失败: {result.stderr}")
            print("   提示: 如果是镜像拉取问题，请使用 --mirror 参数指定镜像源")
            return
    except FileNotFoundError:
        print("❌ 未找到docker-compose命令，请确保Docker Compose已正确安装")
        return
    
    # 等待启动
    print("5. 等待服务启动...")
    time.sleep(3)
    
    # 检查状态
    result = run_command("docker-compose ps")
    
    # 获取IP并生成链接
    print("6. 获取服务器信息...")
    try:
        server_ip = get_public_ip()
        if server_ip == "YOUR_SERVER_IP":
            print("⚠️  无法自动获取公网IP，请手动替换连接链接中的IP地址")
    except Exception as e:
        print(f"⚠️  获取公网IP失败: {e}")
        server_ip = "YOUR_SERVER_IP"
    vmess_link = generate_vmess_link(server_ip, port, uuid_str)
    
    print()
    print("=== 🎉 服务器搭建完成 ===")
    print(f"服务器IP: {server_ip}")
    print(f"端口: {port}")
    print(f"UUID: {uuid_str}")
    print()
    print("📱 客户端连接链接:")
    print(vmess_link)
    print()
    print("📋 管理命令:")
    print(f"停止: cd {config_dir.absolute()} && docker-compose down")
    print(f"重启: cd {config_dir.absolute()} && docker-compose restart")
    print(f"日志: cd {config_dir.absolute()} && docker-compose logs -f")
    print()
    print(f"💡 提示: 如果是云服务器，请在安全组开放端口 {port}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")