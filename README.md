# xray-script

用 Python 一键拉起 **Xray** 的 Docker Compose 部署脚本：服务端走 **REALITY**，客户端根据订阅/分享链接在本地暴露 **HTTP + SOCKS5**（无认证）。

## 环境要求

- **Python 3**
- **Docker**，且已安装 **Compose 插件**（`docker compose`）
- 镜像默认使用 `ghcr.io/xtls/xray-core:latest`；若拉取困难可使用 `--mirror` 或脚本内置的国内镜像逻辑（见下文）

## 服务端：`server.py`

在 VPS 上部署 Xray **入站 REALITY**，无需自备域名与证书（TLS 伪装）。

```bash
python server.py                          # 443，默认伪装 www.microsoft.com
python server.py --port 8443              # 非特权端口
python server.py --dest www.apple.com:443 --fp safari
python server.py --mirror ghcr.nju.edu.cn # 指定 ghcr 镜像前缀（大陆网络）
python server.py --stop
```

常用参数：

| 参数 | 说明 |
|------|------|
| `--port` | 监听端口，默认 `443` |
| `--dest` | REALITY 目标站点，默认 `www.microsoft.com:443` |
| `--fp` | 指纹，默认 `chrome` |
| `--ip` | 可选，绑定/展示用 IP |
| `--mirror` | ghcr.io 镜像主机（如 `ghcr.nju.edu.cn`） |
| `--config-dir` | 配置与 compose 目录，默认 `./xray-server` |
| `--stop` | 停止当前 compose 栈 |

## 客户端：`client.py`

根据**代理分享链接**生成本地 Xray 配置，并用 Docker Compose 运行；本机得到 **SOCKS5 + HTTP** 合一端口（无认证）。

```bash
python client.py 'vless://...'
python client.py 'vmess://...' --port 10828
python client.py 'vless://...' --mirror ghcr.nju.edu.cn
python client.py --stop
```

常用参数：

| 参数 | 说明 |
|------|------|
| `url` | `vmess` / `vless` / `trojan` / `socks` / `socks5` / `http` 等形式链接 |
| `--port` | 本地监听端口，默认 `10808` |
| `--mirror` | ghcr.io 镜像主机 |
| `--config-dir` | 默认 `./xray-client` |
| `--stop` | 停止客户端 compose |

### 支持的链接格式（节选）

- `vmess://...`
- `vless://uuid@host:port?security=reality&pbk=...&sid=...&sni=...&fp=chrome`
- `vless://uuid@host:port?security=tls&sni=...`
- `trojan://password@host:443?security=tls&sni=...`
- `socks://`、`socks5://`（可选 `user:pass@`）
- `http://`（可选 `user:pass@`）

启动后在本机使用：`127.0.0.1:<port>` 作为 HTTP 或 SOCKS5 代理。

## 国内网络说明

- **ghcr.io**：可用 `--mirror ghcr.nju.edu.cn` 等；脚本也会在无法直连时尝试内置 ghcr 镜像列表。
- **Docker Hub**：在 Linux 且 root 时，可能会尝试写入 `/etc/docker/daemon.json` 配置 registry-mirrors（详见脚本内注释）。

## 其他

- 历史脚本与文档在目录 **`trash/`** 中保留，日常只需关注根目录的 `client.py` 与 `server.py`。
- 更细的参数与行为以脚本顶部 **docstring** 为准。

## 仓库

<https://github.com/maximo896/xray-script>
