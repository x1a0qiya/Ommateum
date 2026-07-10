"""
YOLOv11 模型训练脚本 (全量微调 / 冻结部分层)
使用 Ultralytics 库，支持自定义数据集和超参数。

小样本微调最佳实践:
  - 冻结 backbone+neck（freeze=20），仅训练检测头，防止灾难性遗忘
  - 降低学习率（lr0=0.001），避免一步冲垮预训练权重
  - 关闭/减弱数据增强（mosaic/erasing/randaugment），小数据集经不起过强扰动
  - 使用 cosine LR 调度，平滑衰减
"""

import argparse
import os
import shutil
from pathlib import Path
from typing import Union

from ultralytics import YOLO
from ultralytics.engine.results import Results
from ultralytics.utils.downloads import attempt_download_asset


# ── 权重管理路径 ──
WEIGHTS_DIR = Path("weights/yolo")
PRETRAINED_DIR = WEIGHTS_DIR / "pretrained"
TRAINED_DIR = WEIGHTS_DIR / "trained"


def _ensure_pretrained(pretrained: str) -> str:
    """
    确保预训练权重存在于 weights/yolo/pretrained/ 目录下。

    若 pretrained 为纯模型名（如 "yolo11n.pt"），检查本地是否存在，
    不存在则通过 Ultralytics 下载并拷贝到指定目录。
    若 pretrained 已包含路径，则直接返回原路径。

    Args:
        pretrained (str): 预训练权重名称或路径。

    Returns:
        str: 可用的预训练权重本地路径。
    """
    PRETRAINED_DIR.mkdir(parents=True, exist_ok=True)

    # 已经是文件路径，检查是否存在
    if os.path.sep in pretrained or os.path.altsep in pretrained:
        if not os.path.exists(pretrained):
            raise FileNotFoundError(f"预训练权重不存在: {pretrained}")
        return pretrained

    # 纯模型名，检查本地目标路径
    local_path = PRETRAINED_DIR / pretrained
    if local_path.exists():
        return str(local_path)

    # 下载到目标路径
    print(f"[INFO] 预训练权重 {pretrained} 未在本地找到，正在下载到 {PRETRAINED_DIR} ...")
    cached = attempt_download_asset(pretrained)
    shutil.copy2(cached, str(local_path))
    print(f"[INFO] 预训练权重已保存: {local_path}")
    return str(local_path)


