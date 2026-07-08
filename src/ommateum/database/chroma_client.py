"""ChromaDB 客户端封装，提供向量数据库的初始化与操作接口。"""

import os
from pathlib import Path

import chromadb
from chromadb.config import Settings

# 本地持久化路径
CHROMA_DB_DIR = Path(__file__).resolve().parents[3] / "data" / "chromadb"


def get_client() -> chromadb.PersistentClient:
    """获取 ChromaDB 持久化客户端（单例模式）。"""
    os.makedirs(CHROMA_DB_DIR, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(CHROMA_DB_DIR),
        settings=Settings(anonymized_telemetry=False),
    )


def get_or_create_collection(
    name: str,
    embedding_function=None,
    metadata: dict | None = None,
) -> chromadb.Collection:
    """获取或创建指定名称的集合（Collection）。"""
    client = get_client()
    return client.get_or_create_collection(
        name=name,
        embedding_function=embedding_function,
        metadata=metadata,
    )


def delete_collection(name: str) -> None:
    """删除指定集合。"""
    client = get_client()
    client.delete_collection(name)


def list_collections() -> list[str]:
    """列出所有集合名称。"""
    client = get_client()
    return [c.name for c in client.list_collections()]
