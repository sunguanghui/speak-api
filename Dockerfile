# 使用官方轻量级 Python 3.11 镜像 (基于 Debian)
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# ==========================================
# 1. 配置 Debian 系统源为国内镜像 (阿里云)
# ==========================================
# 替换默认的 deb.debian.org 为 mirrors.aliyun.com
# 兼容 Debian 12 (Bookworm) 的 debian.sources 和老版本的 sources.list
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list 2>/dev/null || true

# 设置时区为上海，并安装 tzdata 确保时间正确
ENV TZ=Asia/Shanghai
RUN apt-get update && apt-get install -y tzdata \
    && ln -fs /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo ${TZ} > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 设置环境变量，防止 python 生成 .pyc 文件，并强制无缓冲标准输出
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ==========================================
# 2. 配置 Pip 为国内镜像源 (阿里云)
# ==========================================
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目所有源码到工作目录
COPY . .

# 暴露 FastAPI 运行的 35000 端口
EXPOSE 35000

# 启动服务
CMD ["python", "main.py"]