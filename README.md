# Ommateum — 工业质检极少样本快速缺陷检测系统

面向工业质检场景的**极少样本快速缺陷检测系统**，基于 YOLOv11，解决新类型缺陷样本稀缺、人工标注成本高以及模型上线周期长等实际问题。

## 核心特性

- **极简标注** — 用户只需对极少量样本进行简易的标注即可启动训练
- **数据合成** — 基于标注结果自动扩充样本规模，缓解缺陷数据不足问题
- **快速训练** — 冻结 backbone 小样本微调，快速产出缺陷检测模型
- **动态加载** — 支持根据质检任务动态切换模型权重，灵活适配不同产线
- **对外接口** — 提供 Shell 脚本 + Python API，方便前端 / CI 系统集成调用

## 系统架构

```
用户交互层      →  少量样本标注  →  generate_data_yaml.py
               ↘  模型训练      →  train.sh / train_yolo_model()
模型评估层      →  模型验证      →  test.sh / evaluate_yolo_model()
```

## 快速开始

### 使用 Docker（推荐）

```bash
# 构建并运行 Docker
docker compose up -d

# 进入容器
docker exec -it dd bash
```

### 本地安装

**Important: 我们在依赖文件中去掉了 Docker 自带的库, 详情请看 requirements.txt/requirements-dev.txt 中的注释部分**

```bash
# 安装生产依赖
pip install -U -r requirements.txt

# 安装开发依赖
pip install -U -r requirements-dev.txt
```

## 检测模型（identify）

基于 YOLOv11n 的小样本微调方案，经过多轮实验验证的最优参数：

| 参数 | 值 | 说明 |
|------|-----|------|
| freeze | 20 | 冻结 backbone+neck，仅训练 detection head |
| lr0 | 0.001 | 降低 10x 防止灾难性遗忘 |
| lrf | 0.1 | 最终 lr = lr0 × 0.1，温和衰减 |
| cos_lr | True | Cosine 学习率调度 |
| warmup_epochs | 5 | 延长 warmup 让 head 软着陆 |
| mosaic / erasing | 关闭 | 小数据集经不起过强增强 |

### 外部调用流程

```
┌─────────────────────────────────────────────────────────┐
│ 1. 前端提交 images + labels → 缓存在本地                  │
│                                                         │
│ 2. 调用 generate_data_yaml.py 生成 data.yaml             │
│    python scripts/identify/generate_data_yaml.py \      │
│        --images /cache/xxx/images \                     │
│        --labels /cache/xxx/labels \                     │
│        --names "scratch,crack,dent" \                   │
│        --output /cache/xxx/data.yaml \                  │
│        --val_split 0.1                                  │
│                                                         │
│ 3. 调用 train.sh 启动训练                                │
│    bash scripts/identify/train.sh \                     │
│        --data /cache/xxx/data.yaml \                    │
│        --name task_001 \                                │
│        --epochs 30                                      │
│    → 输出: runs/train/task_001/weights/best.pt          │
│                                                         │
│ 4. 调用 test.sh 评估模型                                 │
│    bash scripts/identify/test.sh \                      │
│        --weights runs/train/task_001/weights/best.pt \  │
│        --data /cache/xxx/data.yaml \                    │
│        --name task_001_eval                             │
│    → 输出: runs/eval/task_001_eval/metrics.json         │
└─────────────────────────────────────────────────────────┘
```

### Shell 脚本参数

**train.sh**（也支持环境变量 `DATA_YAML` `EPOCHS` `BATCH` `FREEZE` 等覆盖默认值）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--data` | `dataset/data.yaml` | data.yaml 路径 |
| `--name` | `exp` | 实验名称 |
| `--epochs` | `30` | 训练轮数 |
| `--batch` | `4` | 批大小 |
| `--freeze` | `20` | 冻结层数 |
| `--lr0` | `0.001` | 初始学习率 |

**test.sh**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--weights` | `runs/train/exp/weights/best.pt` | 模型权重 |
| `--data` | `dataset/data.yaml` | data.yaml 路径 |
| `--name` | `eval` | 输出名称 |

### Python API

```python
from src.ommateum.models.identify.train import train_yolo_model
from src.ommateum.models.identify.evaluate import evaluate_yolo_model

# 训练
model = train_yolo_model(
    data_yaml="dataset/data.yaml",
    epochs=30,
    batch=4,
    freeze=20,
)

# 评估
metrics = evaluate_yolo_model(
    weights="runs/train/exp/weights/best.pt",
    data_yaml="dataset/data.yaml",
)
# → {"mAP50": 0.457, "mAP50_95": 0.301, "precision": ..., "recall": ...}
```

## 开发

```bash
# 运行测试
pytest

# 代码检查
ruff check .
ruff format --check .

# 类型检查
mypy . --ignore-missing-imports
```

## 目录结构

```
├── Dockerfile                    # 多阶段构建镜像
├── docker-compose.yml            # Docker 编排
├── .dockerignore                 # Docker 忽略规则
├── .gitignore                    # Git 忽略规则
├── .gitlab-ci.yml                # GitLab CI/CD 流水线
├── .github/workflows/            # GitHub Actions 流水线
├── requirements.txt              # 生产依赖
├── requirements-dev.txt          # 开发依赖
├── pyproject.toml                # 项目元数据与工具配置
├── LICENSE                       # 许可证
├── README.md                     # 项目说明
│
├── src/ommateum/                 # 主代码
│   ├── models/
│   │   └── identify/
│   │       ├── train.py          # YOLOv11 小样本微调训练
│   │       └── evaluate.py       # 模型评估
│   ├── services/                 # 业务逻辑
│   └── utils/                    # 工具函数
│
├── scripts/
│   ├── identify/
│   │   ├── train.sh              # 训练 Shell 入口
│   │   ├── test.sh               # 评估 Shell 入口
│   │   └── generate_data_yaml.py # 根据 images/labels 生成 data.yaml
│   └── generate/
│       ├── export_safetensor.py  # .pt → .safetensors 导出
│       └── plot_metrics.py       # 训练指标可视化
│
├── dataset/                      # 数据集
│   ├── data.yaml                 # 数据集配置示例
│   └── scripts/
│       └── extract_subset.py     # COCO 子集提取工具
│
├── tests/                        # 测试
├── docs/                         # 文档
└── runs/                         # 训练/评估输出 (gitignored)
```

## CI/CD

项目同时支持两个 CI 平台：

| 平台 | 配置文件 | 触发条件 |
|------|----------|----------|
| GitLab CI | `.gitlab-ci.yml` | 推送到 default / develop 分支或创建 MR |
| GitHub Actions | `.github/workflows/ci.yml` | 推送到 main / master / develop 分支或创建 PR |

流水线包含三个阶段：**代码检查 → 测试 → 构建**，统一使用 Python 3.10+。

## Git 提交规范

采用 Angular 提交规范，格式：`<type>(<scope>): <subject>`

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 问题修复 |
| `docs` | 文档更新 |
| `refactor` | 代码重构 |
| `style` | 代码格式调整 |
| `chore` | 日常维护 |

> 每次提交只解决一个问题，保持提交历史整洁。

## 许可证

详见 [LICENSE](LICENSE)。
