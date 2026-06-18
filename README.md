# SMAS

**S**ocial **M**edia **A**gent **S**ystem — 多 Agent 自媒体运营系统。

用户通过 Telegram（OpenClaw 小龙虾）或本地 CLI 输入想法，系统结合品牌资料库与帖子类型，生成文案、图片，并返回 Instagram Feed 样式预览供审核。Ins/Facebook API 发布 **暂缓**；当前专注内容引擎 V2 演进。

## 文档

- **[docs/DEV_ARCHITECTURE.md](docs/DEV_ARCHITECTURE.md)** — 架构、流程、模块、里程碑（主文档）
- [docs/ARCHITECTURE_V2.md](docs/ARCHITECTURE_V2.md) — V2 设计细节补充

## 当前状态

| 阶段 | 状态 |
|------|------|
| M1–M3（V1 建档、生成、预览、审核） | ✅ |
| V2-A（分类、简报、按类型文案） | ✅ |
| V2-B（Visual Director、Path C 模板合成） | ✅ |
| V2-C（Path B 商品参考生图） | ✅ |
| V2-D（审核 edit 增强） | ✅ |
| MVP-1（Ins 发布） | ⏸ 暂缓 |

## V2 流程（目标）

```text
用户输入 → Classifier → Creative Brief → Caption
                              ↓
                    Visual Director → Image Render (A/B/C)
                              ↓
                    Preview → Review →（发布暂缓）
```

帖子类型（第一版）：`product_promo` · `event_campaign` · `general`

## 技术栈

- LLM：DeepSeek API
- 生图：fal.ai `nano-banana-pro`（Path A/B）；Pillow + rembg（Path C 模板）
- 平台：Instagram（首期）
- 渠道：CLI + Telegram（OpenClaw 桥接）

## 目录结构

```text
SMAS/
├── agents/          # Profile、Classifier、Brief、Caption、Visual Director
├── channels/        # Telegram
├── core/            # Orchestrator、Intent Router、Brand Context、Asset Manager
├── pipeline/        # Image Render、Preview、Review、Publish（暂缓）
├── tools/           # DeepSeek、fal、http_download
├── data/            # brand_profile.json、assets/
├── state/           # 单次任务工件
├── scripts/         # smas.sh、openclaw_bridge.py
└── docs/
```

## 快速开始

```bash
cd ~/Desktop/SMAS
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY、FAL_KEY

python main.py profile          # 建档
python main.py generate "..."   # 生成预览 → state/preview_feed.png
```

## 开发节奏

**已完成**：M1 基础层 → M2 内容层 → M3 编排层  

**下一步**：V2-A（Classifier + Brief + 按类型文案）→ V2-B（Visual Director + Path C）→ V2-C（Path B）→ V2-D（审核增强）→ MVP-1（Ins API）

详见 [docs/DEV_ARCHITECTURE.md](docs/DEV_ARCHITECTURE.md) 第 6 节。