def train_yolo_model(
    data_yaml : str = "dataset/data.yaml",
    epochs : int = 50,
    imgsz : int = 640,
    batch : int = 16,
    device : Union[str, int] = "0",
    workers : int = 4,
    project : str = "weights/yolo",
    name : str = "trained",
    patience : int = 10,
    freeze : int = 20,
    pretrained : str = "yolo11n.pt",
    lr0 : float = 0.001,
    lrf : float = 0.1,
    cos_lr : bool = True,
) -> Results:
    """
    训练 YOLOv11n 模型，默认使用小样本微调参数（冻结 backbone+neck + 低学习率）。

    Args:
        data_yaml (str): 数据集配置文件路径（YAML 格式）。
        epochs (int): 训练轮数。
        imgsz (int): 输入图像尺寸（像素）。
        batch (int): 批大小，根据显存调整。
        device (str | int): 训练设备，如 "0" 表示第一块 GPU，"cpu" 表示 CPU。
        workers (int): 数据加载线程数。
        project (str): 训练输出根目录，默认 "weights/yolo"，best.pt 落在 weights/yolo/trained/weights/。
        name (str): 实验子目录名称，默认 "trained"。
        patience (int): 早停耐心值（验证指标不提升时停止训练）。
        freeze (int): 冻结主干网络的前 N 层，默认 20（冻结 backbone+neck，仅训练 head）。
        pretrained (str): 预训练权重名称或路径，纯模型名（如 "yolo11n.pt"）将自动下载到 weights/yolo/pretrained/。
        lr0 (float): 初始学习率，默认 0.001（全量训练用 0.01，微调用 0.001 或更低）。
        lrf (float): 最终学习率因子 (final_lr = lr0 * lrf)，默认 0.1。
        cos_lr (bool): 是否使用 cosine 学习率衰减，默认 True。

    Returns:
        Results: Ultralytics 训练结果对象，包含最佳模型路径等信息。

    Example:
        # 小样本微调（默认）
        >>> train_yolo_model(epochs=30, batch=8)
        # 全量训练 / 大数据集
        >>> train_yolo_model(epochs=100, freeze=0, lr0=0.01, lrf=0.01, cos_lr=False)
    """
    pretrained = _ensure_pretrained(pretrained)
    model = YOLO(pretrained)

    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        workers=workers,
        project=project,
        name=name,
        exist_ok=True,
        val=True,
        patience=patience,
        save=True,
        save_period=1,
        freeze=freeze,
        verbose=True,
        # ── 学习率策略 ──
        lr0=lr0,                # 初始学习率（微调默认 0.001，比默认 0.01 低 10x）
        lrf=lrf,                # 最终 lr 因子（0.1 → final=lr0*0.1，比默认 0.01 温和）
        cos_lr=cos_lr,          # cosine 衰减（比线性衰减更平滑）
        # ── 数据增强（小数据集降低强度） ──
        mosaic=0.0,             # 关闭 mosaic，20~100 张图经不起 4 图拼接
        mixup=0.0,              # 关闭 mixup
        erasing=0.0,            # 关闭随机擦除
        auto_augment=None,      # 关闭 auto_augment（默认 randaugment 对小数据太激进）
        hsv_h=0.01,             # 色调增强减弱 (默认 0.015)
        hsv_s=0.3,              # 饱和度增强减弱 (默认 0.7)
        hsv_v=0.2,              # 明度增强减弱 (默认 0.4)
        scale=0.3,              # 缩放增强减弱 (默认 0.5)
        fliplr=0.5,             # 保留水平翻转
        # ── 优化器 ──
        warmup_epochs=5,        # 延长 warmup，让 head 软着陆，避免 epoch 1 暴跌
        warmup_bias_lr=0.05,    # warmup 起始 lr = lr0 * 0.05（更保守的起点）
        weight_decay=0.0005,
    )

    if hasattr(model, 'trainer') and hasattr(model.trainer, 'best'):
        best_path = model.trainer.best
        print(f"训练完成！最佳模型保存在：{best_path}")
    else:
        print("训练完成！请检查 runs 目录下的权重文件。")
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="训练 YOLOv11 图像分割/检测模型")
    parser.add_argument("--data", default="dataset/data.yaml", help="数据集配置 YAML")
    parser.add_argument("--epochs", type=int, default=50, help="训练轮数")
    parser.add_argument("--imgsz", type=int, default=640, help="输入图像尺寸")
    parser.add_argument("--batch", type=int, default=16, help="批大小")
    parser.add_argument("--device", default="0", help="设备，如 '0' 或 'cpu'")
    parser.add_argument("--workers", type=int, default=4, help="数据加载线程数")
    parser.add_argument("--project", default="weights/yolo", help="输出根目录")
    parser.add_argument("--name", default="trained", help="实验子目录名")
    parser.add_argument("--patience", type=int, default=10, help="早停耐心值")
    parser.add_argument("--freeze", type=int, default=20,
                        help="冻结主干前 N 层，小样本推荐 20 (0=全量微调)")
    parser.add_argument("--pretrained", default="yolo11n.pt", help="预训练权重路径")
    parser.add_argument("--lr0", type=float, default=0.001,
                        help="初始学习率（全量训练 0.01，微调 0.001 或更低）")
    parser.add_argument("--lrf", type=float, default=0.1,
                        help="最终学习率因子 (final_lr = lr0 * lrf)")
    parser.add_argument("--cos_lr", type=bool, default=True,
                        help="使用 cosine 学习率衰减")
    parser.add_argument("--full_train", action="store_true",
                        help="全量训练模式：不冻结 backbone，使用默认学习率")
    args = parser.parse_args()

    # 当指定 --full_train 时，恢复为大数据集训练的默认参数
    if args.full_train:
        train_yolo_model(
            data_yaml=args.data,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
            workers=args.workers,
            project=args.project,
            name=args.name,
            patience=args.patience,
            freeze=0,
            pretrained=args.pretrained,
            lr0=0.01,
            lrf=0.01,
            cos_lr=False,
        )
    else:
        train_yolo_model(
            data_yaml=args.data,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
            workers=args.workers,
            project=args.project,
            name=args.name,
            patience=args.patience,
            freeze=args.freeze,
            pretrained=args.pretrained,
            lr0=args.lr0,
            lrf=args.lrf,
            cos_lr=args.cos_lr,
        )
