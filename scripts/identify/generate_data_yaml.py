#!/usr/bin/env python3
"""
生成 YOLO 格式的 data.yaml 配置文件。

供前端 / 外部服务调用，接收 images & labels 目录路径，
自动生成可用于训练和评估的 data.yaml。

支持三种模式:

  模式 A - COCO JSON 输入（自动转换标注 + 生成 data.yaml）:
    python scripts/identify/generate_data_yaml.py \
        --coco_json /Ommateum/cache/task_001/annotations.json

    JSON 所在目录需包含 images/ 子目录，脚本自动:
      1. 在 labels/ 下生成 YOLO .txt 标注
      2. 在 JSON 同级输出 data.yaml

  模式 B - 手动指定 train/val 目录:
    python scripts/identify/generate_data_yaml.py \
        --train_images /data/train/images \
        --train_labels /data/train/labels \
        --val_images /data/val/images \
        --val_labels /data/val/labels \
        --names "scratch,crack" \
        --output /data/data.yaml

  模式 C - 统一目录（已有 YOLO .txt 标注）:
    python scripts/identify/generate_data_yaml.py \
        --images /Ommateum/cache/task_001/images \
        --labels /Ommateum/cache/task_001/labels \
        --names "scratch,crack,dent" \
        --output /Ommateum/cache/task_001/data.yaml

    # 带自动 train/val 划分
    python scripts/identify/generate_data_yaml.py \
        --images /Ommateum/cache/task_001/images \
        --labels /Ommateum/cache/task_001/labels \
        --names "scratch,crack" \
        --output /Ommateum/cache/task_001/data.yaml \
        --val_split 0.1
"""

