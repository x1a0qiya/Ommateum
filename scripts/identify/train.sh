#!/bin/bash
# ============================================================
# YOLO 小样本微调训练脚本
# 供外部服务 / 前端调用。
#
# 用法:
#   bash scripts/identify/train.sh \
#       --data     /path/to/data.yaml \
#       --name     my_experiment \
#       --epochs   30
#
# 环境变量覆盖（优先级低于命令行参数）:
#   DATA_YAML, EPOCHS, BATCH, IMGSZ, DEVICE, FREEZE,
#   LR0, LRF, PROJECT, NAME, PATIENCE, PRETRAINED
# ============================================================

set -euo pipefail

cd "$(dirname "$0")/../.."   # 回到项目根目录 /Ommateum

# ── 默认参数（小样本微调最佳参数） ──
DATA="${DATA_YAML:-dataset/data.yaml}"
EPOCHS="${EPOCHS:-30}"
BATCH="${BATCH:-4}"
IMGSZ="${IMGSZ:-640}"
DEVICE="${DEVICE:-0}"
WORKERS="${WORKERS:-4}"
PROJECT="${PROJECT:-runs/train}"
NAME="${NAME:-exp}"
PATIENCE="${PATIENCE:-10}"
FREEZE="${FREEZE:-20}"
PRETRAINED="${PRETRAINED:-yolo11n.pt}"
LR0="${LR0:-0.001}"
LRF="${LRF:-0.1}"
COS_LR="${COS_LR:-True}"

# ── 解析命令行参数 ──
while [[ $# -gt 0 ]]; do
    case $1 in
        --data)       DATA="$2";       shift 2 ;;
        --epochs)     EPOCHS="$2";     shift 2 ;;
        --batch)      BATCH="$2";      shift 2 ;;
        --imgsz)      IMGSZ="$2";      shift 2 ;;
        --device)     DEVICE="$2";     shift 2 ;;
        --workers)    WORKERS="$2";    shift 2 ;;
        --project)    PROJECT="$2";    shift 2 ;;
        --name)       NAME="$2";       shift 2 ;;
        --patience)   PATIENCE="$2";   shift 2 ;;
        --freeze)     FREEZE="$2";     shift 2 ;;
        --pretrained) PRETRAINED="$2"; shift 2 ;;
        --lr0)        LR0="$2";        shift 2 ;;
        --lrf)        LRF="$2";        shift 2 ;;
        --cos_lr)     COS_LR="$2";     shift 2 ;;
        *)
            echo "未知参数: $1"
            echo "用法: bash scripts/identify/train.sh --data <data.yaml> --name <exp_name> [可选参数...]"
            exit 1
            ;;
    esac
done

# ── 打印配置 ──
echo "====================================================="
echo " YOLO 小样本微调训练"
echo "====================================================="
echo " 数据配置:      $DATA"
echo " 预训练权重:    $PRETRAINED"
echo " 训练轮数:      $EPOCHS"
echo " 批大小:        $BATCH"
echo " 图像尺寸:      $IMGSZ"
echo " 设备:          $DEVICE"
echo " 冻结层数:      $FREEZE"
echo " 学习率:        $LR0 (final factor=$LRF)"
echo " Cosine LR:    $COS_LR"
echo " 实验名称:      $NAME"
echo " 输出目录:      $PROJECT/$NAME"
echo " 早停耐心:      $PATIENCE"
echo "====================================================="

# ── 执行训练 ──
python src/ommateum/models/identify/train.py \
    --data "$DATA" \
    --epochs "$EPOCHS" \
    --batch "$BATCH" \
    --imgsz "$IMGSZ" \
    --device "$DEVICE" \
    --workers "$WORKERS" \
    --project "$PROJECT" \
    --name "$NAME" \
    --patience "$PATIENCE" \
    --freeze "$FREEZE" \
    --pretrained "$PRETRAINED" \
    --lr0 "$LR0" \
    --lrf "$LRF" \
    --cos_lr "$COS_LR"

# ── 输出最佳模型路径 ──
BEST_PT="$PROJECT/$NAME/weights/best.pt"
if [ -f "$BEST_PT" ]; then
    echo ""
    echo "====================================================="
    echo " 训练完成！"
    echo " 最佳模型: $BEST_PT"
    echo " 结果目录: $PROJECT/$NAME"
    echo "====================================================="
else
    echo ""
    echo "警告: 未找到 best.pt，训练可能未正常完成"
    exit 1
fi
