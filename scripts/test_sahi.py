"""
使用 SAHI 对 val 图片进行切片推理，结果输出到 result 目录。

用法:
    python scripts/test_sahi.py                              # 使用默认参数
    python scripts/test_sahi.py --model_type yolov8         # 指定模型类型
    python scripts/test_sahi.py --model_path best.pt        # 指定权重
    python scripts/test_sahi.py --conf 0.3                  # 指定置信度阈值
    python scripts/test_sahi.py --no_coco                   # 不导出 COCO JSON
"""

import argparse
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保可导入 ommateum
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ommateum.utils.sahi import predict

def main():
    parser = argparse.ArgumentParser(description="SAHI 切片推理测试")
    parser.add_argument("--model_type",  type=str, default="yolov8",
                        help="模型类型（yolov8 / mmdet 等）")
    parser.add_argument("--model_path",  type=str, default="yolo11n.pt",
                        help="模型权重文件路径")
    parser.add_argument("--conf",        type=float, default=0.3,
                        help="置信度阈值 (default: 0.3)")
    parser.add_argument("--device",      type=str, default="cpu",
                        help="推理设备 (cpu / cuda:0)")
    parser.add_argument("--val_dir",     type=str, default="train",
                        help="val 图片目录路径 (default:train/ )")            #这里应该是实际的路径
    parser.add_argument("--out_dir",     type=str, default="result",
                        help="结果输出目录 (default: result/)")
    parser.add_argument("--slice_h",     type=int, default=256,
                        help="切片高度 (default: 256)")
    parser.add_argument("--slice_w",     type=int, default=640,
                        help="切片宽度 (default: 640)")
    parser.add_argument("--overlap_h",   type=float, default=0.2,
                        help="高度方向重叠比例 (default: 0.2)")
    parser.add_argument("--overlap_w",   type=float, default=0.2,
                        help="宽度方向重叠比例 (default: 0.2)")
    parser.add_argument("--no_coco",     action="store_true",
                        help="不导出 COCO JSON")
    parser.add_argument("--name",        type=str, default="exp",
                        help="实验名称 (default: exp)")

    args = parser.parse_args()

    val_path = Path(args.val_dir)
    if not val_path.exists():
        print(f"[错误] val 目录不存在: {val_path.resolve()}")
        sys.exit(1)

    img_count = len(list(val_path.glob("*")))
    print(f"  val 目录: {val_path.resolve()}")
    print(f"  图片数量: {img_count}")
    print(f"  模型: {args.model_type} / {args.model_path}")
    print(f"  设备: {args.device}")
    print(f"  切片: {args.slice_h}×{args.slice_w}, 重叠 {args.overlap_h}/{args.overlap_w}")
    print(f"  输出: {args.out_dir}/{args.name}")
    print(f"  COCO: {'是' if not args.no_coco else '否'}")
    print()

    # 执行推理
    try:
        results = predict(
            model_type=args.model_type,
            model_path=args.model_path,
            model_confidence_threshold=args.conf,
            model_device=args.device,
            source=str(val_path),
            slice_height=args.slice_h,
            slice_width=args.slice_w,
            overlap_height_ratio=args.overlap_h,
            overlap_width_ratio=args.overlap_w,
            project=args.out_dir,
            name=args.name,
            export_coco=not args.no_coco,
        )

        print(f"\n  ✓ 推理完成！")
        print(f"  总检测框数: {len(results)}")
        result_path = Path(args.out_dir) / args.name
        print(f"  结果路径: {result_path}")
        coco_path = result_path / "annotations.json"
        print(f"  COCO JSON: {coco_path}  ({'存在' if coco_path.exists() else '不存在'})")
        print()

        # 按类别统计
        from collections import Counter
        cat_counts = Counter(r["category"] for r in results)
        print(f"  类别统计:")
        for cat, cnt in cat_counts.most_common():
            print(f"    {cat}: {cnt}")

    except Exception as e:
        print(f"\n  [错误] 推理失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
