#!/bin/bash
# ============================================================
# YOLO 模型评估 / 测试脚本
# 供外部服务 / 前端调用，评估训练好的模型在数据集上的表现。
#
# 用法:
#   bash scripts/identify/test.sh \
#       --weights  /path/to/best.pt \
#       --data     /path/to/data.yaml \
#       --name     eval_result
#
# 环境变量覆盖（优先级低于命令行参数）:
#   WEIGHTS, DATA_YAML, BATCH, IMGSZ, DEVICE, PROJECT, NAME
# ============================================================

set -euo pipefail

cd "$(dirname "$0")/../.."   # 回到项目根目录 /Ommateum

# ── 默认参数 ──
WEIGHTS="${WEIGHTS:-weights/yolo/trained/weights/best.pt}"
DATA="${DATA_YAML:-dataset/data.yaml}"
BATCH="${BATCH:-4}"
IMGSZ="${IMGSZ:-640}"
DEVICE="${DEVICE:-0}"
WORKERS="${WORKERS:-4}"
PROJECT="${PROJECT:-runs/eval}"
NAME="${NAME:-eval}"
CONF="${CONF:-}"
IOU="${IOU:-0.7}"

# ── 解析命令行参数 ──
while [[ $# -gt 0 ]]; do
    case $1 in
        --weights)  WEIGHTS="$2";  shift 2 ;;
        --data)     DATA="$2";     shift 2 ;;
        --batch)    BATCH="$2";    shift 2 ;;
        --imgsz)    IMGSZ="$2";    shift 2 ;;
        --device)   DEVICE="$2";   shift 2 ;;
        --workers)  WORKERS="$2";  shift 2 ;;
        --project)  PROJECT="$2";  shift 2 ;;
        --name)     NAME="$2";     shift 2 ;;
        --conf)     CONF="$2";     shift 2 ;;
        --iou)      IOU="$2";      shift 2 ;;
        *)
            echo "未知参数: $1"
            echo "用法: bash scripts/identify/test.sh --weights <best.pt> --data <data.yaml> [可选参数...]"
            exit 1
            ;;
    esac
done

# ── 检查文件是否存在 ──
if [ ! -f "$WEIGHTS" ]; then
    echo "错误: 模型权重文件不存在: $WEIGHTS"
    exit 1
fi
if [ ! -f "$DATA" ]; then
    echo "错误: data.yaml 文件不存在: $DATA"
    exit 1
fi

# ── 打印配置 ──
echo "====================================================="
echo " YOLO 模型评估"
echo "====================================================="
echo " 模型权重:      $WEIGHTS"
echo " 数据配置:      $DATA"
echo " 批大小:        $BATCH"
echo " 图像尺寸:      $IMGSZ"
echo " 设备:          $DEVICE"
echo " 输出名称:      $NAME"
echo "====================================================="

# ── 构建 Python 命令 ──
CMD="python src/ommateum/models/identify/evaluate.py \
    --weights \"$WEIGHTS\" \
    --data \"$DATA\" \
    --batch \"$BATCH\" \
    --imgsz \"$IMGSZ\" \
    --device \"$DEVICE\" \
    --workers \"$WORKERS\" \
    --project \"$PROJECT\" \
    --name \"$NAME\" \
    --iou \"$IOU\""

if [ -n "$CONF" ]; then
    CMD="$CMD --conf \"$CONF\""
fi

eval "$CMD"

# ── 输出结果路径 ──
METRICS_JSON="$PROJECT/$NAME/metrics.json"
if [ -f "$METRICS_JSON" ]; then
    echo ""
    echo "====================================================="
    echo " 评估完成！"
    echo " 指标 JSON: $METRICS_JSON"
    echo "====================================================="
else
    echo ""
    echo "警告: 未找到 metrics.json，评估可能未正常完成"
    exit 1
fi
