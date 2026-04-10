# V2Ray Docker Setup - 增强版

这是一个增强版的V2Ray Docker一键启动脚本，支持多种代理协议的解析和统一转换。

## 新增功能

### 支持的代理类型

1. **VMess协议** - 原有功能
   ```
   vmess://base64_encoded_config
   ```

2. **SOCKS代理** - 新增
   ```
   socks://username:password@server:port#remark
   socks://base64_encoded_auth@server:port#remark
   ```

3. **HTTP代理** - 新增
   ```
   http://username:password@server:port
   ```

### 统一输出

无论输入什么类型的代理，脚本都会生成统一的本地代理服务：
- **HTTP代理端口**: 默认 10828
- **SOCKS5代理端口**: 默认 10829

## 使用示例

### 1. SOCKS代理
```bash
python v2ray_docker_setup.py -u "socks://cHdqcTU0NzgzLXJlZ2lvbi1TRzpxdTN6YXVjNA%3D%3D@sg.cliproxy.io:3010#cliproxy"
```

### 2. HTTP代理
```bash
python v2ray_docker_setup.py -u "http://user-spppy9kkam-country-us:efwhiJec4BG2g3I4~a@gate.decodo.com:7000"
```

### 3. VMess代理
```bash
python v2ray_docker_setup.py -u "vmess://ew0KICAidiI6ICIyIiwNCiAgInBzIjogIlNpbXBsZVYyUmF5IiwNCiAgImFkZCI6ICIxNTkuNzUuMTIzLjk2IiwNCiAgInBvcnQiOiAiNDc4NjYiLA0KICAiaWQiOiAiY2I4NDNiNjAtNjQxMi00ZGY1LTlmMTUtMTA4ZjE4ZjM0NGZiIiwNCiAgImFpZCI6ICIwIiwNCiAgInNjeSI6ICJhdXRvIiwNCiAgIm5ldCI6ICJ0Y3AiLA0KICAidHlwZSI6ICJub25lIiwNCiAgImhvc3QiOiAiIiwNCiAgInBhdGgiOiAiIiwNCiAgInRscyI6ICIiLA0KICAic25pIjogIiIsDQogICJhbHBuIjogIiIsDQogICJmcCI6ICIiDQp9"
```

## 命令行参数

```bash
python v2ray_docker_setup.py [选项]

选项:
  -u, --url URL          代理配置链接 (支持 vmess://, socks://, http://)
  -p, --port PORT        本地代理端口 (默认: 10828, SOCKS端口为此端口+1)
  --config-dir DIR       配置文件目录 (默认: ./v2ray-docker)
  -v, --verbose          启用详细日志记录
  --test-connection      启动后测试代理连接
  -h, --help            显示帮助信息
```

## 代理URL格式说明

### SOCKS代理URL格式
- 基本格式: `socks://server:port`
- 带认证: `socks://username:password@server:port`
- 带备注: `socks://username:password@server:port#remark`
- Base64编码认证: `socks://base64_encoded_auth@server:port#remark`

### HTTP代理URL格式
- 基本格式: `http://server:port`
- 带认证: `http://username:password@server:port`

### VMess代理URL格式
- 标准格式: `vmess://base64_encoded_json_config`

## 测试功能

运行测试脚本验证解析功能：
```bash
python test_proxy_parsing.py
```

查看使用示例：
```bash
python example_usage.py
```

## 生成的配置文件

脚本会在指定目录生成以下文件：
- `config.json` - V2Ray配置文件
- `docker-compose.yml` - Docker Compose配置

## 使用生成的代理

启动成功后，可以使用以下方式连接：

### HTTP代理
```bash
curl --proxy http://127.0.0.1:10828 https://ipinfo.io
```

### SOCKS5代理
```bash
curl --proxy socks5://127.0.0.1:10829 https://ipinfo.io
```

## 管理命令

```bash
# 停止服务
cd v2ray-docker && docker-compose down

# 重启服务
cd v2ray-docker && docker-compose restart

# 查看日志
cd v2ray-docker && docker-compose logs -f

# 查看状态
cd v2ray-docker && docker-compose ps
```

## 技术实现

### 新增的解析函数
- `parse_socks_url()` - 解析SOCKS代理URL
- `parse_http_url()` - 解析HTTP代理URL
- `detect_proxy_type()` - 自动检测代理类型

### 增强的配置生成
- `generate_v2ray_config()` - 支持多种代理类型的配置生成
- 统一的入站配置（HTTP + SOCKS5）
- 根据代理类型生成相应的出站配置

## 注意事项

1. 需要Docker和docker-compose环境
2. 确保指定的端口未被占用
3. SOCKS代理URL中的认证信息支持URL编码和Base64编码
4. 所有代理类型都会转换为本地的HTTP和SOCKS5代理

## 错误处理

脚本包含完整的错误处理机制：
- URL格式验证
- 端口可用性检查
- Docker环境检测
- 配置文件生成验证
- 容器启动状态监控