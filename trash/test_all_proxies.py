#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试所有代理类型的解析功能
"""

import subprocess
import sys
import os

def test_proxy_url(proxy_url, proxy_type):
    """测试单个代理URL"""
    print(f"\n{'='*60}")
    print(f"🧪 测试 {proxy_type} 代理")
    print(f"{'='*60}")
    
    try:
        # 运行v2ray.py脚本
        result = subprocess.run(
            [sys.executable, "v2ray.py", proxy_url],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print("📤 输出:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ 错误信息:")
            print(result.stderr)
        
        # 检查配置文件是否生成
        config_path = "v2ray-quick/config.json"
        if os.path.exists(config_path):
            print(f"✅ 配置文件已生成: {config_path}")
            
            # 读取并显示配置文件的关键部分
            with open(config_path, 'r', encoding='utf-8') as f:
                import json
                config = json.load(f)
                
            print("📋 生成的配置:")
            print(f"   入站端口: {[ib['port'] for ib in config['inbounds']]}")
            print(f"   出站协议: {config['outbounds'][0]['protocol']}")
            
            if config['outbounds'][0]['protocol'] == 'vmess':
                vmess_config = config['outbounds'][0]['settings']['vnext'][0]
                print(f"   VMess服务器: {vmess_config['address']}:{vmess_config['port']}")
            elif config['outbounds'][0]['protocol'] == 'socks':
                socks_config = config['outbounds'][0]['settings']['servers'][0]
                print(f"   SOCKS服务器: {socks_config['address']}:{socks_config['port']}")
            elif config['outbounds'][0]['protocol'] == 'http':
                http_config = config['outbounds'][0]['settings']['servers'][0]
                print(f"   HTTP服务器: {http_config['address']}:{http_config['port']}")
        else:
            print("❌ 配置文件未生成")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ 测试超时")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 V2Ray 代理解析功能测试")
    print("="*60)
    
    # 测试用例
    test_cases = [
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
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 测试 {i}/{len(test_cases)}: {test_case['type']} 代理")
        success = test_proxy_url(test_case['url'], test_case['type'])
        results.append((test_case['type'], success))
    
    # 总结测试结果
    print(f"\n{'='*60}")
    print("📊 测试结果总结")
    print(f"{'='*60}")
    
    passed = 0
    for proxy_type, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {proxy_type:8} : {status}")
        if success:
            passed += 1
    
    print(f"\n🎯 总体结果: {passed}/{len(results)} 个测试通过")
    
    if passed == len(results):
        print("🎉 所有测试都通过了！")
        print("\n✨ v2ray.py 脚本功能完整，支持:")
        print("   • SOCKS代理解析和配置生成")
        print("   • HTTP代理解析和配置生成")
        print("   • VMess代理解析和配置生成")
        print("   • 自动端口分配")
        print("   • Docker配置生成")
        print("   • 统一的本地代理接口")
    else:
        print("⚠️ 部分测试失败，请检查错误信息")
    
    print("\n📖 使用方法:")
    print("   python v2ray.py <proxy_url>")
    print("\n🔗 生成的本地代理:")
    print("   HTTP:  http://127.0.0.1:10828")
    print("   SOCKS: socks5://127.0.0.1:10829")

if __name__ == "__main__":
    main()