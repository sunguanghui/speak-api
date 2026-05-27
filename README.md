# 🎙️ Speak TTS API (Ghost-TTS)

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**Speak TTS API** 是一个极简、极速且支持“阅后即焚”的文本转语音（Text-to-Speech）中继 API 网关。

本项目专为**高并发场景和第三方系统无缝对接**而设计。它通过异步架构将请求转发至底层的 Cloudflare Worker (Edge TTS)，并在本地实现基于 MD5 指纹的智能哈希缓存与自动生命周期管理。

---

## ✨ 核心特性 (Key Features)

- 🚀 **极速响应 (MD5 哈希缓存)**：自动为请求参数（文本、音色、语速等）生成唯一指纹。完全相同的请求将跳过底层合成，实现 **毫秒级 (ms) 直出**。
- 👻 **阅后即焚 (TTL 自动管理)**：生成的 MP3 文件默认保留 24 小时（可配）。内置后台守护线程，自动清理过期且无人访问的音频，**拒绝硬盘空间刺客**。
- ⚡ **异步非阻塞架构**：底层基于 `FastAPI` + `httpx` 构建，完美支持多用户高并发请求。
- 🔄 **智能续期机制**：只要音频文件被再次请求或播放，其 24 小时生命周期将自动重置。高频音频永远在线，低频音频安静消亡。
- 🐳 **开箱即用 (Docker)**：提供针对国内网络优化的 `Dockerfile` 与 `docker-compose.yml`，一键拉起服务。

---

## 🛠️ 快速部署 (Quick Start)

推荐使用 Docker Compose 进行部署，以获得最佳的隔离性和可维护性。

### 1. 准备配置文件

在项目根目录创建或修改 `.env` 文件，填入你的配置：

```ini
# .env

# 1. 核心接口配置 (必须替换为你自己的 Cloudflare Worker 域名)
WORKER_URL=[https://你的域名.workers.dev/v1/audio/speech](https://你的域名.workers.dev/v1/audio/speech)
# 对外服务的公网基准链接 (用于拼接返回给第三方的直链)
PUBLIC_BASE_URL=[https://speak.你的域名.com](https://speak.你的域名.com)

# 2. 存储与清理配置
STORAGE_DIR=mp3
MAX_AGE_SECONDS=86400  # 音频默认保留时长 (86400秒 = 1天)

# 3. TTS 默认参数配置
DEFAULT_VOICE=zh-CN-XiaoxiaoNeural
DEFAULT_SPEED=1.0
DEFAULT_PITCH=0
DEFAULT_STYLE=general
DEFAULT_VOLUME=0

```

### 2. 一键启动

在包含 `docker-compose.yml` 的目录下执行以下命令：

```bash
docker compose up -d --build

```

服务将在 `35000` 端口启动，并自动映射宿主机的 `./mp3` 目录。

---

## 📖 API 接口文档 (API Reference)

完整的 OpenAPI 规范与在线调试界面，可在服务启动后访问 `http://<YOUR_IP>:35000/docs` 查看。

### 1. 文字转语音直链生成

* **接口**: `POST /tts`
* **Content-Type**: `application/json`

**请求体示例:**

```json
{
  "input": "支付成功，收款十元",
  "voice": "zh-CN-XiaoxiaoNeural",
  "speed": 1.0
}

```

**响应示例:**

```json
{
  "code": 200,
  "msg": "success", 
  "expire_in": "86400 seconds",
  "url": "[https://speak.你的域名.com/audio_c4ca4238a0b923820dcc509a6f75849b.mp3](https://speak.你的域名.com/audio_c4ca4238a0b923820dcc509a6f75849b.mp3)"
}

```

*注：如果该参数请求曾被生成过，`msg` 将返回 `"success (cache hit)"`，直接返回已存在的链接。*

### 2. 音频播放与访问

* **接口**: `GET /{filename}`
* **说明**: 直接访问 `/tts` 接口返回的 URL。每次访问均会自动刷新该文件的生存时间（TTL）。

---

## ⚙️ 架构说明 (Architecture)

1. **请求接入**：第三方工作流或前端应用发送带文本的 JSON 请求。
2. **指纹校验**：系统计算 MD5 指纹，若命中本地 `./mp3` 缓存，直接刷新最后访问时间并返回公网直链。
3. **异步穿透**：未命中缓存时，系统异步请求 Cloudflare Worker 节点处理 Edge TTS 任务。
4. **流式落盘**：拿到完整的 MP3 流后，以 MD5 命名落盘，返回静态直链供第三方直接消费。

---

## 🤝 鸣谢 (Acknowledgements)

本项目的核心基础框架与最初的灵感源自于优秀的开源项目 **[wangwangit/tts](https://github.com/wangwangit/tts)**。

在此对原作者及所有开源社区贡献者表示最诚挚的感谢！没有开源社区的无私奉献，就没有本项目的诞生。

本项目在原仓库的基础上进行了深度重构与二次开发，主要增加了以下特性：

* 引入了基于 `FastAPI` 的异步非阻塞架构。
* 增加了基于 MD5 指纹的哈希缓存极速响应机制。
* 引入了自动生命周期管理（阅后即焚）与高频访问续期逻辑。
* 专门针对第三方 Webhook 与系统间调用进行了网络配置与架构优化。

---

## 📝 许可协议 (License)

本项目遵循 [MIT License](https://www.google.com/search?q=LICENSE) 开源协议。

```