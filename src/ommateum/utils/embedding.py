"""Embedding 向量生成工具。

为缺陷图像提取特征向量，供 RAG 系统检索使用。
"""

import numpy as np
from PIL import Image

# ---------- 方案一：sentence-transformers + CLIP（推荐，轻量易用）----------
try:
    from sentence_transformers import SentenceTransformer

    _clip_model: SentenceTransformer | None = None

    def _get_clip_model() -> SentenceTransformer:
        global _clip_model
        if _clip_model is None:
            _clip_model = SentenceTransformer("clip-ViT-B-32")
        return _clip_model

    def embed_with_clip(image: Image.Image) -> list[float]:
        """用 CLIP 模型提取图像特征向量（512维）。"""
        vec = _get_clip_model().encode(image).tolist()
        return vec

    AVAILABLE = True

except ImportError:
    AVAILABLE = False


# ---------- 方案二：ResNet（PyTorch 兜底）----------
try:
    import torch
    import torchvision.transforms as T
    from torchvision.models import resnet50, ResNet50_Weights

    _resnet_model = None
    _resnet_transform = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    def _get_resnet_model():
        global _resnet_model
        if _resnet_model is None:
            model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V1)
            model.eval()
            _resnet_model = torch.nn.Sequential(*list(model.children())[:-1])
        return _resnet_model

    def embed_with_resnet(image: Image.Image) -> list[float]:
        """用 ResNet50 提取图像特征向量（2048维）。"""
        img_tensor = _resnet_transform(image).unsqueeze(0)
        with torch.no_grad():
            vec = _get_resnet_model()(img_tensor).squeeze().numpy().tolist()
        return vec

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


# ---------- 方案三：轻量兜底（颜色直方图）----------
def embed_fallback(image: Image.Image) -> list[float]:
    """兜底方案：颜色直方图 + 尺寸归一化，不依赖任何模型。"""
    arr = np.array(image.resize((64, 64))).flatten().astype(np.float32)
    norm = np.linalg.norm(arr)
    return (arr / norm).tolist() if norm > 0 else arr.tolist()


# ---------- 统一接口 ----------
def extract_embedding(image: Image.Image, method: str = "auto") -> list[float]:
    """统一入口：提取图像 embedding。

    Args:
        image: PIL 图像。
        method: "auto" / "clip" / "resnet" / "fallback"。

    Returns:
        特征向量（list[float]）。
    """
    if method == "clip" or (method == "auto" and AVAILABLE):
        return embed_with_clip(image)
    if method == "resnet" or (method == "auto" and HAS_TORCH):
        return embed_with_resnet(image)
    return embed_fallback(image)
