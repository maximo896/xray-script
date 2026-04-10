#!/bin/bash
# V2Ray Docker 快速启动脚本
# 适用于 Ubuntu 24.04

set -e

echo "=== V2Ray Docker 快速启动 ==="

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
    echo "请不要使用root用户运行此脚本"
    exit 1
fi

# 显示使用帮助
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "使用方法:"
    echo "  $0 [vmess_url] [port]"
    echo ""
    echo "参数:"
    echo "  vmess_url  - V2Ray vmess:// 配置链接（可选）"
    echo "  port       - 本地代理端口（可选，默认10828）"
    echo ""
    echo "示例:"
    echo "  $0"
    echo "  $0 \"vmess://ew0KICAidiI6ICIyIi...\""
    echo "  $0 \"vmess://ew0KICAidiI6ICIyIi...\" 8080"
    echo ""
    echo "更多选项请使用: python3 v2ray_docker_setup.py -h"
    exit 0
fi

# 检查Python3是否安装
if ! command -v python3 &> /dev/null; then
    echo "正在安装Python3..."
    sudo apt update
    sudo apt install -y python3 python3-pip
fi

# 给Python脚本执行权限
chmod +x v2ray_docker_setup.py

# 构建Python脚本参数
PYTHON_ARGS=""
if [ -n "$1" ]; then
    PYTHON_ARGS="$PYTHON_ARGS -u \"$1\""
fi
if [ -n "$2" ]; then
    PYTHON_ARGS="$PYTHON_ARGS -p $2"
fi

# 运行Python脚本
echo "启动V2Ray配置脚本..."
if [ -n "$PYTHON_ARGS" ]; then
    echo "使用参数: $PYTHON_ARGS"
    eval "python3 v2ray_docker_setup.py $PYTHON_ARGS"
else
    python3 v2ray_docker_setup.py
fi

echo "\n脚本执行完成！"
echo "如果是首次安装Docker，请执行以下命令后重新运行:"
echo "newgrp docker"
echo "或者重新登录系统"