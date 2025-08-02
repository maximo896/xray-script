#!/bin/bash

# V2Ray 极简服务器一键启动脚本 v2.0
# 支持随机端口和Docker镜像源配置

set -e

# 显示帮助信息
show_help() {
    echo "V2Ray 极简服务器一键启动脚本 v2.0"
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  -p, --port PORT        指定端口号 (默认随机生成)"
    echo "  -m, --mirror MIRROR    Docker镜像源地址"
    echo "  -n, --no-input         非交互模式"
    echo "  -h, --help             显示此帮助信息"
    echo
    echo "使用示例:"
    echo "  $0                                    # 默认配置"
    echo "  $0 -m registry.cn-hangzhou.aliyuncs.com  # 使用阿里云镜像源"
    echo "  $0 -p 8080                           # 指定端口"
    echo "  $0 -n -m hub-mirror.c.163.com       # 非交互模式 + 网易云镜像源"
    echo
    echo "常用Docker镜像源:"
    echo "  - 阿里云: registry.cn-hangzhou.aliyuncs.com"
    echo "  - 腾讯云: ccr.ccs.tencentyun.com"
    echo "  - 华为云: swr.cn-north-4.myhuaweicloud.com"
    echo "  - 网易云: hub-mirror.c.163.com"
}

# 解析命令行参数
PORT=""
MIRROR=""
NO_INPUT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -m|--mirror)
            MIRROR="$2"
            shift 2
            ;;
        -n|--no-input)
            NO_INPUT="--no-input"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

echo "🚀 V2Ray 极简服务器一键启动 v2.0"
echo "=========================================="
echo

# 检查Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，正在安装..."
    sudo apt update
    sudo apt install -y python3
fi

# 检查脚本文件
if [ ! -f "simple_v2ray_server.py" ]; then
    echo "❌ 未找到 simple_v2ray_server.py"
    exit 1
fi

# 给脚本执行权限
chmod +x simple_v2ray_server.py

# 构建Python命令参数
PYTHON_ARGS=""
if [ -n "$PORT" ]; then
    PYTHON_ARGS="$PYTHON_ARGS --port $PORT"
fi
if [ -n "$MIRROR" ]; then
    PYTHON_ARGS="$PYTHON_ARGS --mirror $MIRROR"
fi
if [ -n "$NO_INPUT" ]; then
    PYTHON_ARGS="$PYTHON_ARGS $NO_INPUT"
fi

# 执行脚本
echo "🔥 开始部署..."
echo
python3 simple_v2ray_server.py $PYTHON_ARGS

echo
echo "✅ 完成！复制上面的 vmess:// 链接到客户端即可使用"