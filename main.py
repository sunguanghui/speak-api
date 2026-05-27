import os
import time
import hashlib
import threading
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# ================= 1. 加载与初始化配置 =================
load_dotenv()

# 核心与存储配置
WORKER_URL = os.getenv("WORKER_URL", "https://tts.gptclub.top/v1/audio/speech")
# 【修改点1】：默认保留时间调整为 86400 秒（即 1 天）
MAX_AGE_SECONDS = int(os.getenv("MAX_AGE_SECONDS", 86400))
STORAGE_DIR = os.getenv("STORAGE_DIR", "mp3")

# TTS 默认参数
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "zh-CN-XiaoxiaoNeural")
DEFAULT_SPEED = float(os.getenv("DEFAULT_SPEED", 1.0))
DEFAULT_PITCH = os.getenv("DEFAULT_PITCH", "0")
DEFAULT_STYLE = os.getenv("DEFAULT_STYLE", "general")
DEFAULT_VOLUME = os.getenv("DEFAULT_VOLUME", "0")

# 确保音频存放目录存在
os.makedirs(STORAGE_DIR, exist_ok=True)

# ================= 2. 后台清理机制 =================
def cleanup_old_files():
    """后台线程：每 10 分钟扫描一次，清理过期音频"""
    while True:
        try:
            current_time = time.time()
            for filename in os.listdir(STORAGE_DIR):
                file_path = os.path.join(STORAGE_DIR, filename)
                # 仅处理 mp3 文件
                if os.path.isfile(file_path) and filename.endswith(".mp3"):
                    # 如果当前时间减去文件的最后修改时间，超过了设定的最大存活时间，则删除
                    if current_time - os.path.getmtime(file_path) > MAX_AGE_SECONDS:
                        os.remove(file_path)
                        print(f"[清理机制] 已自动删除长时间未访问的文件: {filename}")
        except Exception as e:
            print(f"[清理机制] 扫描出错: {e}")
        time.sleep(600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 正在启动后台自动清理服务 (清理周期: {MAX_AGE_SECONDS}秒, 目录: {STORAGE_DIR})...")
    threading.Thread(target=cleanup_old_files, daemon=True).start()
    yield
    print("🛑 服务正在关闭...")

# ================= 3. FastAPI 路由配置 =================
app = FastAPI(title="Speak TTS API", lifespan=lifespan)

# 请求参数模型映射
class TTSRequest(BaseModel):
    input: str
    voice: str = DEFAULT_VOICE
    speed: float = DEFAULT_SPEED
    pitch: str = DEFAULT_PITCH
    style: str = DEFAULT_STYLE
    volume: str = DEFAULT_VOLUME

@app.post("/tts")
async def generate_audio_link(request: Request, params: TTSRequest):
    """
    核心接口：[异步] 请求底层 TTS 并在目录下生成限时存在的 MP3 直链，支持哈希缓存机制
    """
    # 【修改点2】：使用所有参数生成唯一 MD5 指纹，作为哈希缓存的文件名
    raw_str = f"{params.input}_{params.voice}_{params.speed}_{params.pitch}_{params.style}_{params.volume}"
    file_md5 = hashlib.md5(raw_str.encode('utf-8')).hexdigest()
    file_name = f"audio_{file_md5}.mp3"
    file_path = os.path.join(STORAGE_DIR, file_name)
    
    # 拼装直链 (端口硬编码为 35000)
    host = request.headers.get("host", "127.0.0.1:35000")
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    mp3_url = f"{scheme}://{host}/{file_name}"

    # 【修改点3】：检查缓存是否存在
    if os.path.exists(file_path):
        # 如果文件存在，更新文件的修改时间和访问时间为“当前时间”
        # 这会让清理线程重新计算过期时间，从而实现“只要被调用就自动续命1天”
        os.utime(file_path, None)
        return {
            "code": 200,
            "msg": "success (cache hit)",
            "expire_in": f"{MAX_AGE_SECONDS} seconds",
            "url": mp3_url
        }

    # 如果没命中缓存，才去请求底层服务
    payload = params.model_dump()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(WORKER_URL, json=payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"请求底层 TTS 服务失败: {str(e)}")

    if response.status_code == 200:
        # 保存音频流
        with open(file_path, "wb") as f:
            f.write(response.content)
        
        return {
            "code": 200,
            "msg": "success",
            "expire_in": f"{MAX_AGE_SECONDS} seconds",
            "url": mp3_url
        }
    else:
        raise HTTPException(status_code=response.status_code, detail=f"底层服务报错: {response.text}")

@app.get("/{filename}")
def get_mp3_file_directly(filename: str):
    """
    直链解析接口：直接返回 .mp3 音频流，并自动刷新文件存活时间
    """
    if not filename.endswith(".mp3"):
        raise HTTPException(status_code=400, detail="只支持访问 mp3 文件")
        
    file_path = os.path.join(STORAGE_DIR, filename)
    if os.path.exists(file_path):
        # 【修改点4】：只要有人访问/播放了这个音频链接，就刷新它的修改时间
        # 同样实现“高频播放，自动续命”的机制
        os.utime(file_path, None)
        return FileResponse(file_path, media_type="audio/mpeg")
    
    raise HTTPException(status_code=404, detail="该音频文件不存在或已过期被自动销毁")

# ================= 4. 服务启动入口 =================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=35000, reload=False)
