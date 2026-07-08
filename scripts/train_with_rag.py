"""RAG 辅助 YOLO 训练完整流程。

⚠️ 这是一个示意脚本，需要根据实际数据和路径调整。

核心思想：
  1. 训练前 → 用 RAG 分析历史缺陷分布，辅助数据准备
  2. 训练中 → YOLO 正常训练，RAG 不参与
  3. 训练后 → 用 RAG 存储验证集缺陷特征，用于后续迭代


在 YOLO 部署侧的使用步骤：

  step 1 ── 分析数据库，了解缺陷分布
      python scripts/train_with_rag.py analyze

  step 2 ── 准备平衡后的数据集
      python scripts/train_with_rag.py prepare

  step 3 ── 训练 YOLO（标准训练，RAG不参与）
      yolo train model=yolo11n.pt data=balanced_data.yaml epochs=100

  step 4 ── 验证后，将新检测结果存入RAG
      python scripts/train_with_rag.py index --image_dir ./val_images
"""

import argparse
from pathlib import Path
from ultralytics import YOLO
from PIL import Image
from ommateum import get_underrepresented_labels, index_defect
from ommateum.utils.embedding import extract_embedding

def compute_weights(scarce_items, gamma=2.0):
    """
    修正的 Focal Loss 风格权重计算

    原理：
    - 样本占比越大 → 权重越低（因为是"容易"的类别）
    - 样本占比越小 → 权重越高（因为是"困难"的类别）
    - gamma 控制不平衡的惩罚程度
    """
    weights = {}
    total = sum(item["count"] for item in scarce_items)

    if total == 0:
        return {item["label"]: 1.0 for item in scarce_items}

    # 先计算原始权重
    raw_weights = {}
    for item in scarce_items:
        ratio = item["count"] / total  # 样本占比，范围 [0, 1]

        weight = 1.0 / (ratio ** gamma + 1e-6)

        raw_weights[item["label"]] = weight

    if raw_weights:
        min_weight = min(raw_weights.values())
        if min_weight > 0:
            for label in raw_weights:
                weights[label] = round(raw_weights[label] / min_weight, 2)
        else:
            weights = {k: round(v, 2) for k, v in raw_weights.items()}

    return weights

def step_analyze():
    """step 1: 分析 RAG 数据库中的缺陷分布。"""

    print("=" * 50)
    print("RAG 分析：缺陷类别分布")

    scarce = get_underrepresented_labels(top_k=5)
    if not scarce:
        print("  ChromaDB 中暂无缺陷数据，请先通过在线检测积累或导入历史数据。")
        return

    print(f"  最稀缺的 {len(scarce)} 个类别：")
    for item in scarce:
        print(f"    - {item['label']}: 仅 {item['count']} 条记录")
    print("  → 建议优先收集 / 合成这些类别的样本加入训练集。")
    print("=" * 50)


def step_prepare():
    """step 2: 根据 RAG 分析结果，辅助生成平衡数据集配置。"""

    print("=" * 50)
    print("RAG 辅助数据准备")

    scarce = get_underrepresented_labels()  # 注意：保持变量名为 scarce
    if not scarce:
        print("  数据库为空，使用原始数据配置。")
        return

    # 计算总样本数（修复：添加 total 变量）
    total = sum(item["count"] for item in scarce)

    # 生成权重策略：稀缺类别在 loss 中获得更高权重
    print("\n  类别分布统计：")
    for item in scarce:
        ratio = item["count"] / total
        print(f"    {item['label']}: count={item['count']}, ratio={ratio:.3f}")

    # 计算权重（修复：使用 scarce 而不是 scarce_items）
    weights = compute_weights(scarce, gamma=2.0)
    print("\n  建议的类别权重（用于缓解样本不平衡）：")
    for label, weight in weights.items():
        count = next(item["count"] for item in scarce if item["label"] == label)
        ratio = count / total
        print(f"    {label}: ratio={ratio:.3f}, weight={weight:.2f}")

    # 生成建议的 YOLO data.yaml 内容
    print()
    print("  参考 data.yaml 配置：")
    print("  ┌────────────────────────────────────────────┐")
    print(f"  │  train: ./datasets/train/images             │")
    print(f"  │  val:   ./datasets/val/images               │")
    print(f"  │  nc: {len(scarce)}                                  │")
    # 修复：正确格式化 names 列表
    names_list = [item['label'] for item in scarce]
    names_str = str(names_list)
    print(f"  │  names: {names_str}  │")
    print("  └────────────────────────────────────────────┘")

    print("=" * 50)


def step_index_results(image_dir: str):
    """step 4: 将验证集/产线检测结果存入 RAG。"""
    from ommateum import index_defect
    from pathlib import Path
    from PIL import Image
    import numpy as np

    img_dir = Path(image_dir)
    if not img_dir.exists():
        print(f"  目录不存在: {image_dir}")
        return

    print("=" * 50)
    print("将检测结果存入 RAG 数据库")
    extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    image_files = [
        f for f in img_dir.rglob('*')
        if f.is_file() and f.suffix.lower() in extensions
    ]

    print(f"找到 {len(image_files)} 张图片")

    if not image_files:
        print(f"  目录中没有图片文件: {image_dir}")
        return

    count = 0
    for img_path in image_files:
        try:
            # 正确打开图片文件
            with Image.open(img_path) as img:
                vec = extract_embedding(img)

            label = img_path.parent.name
            if "scratch" in str(img_path).lower():
                label = "scratch"
            elif "defect" in str(img_path).lower():
                label = "defect"

            metadata = {
                "label": label,
                "source": str(img_path.name),
                "confidence": 0.95,
                "file_path": str(img_path.absolute()),
                "timestamp": str(img_path.stat().st_mtime)  # 添加时间戳
            }

            # 存入 RAG 数据库 - 使用实际的 embedding
            index_defect(embedding=vec, metadata=metadata)
            count += 1

        except Exception as e:
            print(f"  处理失败: {img_path.name} - {e}")
            continue

    print(f"  已存入 {count} 条记录到 ChromaDB")
    print("  后续训练迭代时，这些数据将用于分析稀缺类别。")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="RAG 辅助 YOLO 训练")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("analyze", help="分析数据库中的缺陷分布")
    sub.add_parser("prepare", help="根据分析结果生成数据配置建议")
    index_parser = sub.add_parser("index", help="将验证集结果存入数据库")
    index_parser.add_argument("--image_dir", required=True)

    args = parser.parse_args()

    if args.command == "analyze":
        step_analyze()
    elif args.command == "prepare":
        step_prepare()
    elif args.command == "index":
        step_index_results(args.image_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
