"""RAG 数据库服务层 - 纯向量检索接口。

外部 YOLO 部署侧通过调用本模块的函数，将检测到的缺陷特征
（embedding 向量 + 元数据）写入或检索 ChromaDB，获取历史参考信息。

使用方式（在 YOLO 部署侧）：
    from ommateum.services.rag_bridge import index_defect, retrieve_similar
"""

import uuid
from typing import Any

from ..database.chroma_client import get_or_create_collection

COLLECTION_NAME = "defect_samples"


def index_defect(
    embedding: list[float],
    metadata: dict[str, Any] | None = None,
    record_id: str | None = None,
) -> str:
    """将缺陷特征存入 ChromaDB。"""
    rid = record_id or str(uuid.uuid4())
    collection = get_or_create_collection(COLLECTION_NAME)
    collection.add(ids=[rid], embeddings=[embedding], metadatas=metadata or {})
    return rid


def retrieve_similar(
    query_embedding: list[float],
    top_k: int = 5,
    filter_criteria: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """检索与查询向量最相似的历史缺陷记录。"""
    collection = get_or_create_collection(COLLECTION_NAME)
    total = collection.count()
    if total == 0:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, total),
        where=filter_criteria,
        include=["metadatas", "distances"],
    )

    records = []
    for rid, meta, dist in zip(
        results["ids"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        records.append({
            "id": rid,
            "metadata": meta,
            "distance": round(dist, 4),
        })
    return records


def update_defect(record_id: str, metadata: dict[str, Any]) -> None:
    """更新已有缺陷的元数据。"""
    collection = get_or_create_collection(COLLECTION_NAME)
    collection.update(ids=[record_id], metadatas=[metadata])


def delete_defect(record_id: str) -> None:
    """删除指定缺陷记录。"""
    collection = get_or_create_collection(COLLECTION_NAME)
    collection.delete(ids=[record_id])


def count_defects(filter_criteria: dict[str, Any] | None = None) -> int:
    """统计缺陷记录总数，可选按条件过滤。"""
    collection = get_or_create_collection(COLLECTION_NAME)
    return collection.count() if filter_criteria is None else len(
        collection.get(where=filter_criteria)["ids"]
    )
