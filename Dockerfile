# 基础镜像 : 要求 pytorch >= 2.5.1, python >= 3.10
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-devel AS base

WORKDIR /Ommateum

# apt 下载依赖库
RUN apt-get update && apt-get install -y --no-install-recommends \
    # git 工具
    git \
    # OpenCV 依赖库
    libgl1-mesa-glx \
    libglib2.0-0 \
    # 删除安装包
    && rm -rf /var/lib/apt/lists/*

ARG INSTALL_DEV=false

# 下载依赖
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -U pip
RUN if [ "$INSTALL_DEV" = "true" ] ; then \
        pip install --no-cache-dir -r requirements-dev.txt ; \
    else \
        pip install --no-cache-dir -r requirements.txt ; \
    fi

# 开放端口
EXPOSE 8000 7860