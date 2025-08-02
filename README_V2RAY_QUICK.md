# V2Ray 快速启动脚本

一个简化的V2Ray启动脚本，支持一键解析和启动多种代理类型。

## 🚀 快速开始

### 基本用法
```bash
python v2ray.py <proxy_url>
```

### 支持的代理类型

#### 1. SOCKS代理
```bash
python v2ray.py "socks://cHdqcTU0NzgzLXJlZ2lvbi1TRzpxdTN6YXVjNA%3D%3D@sg.cliproxy.io:3010#cliproxy"
```

#### 2. HTTP代理
```bash
python v2ray.py "http://user:pass@proxy.example.com:8080"
```

#### 3. VMess代理
```bash
python v2ray.py "vmess://base64_encoded_config"
```

## 📋 功能特点

- ✅ **自动解析**: 支持SOCKS、HTTP、VMess三种代理格式
- ✅ **智能端口**: 自动查找可用端口，避免冲突
- ✅ **统一输出**: 提供HTTP和SOCKS5两种本地代理端口
- ✅ **Docker集成**: 自动生成Docker配置并启动容器
- ✅ **错误处理**: 完善的错误检测和解决方案提示

## 🔧 环境要求

1. **Python 3.6+**
2. **Docker Desktop** (Windows/Mac) 或 **Docker + Docker Compose** (Linux)

### Docker安装
- Windows/Mac: [Docker Desktop](https://www.docker.com/products/docker-desktop)
- Linux: 
  ```bash
  sudo apt update
  sudo apt install docker.io docker-compose
  sudo systemctl start docker
  sudo usermod -aG docker $USER
  ```

## 📖 使用示例

### 启动SOCKS代理
```bash
$ python v2ray.py "socks://cHdqcTU0NzgzLXJlZ2lvbi1TRzpxdTN6YXVjNA%3D%3D@sg.cliproxy.io:3010#cliproxy"

🚀 V2Ray 快速启动
========================================
📋 解析代理配置...
   类型: SOCKS
   服务器: sg.cliproxy.io:3010
   备注: cliproxy

🔍 查找可用端口...
   HTTP端口: 10828
   SOCKS端口: 10829

⚙️  生成V2Ray配置...
   配置已保存到: ./v2ray-quick

🐳 启动Docker容器...
✅ 启动成功!
========================================
HTTP代理:  http://127.0.0.1:10828
SOCKS代理: socks5://127.0.0.1:10829
```

### 使用生成的代理
```bash
# 测试HTTP代理
curl --proxy http://127.0.0.1:10828 https://ipinfo.io

# 测试SOCKS5代理
curl --proxy socks5://127.0.0.1:10829 https://ipinfo.io
```

## 🛠️ 管理命令

```bash
# 停止服务
cd v2ray-quick && docker compose down

# 查看日志
cd v2ray-quick && docker compose logs -f

# 重启服务
cd v2ray-quick && docker compose restart

# 查看状态
cd v2ray-quick && docker compose ps
```

## 📁 生成的文件

脚本会在 `./v2ray-quick/` 目录下生成：

- `config.json` - V2Ray配置文件
- `docker-compose.yml` - Docker Compose配置

## 🔍 代理URL格式说明

### SOCKS代理格式
```
socks://[username:password@]host:port[#remark]
```

支持Base64编码的用户名:密码组合：
```
socks://base64_encoded_auth@host:port#remark
```

### HTTP代理格式
```
http://[username:password@]host:port
```

### VMess代理格式
```
vmess://base64_encoded_json_config
```

## ⚠️ 常见问题

### 1. Docker未安装
```
❌ Docker未安装或未启动

💡 解决方案:
1. 安装Docker Desktop
2. 确保Docker服务正在运行
3. 重新启动终端
```

### 2. 端口被占用
脚本会自动查找可用端口，从10828开始递增。

### 3. 启动失败
检查Docker日志：
```bash
cd v2ray-quick && docker compose logs
```

## 🎯 设计理念

这个脚本的设计目标是**简单易用**：

1. **一条命令启动**: 无需复杂配置
2. **自动化处理**: 端口检测、配置生成、容器启动
3. **统一接口**: 不同代理类型，相同使用方式
4. **清晰反馈**: 详细的状态信息和错误提示

## 📝 技术实现

- **URL解析**: 支持标准URL格式和Base64编码
- **端口管理**: 智能端口分配，避免冲突
- **Docker集成**: 自动生成配置，容器化部署
- **错误处理**: 完善的异常捕获和用户友好的错误信息

---

**享受快速、简单的代理启动体验！** 🎉