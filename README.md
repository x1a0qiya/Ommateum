# Ommateum — 工业质检极少样本快速缺陷分割系统

面向工业质检场景的**极少样本快速缺陷分割系统**，解决新类型缺陷样本稀缺、人工标注成本高以及模型上线周期长等实际问题。

## 核心特性

- **极简标注** — 用户只需对极少量样本进行简易的交互式标注即可启动训练
- **数据合成** — 基于标注结果自动扩充样本规模，缓解缺陷数据不足问题
- **快速训练** — 快速产出像素级的缺陷检测与分割模型，缩短上线周期
- **动态加载** — 支持根据质检任务动态切换模型权重，灵活适配不同产线
- **显存优化** — 针对高分辨率工业图像进行显存控制优化，降低部署成本

## 系统架构

```
用户交互层      →  极少样本标注  →  数据合成
               ↘  模型训练      →  模型评估
模型部署层      →  动态加载      →  像素级分割
```

## 快速开始

### 使用 Docker（推荐）

```bash
# 构建并运行 Docker
docker compose up -d
```

### 本地安装

**Important:我们在依赖文件中去掉了 Docker 自带的库, 详情请看 requirements.txt/requirements-dev.txt 中的注释部分**
```bash
# 安装生产依赖
pip install -U -r requirements.txt

# 安装开发依赖
pip install -U -r requirements-dev.txt
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
├── Dockerfile              # 多阶段构建镜像
├── docker-compose.yml      # 多容器启动工具
├── .dockerignore           # Docker 忽略规则
├── .gitignore              # Git 忽略规则
├── .gitlab-ci.yml          # GitLab CI/CD 流水线
├── .github/workflows/      # GitHub Actions 流水线
├── requirements.txt        # 生产依赖
├── requirements-dev.txt    # 开发依赖
├── pyproject.toml          # 项目元数据与工具配置
├── LICENSE                 # 许可证
├── README.md               # 项目说明
├── src/ommateum/           # 主代码
│   ├── models/             # 模型定义
│   ├── services/           # 业务逻辑
│   └── utils/              # 工具函数
├── tests/                  # 测试
├── docs/                   # 文档
└── scripts/                # 工具脚本
```

## CI/CD

项目同时支持两个 CI 平台：

| 平台 | 配置文件 | 触发条件 |
|------|----------|----------|
| GitLab CI | `.gitlab-ci.yml` | 推送到 default / develop 分支或创建 MR |
| GitHub Actions | `.github/workflows/ci.yml` | 推送到 main / master / develop 分支或创建 PR |

流水线包含三个阶段：**代码检查 → 测试 → 构建**，统一使用 Python 3.14.6。

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
