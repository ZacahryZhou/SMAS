# SMAS

**S**ocial **M**edia **A**gent **S**ystem — 多 Agent 自媒体运营系统。

当前目标是先做 **Instagram 内容生产 MVP**：用户通过 Telegram 或本地 CLI 说一句需求，系统结合品牌资料库与频道风格，生成选题、文案、图片，并返回一张贴近 Instagram 信息流样式的预览图供审核。MVP 阶段先本地 dry-run，不直接发布。

## 文档

- [docs/DEV_ARCHITECTURE.md](docs/DEV_ARCHITECTURE.md)

## 技术栈

- LLM：DeepSeek API
- 生图：fal.ai `fal-ai/nano-banana-pro`
- 平台：Instagram（首期）
- 渠道：Telegram（MVP-1），后续 WhatsApp / Web

## 目录结构

```text
SMAS/
├── agents/      # Profile、Topic、Caption、Image
├── channels/    # Telegram / 未来 WhatsApp / Web
├── core/        # Orchestrator、Intent Router、Brand Context
├── pipeline/    # Preview、Review、Publish、Analytics
├── tools/       # DeepSeek、fal、Instagram API
├── data/        # brand_profile.json
├── state/       # 单次任务中间文件
├── schemas/
└── docs/
```

## 开发节奏

按里程碑交付：**M1 基础层 → M2 内容层 → M3 编排层**。详见开发架构文档第 6 节。

## 快速开始（M1 完成后）

```bash
cd ~/Desktop/SMAS
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
