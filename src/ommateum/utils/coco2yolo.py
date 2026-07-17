#!/usr/bin/env python3
"""
COCO JSON 标注 → YOLO .txt 格式转换脚本。

读取 COCO JSON，将其中的 bbox 标注转为 YOLO 归一化格式，
在同级目录生成 labels/ 文件夹。

用法:
  python src/ommateum/models/identify/coco2yolo.py \
      --coco_json /path/to/dataset/id_0001/annotation.json

  JSON 所在目录生成 labels/，输出 YOLO .txt 文件。

Python API:
  from ommateum.models.identify.coco2yolo import coco2yolo

  names = coco2yolo(coco_json="/path/to/annotation.json")
  # → ["scratch", "crack", "dent"]
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List


def coco2yolo(coco_json: str) -> List[str]:
    """将 COCO JSON 标注转为 YOLO .txt 格式。

    在同级目录创建 labels/ 文件夹，每张图片生成一个同名 .txt。

    Args:
        coco_json: COCO 格式 JSON 文件路径。

    Returns:
        类别名称列表（按 YOLO 0-based 索引顺序）。

    Raises:
        FileNotFoundError: JSON 文件不存在。
        ValueError: JSON 缺少 categories 字段。
    """
    coco_json = os.path.abspath(coco_json)
    if not os.path.isfile(coco_json):
        raise FileNotFoundError(f"COCO JSON 不存在: {coco_json}")

    base_dir = os.path.dirname(coco_json)
    labels_dir = os.path.join(base_dir, "labels")

    with open(coco_json, "r", encoding="utf-8") as f:
        coco: Dict[str, Any] = json.load(f)

    # ── 构建 image_id → image_info 索引 ──
    images_info: Dict[int, Dict[str, Any]] = {}
    for img in coco.get("images", []):
        images_info[img["id"]] = img

    # ── 类别映射: COCO category.id → YOLO 0-based index ──
    categories = coco.get("categories", [])
    if not categories:
        raise ValueError("COCO JSON 中缺少 categories 字段")

    cat_id_to_idx: Dict[int, int] = {}
    names: Dict[int, str] = {}
    for idx, cat in enumerate(sorted(categories, key=lambda c: c["id"])):
        cat_id_to_idx[cat["id"]] = idx
        names[idx] = cat["name"]

    # ── image_id → annotations 分组 ──
    anns_by_image: Dict[int, List[Dict[str, Any]]] = {}
    for ann in coco.get("annotations", []):
        img_id = ann["image_id"]
        anns_by_image.setdefault(img_id, []).append(ann)

    os.makedirs(labels_dir, exist_ok=True)

    generated = 0
    for img_id, img_info in images_info.items():
        img_w = img_info["width"]
        img_h = img_info["height"]
        file_stem = Path(img_info["file_name"]).stem
        txt_path = os.path.join(labels_dir, f"{file_stem}.txt")

        anns = anns_by_image.get(img_id, [])
        lines = []
        for ann in anns:
            cat_id = ann["category_id"]
            yolo_cls = cat_id_to_idx[cat_id]
            x, y, w, h = ann["bbox"]
            # COCO [x,y,w,h] → YOLO 归一化 [cx,cy,w,h]
            cx = (x + w / 2.0) / img_w
            cy = (y + h / 2.0) / img_h
            nw = w / img_w
            nh = h / img_h
            lines.append(f"{yolo_cls} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        generated += 1

    name_list = [names[i] for i in sorted(names.keys())]
    print(f"[COCO→YOLO] 已生成 {generated} 个标注文件 → {labels_dir}")
    print(f"[COCO→YOLO] 类别: {len(name_list)} → {name_list}")
    return name_list


# ── CLI ──
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="COCO JSON 标注 → YOLO .txt 格式转换",
    )
    parser.add_argument(
        "--coco_json", type=str, required=True,
        help="COCO JSON 标注文件路径（JSON 同级将生成 labels/ 目录）",
    )
    args = parser.parse_args()
    coco2yolo(args.coco_json)
