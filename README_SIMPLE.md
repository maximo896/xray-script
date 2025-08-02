# V2Ray 极简服务器一键搭建脚本 v2.0

🚀 **零配置、一键部署、随机端口、支持国内镜像源**

## ✨ 新版本特性

- 🎲 **随机端口生成** - 自动检测可用端口，避免冲突
- 🐳 **Docker镜像源支持** - 解决国内拉取镜像慢的问题
- 🔧 **命令行参数** - 支持自定义配置
- 🤖 **非交互模式** - 适合自动化部署
- 🌐 **网络检测** - 智能推荐镜像源

## 🚀 快速开始

### 方法一：使用启动脚本（推荐）

```bash
# 默认配置（随机端口 + 自动检测镜像源）
./start_simple.sh

# 使用阿里云镜像源
./start_simple.sh -m registry.cn-hangzhou.aliyuncs.com

# 指定端口
./start_simple.sh -p 8080

# 非交互模式 + 网易云镜像源
./start_simple.sh -n -m hub-mirror.c.163.com
```

### 方法二：直接运行Python脚本

```bash
# 默认配置
python3 simple_v2ray_server.py

# 使用镜像源
python3 simple_v2ray_server.py --mirror registry.cn-hangzhou.aliyuncs.com

# 指定端口
python3 simple_v2ray_server.py --port 8080

# 非交互模式
python3 simple_v2ray_server.py --no-input
```

## 📋 命令行参数

### Bash脚本参数

| 参数 | 长参数 | 说明 | 示例 |
|------|--------|------|------|
| `-p` | `--port` | 指定端口号 | `-p 8080` |
| `-m` | `--mirror` | Docker镜像源地址 | `-m registry.cn-hangzhou.aliyuncs.com` |
| `-n` | `--no-input` | 非交互模式 | `-n` |
| `-h` | `--help` | 显示帮助信息 | `-h` |

### Python脚本参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--port` | 指定端口号 | `--port 8080` |
| `--mirror` | Docker镜像源地址 | `--mirror registry.cn-hangzhou.aliyuncs.com` |
| `--no-input` | 非交互模式 | `--no-input` |
| `--config-dir` | 配置文件目录 | `--config-dir ./my-v2ray` |

## 🐳 常用Docker镜像源

| 提供商 | 镜像源地址 | 说明 |
|--------|------------|------|
| 阿里云 | `registry.cn-hangzhou.aliyuncs.com` | 推荐，速度快 |
| 腾讯云 | `ccr.ccs.tencentyun.com` | 稳定可靠 |
| 华为云 | `swr.cn-north-4.myhuaweicloud.com` | 企业级 |
| 网易云 | `hub-mirror.c.163.com` | 老牌镜像源 |

## 📱 使用示例

### 场景一：国内服务器快速部署

```bash
# 使用阿里云镜像源，非交互模式
./start_simple.sh -n -m registry.cn-hangzhou.aliyuncs.com
```

### 场景二：指定端口部署

```bash
# 使用8080端口
./start_simple.sh -p 8080
```

### 场景三：完全自动化部署

```bash
# 随机端口 + 自动检测最佳镜像源
./start_simple.sh -n
```

## 🔧 服务器管理

```bash
# 查看容器状态
docker ps

# 查看日志
cd v2ray-simple && docker-compose logs -f

# 停止服务
cd v2ray-simple && docker-compose down

# 重启服务
cd v2ray-simple && docker-compose restart

# 完全清理
cd v2ray-simple && docker-compose down -v
rm -rf v2ray-simple
```

## 🛠️ 故障排除

### 问题1：Docker镜像拉取失败

**解决方案：**
```bash
# 使用国内镜像源
./start_simple.sh -m registry.cn-hangzhou.aliyuncs.com
```

### 问题2：端口被占用

**解决方案：**
```bash
# 使用随机端口（默认行为）
./start_simple.sh

# 或指定其他端口
./start_simple.sh -p 9999
```

### 问题3：网络检测超时

**解决方案：**
```bash
# 使用非交互模式跳过网络检测
./start_simple.sh -n -m registry.cn-hangzhou.aliyuncs.com
```

## 💡 最佳实践

1. **国内服务器**：建议使用阿里云镜像源
   ```bash
   ./start_simple.sh -m registry.cn-hangzhou.aliyuncs.com
   ```

2. **自动化部署**：使用非交互模式
   ```bash
   ./start_simple.sh -n
   ```

3. **生产环境**：指定固定端口便于防火墙配置
   ```bash
   ./start_simple.sh -p 8080
   ```

4. **云服务器**：记得在安全组开放对应端口

## 🔒 安全建议

- 定期更换UUID和端口
- 使用防火墙限制访问来源
- 定期更新V2Ray版本
- 不要在公共网络分享vmess链接

## 📄 许可证

MIT License

## 🆘 支持

如有问题，请检查：
1. Docker是否正确安装
2. 端口是否被占用
3. 网络连接是否正常
4. 防火墙设置是否正确