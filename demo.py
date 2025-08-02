#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2Ray 快速启动脚本演示
展示如何使用 v2ray.py 处理不同类型的代理URL
"""

import subprocess
import sys
import os
import time

def run_demo(proxy_url, proxy_type):
    """运行单个演示"""
    print(f"\n{'='*60}")
    print(f"演示: {proxy_type} 代理解析")
    print(f"{'='*60}")
    print(f"代理URL: {proxy_url[:50]}...")
    print("\n执行命令: python v2ray.py \"<proxy_url>\"")
    print("-" * 60)
    
    try:
        # 运行v2ray.py脚本
        result = subprocess.run(
            [sys.executable, "v2ray.py", proxy_url],
            text=True,
            timeout=30
        )
        
        print(f"\n返回码: {result.returncode}")
        
        # 检查生成的配置文件
        config_path = "v2ray-quick/config.json"
        compose_path = "v2ray-quick/docker-compose.yml"
        
        if os.path.exists(config_path) and os.path.exists(compose_path):
            print("\n✅ 配置文件生成成功:")
            print(f"   - {config_path}")
            print(f"   - {compose_path}")
            
            # 显示配置摘要
            with open(config_path, 'r', encoding='utf-8') as f:
                import json
                config = json.load(f)
                
            inbound_ports = [ib['port'] for ib in config['inbounds']]
            outbound_protocol = config['outbounds'][0]['protocol']
            
            print(f"\n📋 配置摘要:")
            print(f"   入站端口: {inbound_ports}")
            print(f"   出站协议: {outbound_protocol}")
            
            if outbound_protocol == 'vmess':
                vmess = config['outbounds'][0]['settings']['vnext'][0]
                print(f"   目标服务器: {vmess['address']}:{vmess['port']}")
            elif outbound_protocol in ['socks', 'http']:
                server = config['outbounds'][0]['settings']['servers'][0]
                print(f"   目标服务器: {server['address']}:{server['port']}")
                
            print(f"\n🔗 本地代理地址:")
            print(f"   HTTP:  http://127.0.0.1:{inbound_ports[0]}")
            print(f"   SOCKS: socks5://127.0.0.1:{inbound_ports[1]}")
        else:
            print("\n❌ 配置文件生成失败")
            
    except subprocess.TimeoutExpired:
        print("\n⏰ 执行超时")
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")

def main():
    """主演示函数"""
    print("🚀 V2Ray 快速启动脚本 - 功能演示")
    print("=" * 60)
    print("\n本演示将展示如何使用 v2ray.py 脚本解析和配置不同类型的代理:")
    print("• SOCKS 代理")
    print("• HTTP 代理")
    print("• VMess 代理")
    print("\n每种代理类型都会生成统一的本地 HTTP 和 SOCKS5 代理接口。")
    
    # 演示用例
    demos = [
        {
            "url": "socks://cHdqcTU0NzgzLXJlZ2lvbi1TRzpxdTN6YXVjNA%3D%3D@sg.cliproxy.io:3010#cliproxy",
            "type": "SOCKS"
        },
        {
            "url": "http://user-spppy9kkam-country-us:efwhiJec4BG2g3I4~a@gate.decodo.com:7000",
            "type": "HTTP"
        },
        {
            "url": "vmess://ew0KICAidiI6ICIyIiwNCiAgInBzIjogIlNpbXBsZVYyUmF5IiwNCiAgImFkZCI6ICIxNTkuNzUuMTIzLjk2IiwNCiAgInBvcnQiOiAiNDc4NjYiLA0KICAiaWQiOiAiY2I4NDNiNjAtNjQxMi00ZGY1LTlmMTUtMTA4ZjE4ZjM0NGZiIiwNCiAgImFpZCI6ICIwIiwNCiAgInNjeSI6ICJhdXRvIiwNCiAgIm5ldCI6ICJ0Y3AiLA0KICAidHlwZSI6ICJub25lIiwNCiAgImhvc3QiOiAiIiwNCiAgInBhdGgiOiAiIiwNCiAgInRscyI6ICIiLA0KICAic25pIjogIiIsDQogICJhbHBuIjogIiIsDQogICJmcCI6ICIiDQp9",
            "type": "VMess"
        }
    ]
    
    for i, demo in enumerate(demos, 1):
        print(f"\n\n🎯 演示 {i}/{len(demos)}")
        run_demo(demo['url'], demo['type'])
        
        if i < len(demos):
            print("\n⏳ 等待 3 秒后继续下一个演示...")
            time.sleep(3)
    
    # 总结
    print(f"\n\n{'='*60}")
    print("📊 演示总结")
    print(f"{'='*60}")
    print("\n✨ v2ray.py 脚本功能特点:")
    print("\n🔧 支持的代理类型:")
    print("   • SOCKS 代理 (支持用户名密码认证)")
    print("   • HTTP 代理 (支持用户名密码认证)")
    print("   • VMess 代理 (支持完整的 VMess 配置)")
    
    print("\n⚙️ 自动化功能:")
    print("   • 智能URL解析 (包括Base64编码)")
    print("   • 自动端口分配 (避免冲突)")
    print("   • V2Ray配置生成")
    print("   • Docker Compose配置生成")
    print("   • 容器自动启动 (如果Docker可用)")
    
    print("\n🌐 统一输出:")
    print("   • HTTP代理:  http://127.0.0.1:10828")
    print("   • SOCKS代理: socks5://127.0.0.1:10829")
    
    print("\n📖 使用方法:")
    print("   python v2ray.py <proxy_url>")
    
    print("\n🛠️ 管理命令:")
    print("   cd v2ray-quick")
    print("   docker compose up -d    # 启动")
    print("   docker compose down     # 停止")
    print("   docker compose logs -f  # 查看日志")
    
    print("\n💡 注意事项:")
    print("   • 需要安装 Docker Desktop")
    print("   • 确保端口 10828-10829 可用")
    print("   • 支持 Windows、macOS、Linux")
    
    print("\n🎉 演示完成！脚本已准备就绪，可以开始使用。")

if __name__ == "__main__":
    main()