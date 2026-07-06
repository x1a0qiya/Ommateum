# Ommateum — 工业质检极少样本快速缺陷分割系统

面向工业质检的**极少样本快速缺陷分割系统**，解决新类型缺陷样本稀缺、人工标注成本高以及模型上线周期长等实际问题。

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
# 构建镜像
docker build -t ommateum .

# 运行（GPU）
docker run --gpus all -p 8000:8000 ommateum

# 运行（CPU）
docker run -p 8000:8000 ommateum
```

### 本地安装

```bash
# 安装生产依赖
pip install -r requirements.txt

# 开发环境
pip install -r requirements-dev.txt
```

## 开发

```bash
# 运行测试
pytest

# 代码检查
ruff check .
ruff format --check .
```

## Git 提交规范

本项目统一采用 Angular 提交规范，格式：`<type>(<scope>): <subject>`

- **feat** — 新功能
- **fix** — 问题修复
- **docs** — 文档更新
- **refactor** — 代码重构
- **chore** — 日常维护

> 每次提交只解决一个问题，保持提交历史整洁。

## 目录结构

```
├── Dockerfile           # 构建镜像
├── .dockerignore        # Docker 忽略规则
├── src/ommateum/        # 主代码
├── tests/               # 测试
├── docs/                # 文档
└── scripts/             # 工具脚本
```

## 许可证

详见 [LICENSE](LICENSE)。
