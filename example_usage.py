#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用示例：展示如何使用改进后的v2ray_docker_setup.py
"""

import subprocess
import sys

def run_example(proxy_url, description):
    """运行示例"""
    print(f"\n=== {description} ===")
    print(f"代理URL: {proxy_url[:50]}...")
    
    try:
        # 构建命令
        cmd = [sys.executable, "v2ray_docker_setup.py", "-u", proxy_url, "--verbose"]
        
        print(f"执行命令: {' '.join(cmd[:3])} -u [代理URL] --verbose")
        print("注意: 这只是演示命令构建，实际运行需要Docker环境")
        
        # 这里只是展示命令，不实际执行，因为需要Docker环境
        # result = subprocess.run(cmd, capture_output=True, text=True)
        
    except Exception as e:
        print(f"错误: {e}")

def main():
    """主函数"""
    print("V2Ray Docker Setup 使用示例")
    print("=" * 50)
    
    # 示例代理URL
    examples = [
        {
            "url": "socks://cHdqcTU0NzgzLXJlZ2lvbi1TRzpxdTN6YXVjNA%3D%3D@sg.cliproxy.io:3010#cliproxy",
            "desc": "SOCKS5 代理示例"
        },
        {
            "url": "http://user-spppy9kkam-country-us:efwhiJec4BG2g3I4~a@gate.decodo.com:7000",
            "desc": "HTTP 代理示例"
        },
        {
            "url": "vmess://ew0KICAidiI6ICIyIiwNCiAgInBzIjogIlNpbXBsZVYyUmF5IiwNCiAgImFkZCI6ICIxNTkuNzUuMTIzLjk2IiwNCiAgInBvcnQiOiAiNDc4NjYiLA0KICAiaWQiOiAiY2I4NDNiNjAtNjQxMi00ZGY1LTlmMTUtMTA4ZjE4ZjM0NGZiIiwNCiAgImFpZCI6ICIwIiwNCiAgInNjeSI6ICJhdXRvIiwNCiAgIm5ldCI6ICJ0Y3AiLA0KICAidHlwZSI6ICJub25lIiwNCiAgImhvc3QiOiAiIiwNCiAgInBhdGgiOiAiIiwNCiAgInRscyI6ICIiLA0KICAic25pIjogIiIsDQogICJhbHBuIjogIiIsDQogICJmcCI6ICIiDQp9",
            "desc": "VMess 代理示例"
        }
    ]
    
    for example in examples:
        run_example(example["url"], example["desc"])
    
    print("\n=== 实际使用方法 ===")
    print("1. 确保已安装Docker和docker-compose")
    print("2. 运行以下命令之一:")
    print("   python v2ray_docker_setup.py -u \"socks://your_socks_url\"")
    print("   python v2ray_docker_setup.py -u \"http://your_http_url\"")
    print("   python v2ray_docker_setup.py -u \"vmess://your_vmess_url\"")
    print("3. 脚本会自动:")
    print("   - 解析代理配置")
    print("   - 生成V2Ray配置文件")
    print("   - 启动Docker容器")
    print("   - 提供HTTP和SOCKS5两种本地代理端口")
    print("\n=== 代理端口说明 ===")
    print("默认情况下:")
    print("- HTTP代理: http://127.0.0.1:10828")
    print("- SOCKS5代理: socks5://127.0.0.1:10829")
    print("\n可以使用 -p 参数指定其他端口")
    
if __name__ == "__main__":
    main()