import argparse
import json
import os
import random
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _coco_to_yolo_labels(coco_json_path: str, labels_dir: str) -> List[str]:
    """
    将 COCO JSON 标注转为 YOLO .txt 格式，写入 labels_dir。

    Args:
        coco_json_path (str): COCO 格式 JSON 文件路径。
        labels_dir (str): 输出 YOLO .txt 的目标目录。

    Returns:
        List[str]: 类别名称列表（按 YOLO 0-based 索引顺序）。

    Raises:
        ValueError: JSON 格式不正确或缺少必要字段时抛出。
    """
    with open(coco_json_path, "r", encoding="utf-8") as f:
        coco = json.load(f)

    images_info: Dict[int, Dict[str, Any]] = {}
    for img in coco.get("images", []):
        images_info[img["id"]] = img

    categories = coco.get("categories", [])
    if not categories:
        raise ValueError("COCO JSON 中缺少 categories 字段")

    # COCO category.id → YOLO 0-based index 映射
    cat_id_to_idx: Dict[int, int] = {}
    names: Dict[int, str] = {}
    for idx, cat in enumerate(sorted(categories, key=lambda c: c["id"])):
        cat_id_to_idx[cat["id"]] = idx
        names[idx] = cat["name"]

    os.makedirs(labels_dir, exist_ok=True)

    # image_id → annotations 分组
    anns_by_image: Dict[int, List[Dict[str, Any]]] = {}
    for ann in coco.get("annotations", []):
        img_id = ann["image_id"]
        anns_by_image.setdefault(img_id, []).append(ann)

    generated = 0
    for img_id, img_info in images_info.items():
        img_w = img_info["width"]
        img_h = img_info["height"]
        file_stem = Path(img_info["file_name"]).stem
        txt_path = os.path.join(labels_dir, file_stem + ".txt")

        anns = anns_by_image.get(img_id, [])
        lines = []
        for ann in anns:
            cat_id = ann["category_id"]
            yolo_cls = cat_id_to_idx[cat_id]
            x, y, w, h = ann["bbox"]
            # COCO [x,y,w,h] → YOLO [cx,cy,w,h] 归一化
            cx = (x + w / 2) / img_w
            cy = (y + h / 2) / img_h
            nw = w / img_w
            nh = h / img_h
            lines.append(f"{yolo_cls} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        generated += 1

    # 恢复 categories 原始顺序（按 COCO category.id 排序后的 name 列表）
    name_list = [names[i] for i in sorted(names.keys())]
    print(f"[COCO→YOLO] 已生成 {generated} 个标注文件 → {labels_dir}")
    print(f"[COCO→YOLO] 类别: {len(name_list)} → {name_list}")
    return name_list


def generate_data_yaml(
    output : str,
    names : List[str],
    train_images : Optional[str] = None,
    train_labels : Optional[str] = None,
    val_images : Optional[str] = None,
    val_labels : Optional[str] = None,
    images : Optional[str] = None,
    labels : Optional[str] = None,
    val_split : float = 0.0,
    seed : int = 42,
    coco_json : Optional[str] = None,
) -> str:
    """
    根据图片和标注目录生成 YOLO data.yaml。

    支持三种输入模式:
      A. 传入 coco_json → 自动转 COCO→YOLO .txt + 生成 data.yaml
      B. 直接指定 train/val 各自的 images & labels 目录
      C. 指定统一的 images & labels 目录，通过 val_split 自动划分

    Args:
        output (str): 输出的 data.yaml 文件路径。模式 A 下可留空，自动生成为
                      JSON 同级目录下的 data.yaml。
        names (List[str]): 类别名称列表。模式 A 下可留空，自动从 COCO categories 读取。
        train_images (str | None): 训练集图片目录，模式 B 必填。
        train_labels (str | None): 训练集标注目录，模式 B 必填。
        val_images (str | None): 验证集图片目录，未提供则复用 train_images。
        val_labels (str | None): 验证集标注目录，未提供则复用 train_labels。
        images (str | None): 统一图片目录，模式 C 必填。
        labels (str | None): 统一标注目录，模式 C 必填。
        val_split (float): 验证集划分比例 (0.0~1.0)，模式 A/C 下生效。
        seed (int): 随机种子，用于 train/val 划分。
        coco_json (str | None): COCO JSON 路径，模式 A 必填。
                                JSON 所在目录需包含 images/ 子目录，
                                脚本自动在 labels/ 下生成 YOLO .txt 标注，
                                并在 JSON 同级生成 data.yaml。

    Returns:
        str: 生成的 data.yaml 的绝对路径。

    Raises:
        ValueError: 参数不足时抛出。
        RuntimeError: 当 images 目录中没有图片文件时抛出。
    """
    # ── 模式 A: COCO JSON 输入，自动转换标注 ──
    if coco_json:
        coco_json = os.path.abspath(coco_json)
        if not os.path.isfile(coco_json):
            raise FileNotFoundError(f"COCO JSON 不存在: {coco_json}")
        base_dir = os.path.dirname(coco_json)

        images_dir = os.path.join(base_dir, "images")
        labels_dir = os.path.join(base_dir, "labels")

        if not os.path.isdir(images_dir):
            raise FileNotFoundError(f"JSON 同级缺少 images/ 目录: {images_dir}")

        # 从 COCO JSON 生成 YOLO .txt 标注
        names = _coco_to_yolo_labels(coco_json, labels_dir)

        # 自动设置 output 路径
        if not output or output == "dataset/data.yaml":
            output = os.path.join(base_dir, "data.yaml")

        return generate_data_yaml(
            output=output,
            names=names,
            images=images_dir,
            labels=labels_dir,
            val_split=val_split,
            seed=seed,
        )

    # ── 模式 B / C ──
    output = os.path.abspath(output)
    output_dir = os.path.dirname(output)
    os.makedirs(output_dir, exist_ok=True)

    # ── 模式 B: 手动指定 train/val ──
    if train_images and train_labels:
        train_img_abspath = os.path.abspath(train_images)
        train_lbl_abspath = os.path.abspath(train_labels)
        val_img_abspath = os.path.abspath(val_images) if val_images else train_img_abspath
        val_lbl_abspath = os.path.abspath(val_labels) if val_labels else train_lbl_abspath
    else:
        # ── 模式 C: 统一目录 + 可选自动划分 ──
        if not images or not labels:
            raise ValueError("必须提供 --images/--labels 或 --train_images/--train_labels")
        images = os.path.abspath(images)
        labels = os.path.abspath(labels)

        if val_split > 0:
            train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir = _split_train_val(
                images, labels, output_dir, val_split, seed
            )
            train_img_abspath = train_img_dir
            train_lbl_abspath = train_lbl_dir
            val_img_abspath = val_img_dir
            val_lbl_abspath = val_lbl_dir
        else:
            train_img_abspath = images
            train_lbl_abspath = labels
            val_img_abspath = images
            val_lbl_abspath = labels

    # ── 生成 YAML ──
    yaml_content = f"""# Auto-generated data.yaml for YOLO training
# Generated by scripts/identify/generate_data_yaml.py

path: {output_dir}
train: {train_img_abspath}
val: {val_img_abspath}

nc: {len(names)}
names: {names}
"""
    with open(output, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print(f"[OK] data.yaml 已生成: {output}")
    print(f"     类别数: {len(names)} → {names}")
    print(f"     train images: {train_img_abspath}")
    print(f"     train labels: {train_lbl_abspath}")
    print(f"     val   images: {val_img_abspath}")
    print(f"     val   labels: {val_lbl_abspath}")
    return output


def _split_train_val(
    images_dir : str,
    labels_dir : str,
    output_dir : str,
    val_split : float,
    seed : int,
) -> Tuple[str, str, str, str]:
    """
    将 images / labels 目录按比例随机拆分为 train / val。

    Args:
        images_dir (str): 原始图片目录。
        labels_dir (str): 原始标注目录。
        output_dir (str): train/val 子目录的输出根路径。
        val_split (float): 验证集比例 (0.0~1.0)。
        seed (int): 随机种子。

    Returns:
        Tuple[str, str, str, str]: (train_images_dir, val_images_dir,
                                     train_labels_dir, val_labels_dir)

    Raises:
        RuntimeError: 当 images_dir 中无图片文件时抛出。
    """
    random.seed(seed)

    img_files = sorted(
        f for f in os.listdir(images_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"))
    )
    if not img_files:
        raise RuntimeError(f"images 目录中没有图片文件: {images_dir}")

    random.shuffle(img_files)
    split_idx = max(1, int(len(img_files) * (1 - val_split)))
    train_files = img_files[:split_idx]
    val_files = img_files[split_idx:]

    train_img_dir = os.path.join(output_dir, "train", "images")
    train_lbl_dir = os.path.join(output_dir, "train", "labels")
    val_img_dir = os.path.join(output_dir, "val", "images")
    val_lbl_dir = os.path.join(output_dir, "val", "labels")

    for d in [train_img_dir, train_lbl_dir, val_img_dir, val_lbl_dir]:
        os.makedirs(d, exist_ok=True)

    _copy_files(images_dir, labels_dir, train_files, train_img_dir, train_lbl_dir)
    _copy_files(images_dir, labels_dir, val_files, val_img_dir, val_lbl_dir)

    print(f"[自动划分] train={len(train_files)} 张, val={len(val_files)} 张 (split={val_split})")
    return train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir


def _copy_files(
    src_img : str,
    src_lbl : str,
    files : List[str],
    dst_img : str,
    dst_lbl : str,
) -> None:
    """
    将图片及其对应的 YOLO label 文件复制到目标目录。

    Args:
        src_img (str): 源图片目录。
        src_lbl (str): 源标注目录。
        files (List[str]): 要复制的图片文件名列表。
        dst_img (str): 目标图片目录。
        dst_lbl (str): 目标标注目录。
    """
    for fname in files:
        shutil.copy2(os.path.join(src_img, fname), os.path.join(dst_img, fname))
        stem = Path(fname).stem
        lbl_file = stem + ".txt"
        src_lbl_path = os.path.join(src_lbl, lbl_file)
        if os.path.exists(src_lbl_path):
            shutil.copy2(src_lbl_path, os.path.join(dst_lbl, lbl_file))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成 YOLO data.yaml 配置文件")
    # ── 模式 A: COCO JSON ──
    parser.add_argument("--coco_json", default=None,
                        help="COCO JSON 标注文件路径（JSON 同级需有 images/ 目录）")
    # ── 模式 B: 手动指定 train/val ──
    parser.add_argument("--train_images", default=None, help="训练集图片目录")
    parser.add_argument("--train_labels", default=None, help="训练集标注目录（YOLO 格式 .txt）")
    parser.add_argument("--val_images", default=None, help="验证集图片目录")
    parser.add_argument("--val_labels", default=None, help="验证集标注目录")
    # ── 模式 C: 统一目录 ──
    parser.add_argument("--images", default=None, help="图片目录（train/val 共用）")
    parser.add_argument("--labels", default=None, help="标注目录（train/val 共用）")
    parser.add_argument("--val_split", type=float, default=0.0,
                        help="验证集比例 (0.0~1.0)，设置后自动从 images/labels 划分 train/val")
    # ── 通用参数 ──
    parser.add_argument("--names", default=None,
                        help="类别名称，逗号分隔（模式 A 下可省略，自动从 COCO 读取）")
    parser.add_argument("--output", default="dataset/data.yaml",
                        help="输出 data.yaml 的路径（模式 A 下可省略，自动生成到 JSON 同级）")
    parser.add_argument("--seed", type=int, default=42, help="随机种子（用于 train/val 划分）")
    args = parser.parse_args()

    # ── 模式 A: COCO JSON ──
    if args.coco_json:
        generate_data_yaml(
            output=args.output,
            names=[],  # 由 coco_json 模式自动读取
            coco_json=args.coco_json,
            val_split=args.val_split,
            seed=args.seed,
        )
    else:
        # ── 模式 B / C ──
        if not args.names:
            raise ValueError("非 COCO 模式下 --names 不能为空")
        names_list = [n.strip() for n in args.names.split(",") if n.strip()]
        if not names_list:
            raise ValueError("--names 不能为空")

        generate_data_yaml(
            output=args.output,
            names=names_list,
            train_images=args.train_images,
            train_labels=args.train_labels,
            val_images=args.val_images,
            val_labels=args.val_labels,
            images=args.images,
            labels=args.labels,
            val_split=args.val_split,
            seed=args.seed,
        )
