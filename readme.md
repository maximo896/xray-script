# V2Ray Docker 一键启动脚本

这个脚本可以帮助你在 Ubuntu 24.04 上快速启动一个 V2Ray Docker 容器，并将代理服务映射到本地端口。

## 功能特性

- 🚀 **一键启动**: 自动解析vmess链接，生成配置文件
- 🐳 **Docker化部署**: 使用Docker容器运行，环境隔离
- 🔧 **自动化安装**: 自动检查并安装Docker环境
- 📝 **配置生成**: 自动生成V2Ray和Docker Compose配置
- 🌐 **双协议支持**: 同时提供HTTP和SOCKS5代理
- 🔒 **无鉴权访问**: 本地代理无需用户名密码
- 📊 **智能监控**: 端口检查、健康检查和连接测试
- 📋 **详细日志**: 支持详细日志记录和文件输出
- 🔍 **故障诊断**: 自动重试机制和错误处理
- ⚙️ **灵活配置**: 支持自定义端口、配置目录等参数

## 端口映射

- **HTTP 代理**: `http://127.0.0.1:10828`
- **SOCKS5 代理**: `socks5://127.0.0.1:10829`

## 快速开始

### 安装依赖

```bash
# 安装Python依赖
pip3 install -r requirements.txt

# 或者手动安装
pip3 install requests
```

### 方法一：使用 Bash 脚本（推荐）

```bash
# 给脚本执行权限
chmod +x start_v2ray.sh

# 使用默认配置
./start_v2ray.sh

# 使用自定义vmess链接
./start_v2ray.sh "vmess://your_vmess_url_here"

# 使用自定义vmess链接和端口
./start_v2ray.sh "vmess://your_vmess_url_here" 8080

# 查看帮助
./start_v2ray.sh -h
```

### 方法二：直接运行 Python 脚本

```bash
# 确保有 Python3
sudo apt update
sudo apt install -y python3

# 使用默认配置运行
python3 v2ray_docker_setup.py

# 使用自定义vmess链接
python3 v2ray_docker_setup.py -u "vmess://your_vmess_url_here"

# 自定义端口和配置目录
python3 v2ray_docker_setup.py -u "vmess://your_vmess_url_here" -p 8080 --config-dir ./my-v2ray

# 启用详细日志和连接测试
python3 v2ray_docker_setup.py -u "vmess://your_vmess_url_here" --verbose --test-connection

# 查看所有参数选项
python3 v2ray_docker_setup.py -h
```

## 命令行参数

脚本支持以下命令行参数：

- `-u, --url`: V2Ray vmess:// 配置链接（必需，除非使用默认配置）
- `-p, --port`: 本地代理端口（默认: 10828，SOCKS端口为此端口+1）
- `--config-dir`: 配置文件目录（默认: ./v2ray-docker）
- `-v, --verbose`: 启用详细日志记录
- `--test-connection`: 启动后自动测试代理连接
- `-h, --help`: 显示帮助信息

### 使用示例

```bash
# 基本使用
python3 v2ray_docker_setup.py -u "vmess://ew0KICAidiI6ICIyIi..."

# 指定不同端口
python3 v2ray_docker_setup.py -u "vmess://ew0KICAidiI6ICIyIi..." -p 8080

# 启用详细日志和连接测试
python3 v2ray_docker_setup.py -u "vmess://ew0KICAidiI6ICIyIi..." --verbose --test-connection

# 指定配置目录
python3 v2ray_docker_setup.py -u "vmess://ew0KICAidiI6ICIyIi..." --config-dir /home/user/v2ray-config
```

## 使用代理

### 命令行测试

```bash
# 使用 HTTP 代理测试
curl --proxy http://127.0.0.1:10828 https://ipinfo.io

# 使用 SOCKS5 代理测试
curl --proxy socks5://127.0.0.1:10829 https://ipinfo.io
```

### 浏览器配置

1. **HTTP 代理**:
   - 代理服务器: `127.0.0.1`
   - 端口: `10828`
   - 类型: HTTP

2. **SOCKS5 代理**:
   - 代理服务器: `127.0.0.1`
   - 端口: `10829`
   - 类型: SOCKS5

### 应用程序配置

大多数支持代理的应用程序都可以使用以下配置：

- **HTTP 代理**: `http://127.0.0.1:10828`
- **SOCKS5 代理**: `socks5://127.0.0.1:10829`

## 容器管理

脚本运行完成后，会在 `./v2ray-docker/` 目录下生成配置文件。你可以使用以下命令管理容器：

```bash
# 进入配置目录
cd ./v2ray-docker/

# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止容器
docker-compose down

# 重启容器
docker-compose restart

# 重新启动（拉取最新镜像）
docker-compose down
docker-compose pull
docker-compose up -d
```

## 故障排除

### 常见问题

1. **Docker权限问题**
   ```bash
   sudo usermod -aG docker $USER
   # 重新登录或重启终端
   ```

2. **端口被占用**
   ```bash
   # 查看端口占用
   sudo netstat -tlnp | grep :10828
   # 或使用其他端口
   python3 v2ray_docker_setup.py -p 8080
   ```

3. **容器启动失败**
   ```bash
   # 查看详细日志
   cd v2ray-docker && docker-compose logs
   
   # 重新构建
   docker-compose down
   docker-compose up -d
   ```

4. **V2Ray命令错误**
   如果看到 `v2ray /usr/bin/v2ray: unknown command` 错误：
   ```bash
   # 停止容器
   docker-compose down
   
   # 清理镜像缓存
   docker system prune -f
   
   # 重新启动
   python3 v2ray_docker_setup.py -u "your_vmess_link"
   ```

5. **代理连接失败**
   ```bash
   # 使用内置测试功能
   python3 v2ray_docker_setup.py -u "your_vmess_link" --test-connection
   
   # 手动测试代理
   curl --proxy http://127.0.0.1:10828 https://ipinfo.io
   
   # 检查防火墙
   sudo ufw status
   ```

6. **查看详细日志**
   ```bash
   # 启用详细日志模式
   python3 v2ray_docker_setup.py -u "your_vmess_link" --verbose
   
   # 查看日志文件
   cat v2ray_setup.log
   ```

7. **容器健康检查失败**
   ```bash
   # 检查容器状态
   docker ps -a
   
   # 查看容器详细信息
   docker inspect v2ray-proxy
   
   # 重启容器
   docker-compose restart
   ```

## 配置文件说明

脚本会生成以下文件：

- `./v2ray-docker/config.json` - V2Ray 配置文件
- `./v2ray-docker/docker-compose.yml` - Docker Compose 配置

## 安全注意事项

1. 代理服务只绑定到本地地址（127.0.0.1），不会暴露到外网
2. 没有设置认证，请确保只在可信环境中使用
3. 定期更新 V2Ray 镜像以获取安全更新

## 系统要求

- Ubuntu 24.04 LTS
- Python 3.x
- Docker 和 Docker Compose
- 至少 100MB 可用磁盘空间

## 许可证

本脚本仅供学习和合法用途使用。请遵守当地法律法规。