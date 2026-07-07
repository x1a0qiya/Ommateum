"""RAG 辅助 YOLO 训练 - 主动学习与难例挖掘模块。

利用 ChromaDB 中的历史缺陷分布，指导 YOLO 训练集的扩充和优化。
"""

from ..database.chroma_client import get_or_create_collection
from .rag_bridge import (
    COLLECTION_NAME,
    retrieve_similar,
)


def find_novel_defects(
    embedding: list[float],
    similarity_threshold: float = 0.7,
) -> bool:
    """判断当前缺陷是否"新颖"（与历史库相似度低）。

    新颖样本属于长尾/罕见缺陷，建议优先标注并加入训练集。
    """
    results = retrieve_similar(embedding, top_k=1)
    if not results:
        return True
    return results[0]["distance"] > similarity_threshold


def get_underrepresented_labels(top_k: int = 5) -> list[dict]:
    """统计各缺陷类别的数量，返回最稀缺的类别。

    用于指导 YOLO 训练数据平衡，优先采集/合成稀缺类别样本。
    """
    collection = get_or_create_collection(COLLECTION_NAME)
    all_meta = collection.get(include=["metadatas"])["metadatas"]

    counts: dict[str, int] = {}
    for meta in all_meta:
        label = meta.get("label", "unknown")
        counts[label] = counts.get(label, 0) + 1

    sorted_labels = sorted(counts.items(), key=lambda x: x[1])
    return [
        {"label": label, "count": count}
        for label, count in sorted_labels[:top_k]
    ]


def get_hard_negatives(
    embedding: list[float],
    top_k: int = 10,
) -> list[dict]:
    """检索容易误检的相似负样本（人工确认的误报）。

    将这些样本加入 YOLO 训练集作为负样本，可有效减少误检率。
    """
    collection = get_or_create_collection(COLLECTION_NAME)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        where={"is_false_positive": True},
        include=["metadatas", "distances"],
    )

    return [
        {"id": rid, "metadata": meta, "distance": round(dist, 4)}
        for rid, meta, dist in zip(
            results["ids"][0], results["metadatas"][0], results["distances"][0]
        )
    ]
