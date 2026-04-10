#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试代理URL解析功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from v2ray_docker_setup import detect_proxy_type, generate_v2ray_config
import json

def test_proxy_urls():
    """测试不同类型的代理URL解析"""
    
    # 测试URL
    test_urls = [
        # SOCKS代理
        "socks://cHdqcTU0NzgzLXJlZ2lvbi1TRzpxdTN6YXVjNA%3D%3D@sg.cliproxy.io:3010#cliproxy",
        
        # HTTP代理
        "http://user-spppy9kkam-country-us:efwhiJec4BG2g3I4~a@gate.decodo.com:7000",
        
        # VMess代理
        "vmess://ew0KICAidiI6ICIyIiwNCiAgInBzIjogIlNpbXBsZVYyUmF5IiwNCiAgImFkZCI6ICIxNTkuNzUuMTIzLjk2IiwNCiAgInBvcnQiOiAiNDc4NjYiLA0KICAiaWQiOiAiY2I4NDNiNjAtNjQxMi00ZGY1LTlmMTUtMTA4ZjE4ZjM0NGZiIiwNCiAgImFpZCI6ICIwIiwNCiAgInNjeSI6ICJhdXRvIiwNCiAgIm5ldCI6ICJ0Y3AiLA0KICAidHlwZSI6ICJub25lIiwNCiAgImhvc3QiOiAiIiwNCiAgInBhdGgiOiAiIiwNCiAgInRscyI6ICIiLA0KICAic25pIjogIiIsDQogICJhbHBuIjogIiIsDQogICJmcCI6ICIiDQp9"
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n=== 测试 {i}: {url[:50]}... ===")
        
        try:
            # 解析代理配置
            proxy_info = detect_proxy_type(url)
            proxy_type = proxy_info['type']
            proxy_config = proxy_info['config']
            
            print(f"代理类型: {proxy_type.upper()}")
            
            if proxy_type == 'vmess':
                print(f"服务器: {proxy_config['add']}:{proxy_config['port']}")
                print(f"用户ID: {proxy_config['id']}")
                print(f"网络类型: {proxy_config['net']}")
                print(f"安全性: {proxy_config['scy']}")
            elif proxy_type == 'socks':
                print(f"服务器: {proxy_config['server']}:{proxy_config['port']}")
                print(f"用户名: {proxy_config.get('username', 'N/A')}")
                print(f"密码: {'***' if proxy_config.get('password') else 'N/A'}")
                print(f"备注: {proxy_config['remark']}")
            elif proxy_type == 'http':
                print(f"服务器: {proxy_config['server']}:{proxy_config['port']}")
                print(f"用户名: {proxy_config.get('username', 'N/A')}")
                print(f"密码: {'***' if proxy_config.get('password') else 'N/A'}")
            
            # 生成V2Ray配置
            v2ray_config = generate_v2ray_config(proxy_info, 10828)
            print("\n✅ V2Ray配置生成成功")
            print(f"入站端口: HTTP={v2ray_config['inbounds'][0]['port']}, SOCKS={v2ray_config['inbounds'][1]['port']}")
            print(f"出站协议: {v2ray_config['outbounds'][0]['protocol']}")
            
            # 保存配置文件用于检查
            config_filename = f"test_config_{proxy_type}_{i}.json"
            with open(config_filename, 'w', encoding='utf-8') as f:
                json.dump(v2ray_config, f, indent=2, ensure_ascii=False)
            print(f"配置已保存到: {config_filename}")
            
        except Exception as e:
            print(f"❌ 解析失败: {e}")
            continue

if __name__ == "__main__":
    print("开始测试代理URL解析功能...")
    test_proxy_urls()
    print("\n测试完成！")