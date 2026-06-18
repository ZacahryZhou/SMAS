# SMAS / 社交媒体 Agent 系统

**S**ocial **M**edia **A**gent **S**ystem

> An orchestrated multi-agent pipeline for Instagram content: classify → brief → caption → image → preview → human review.  
> 一套编排式多 Agent 流水线，用于 Instagram 内容生产：分类 → 简报 → 文案 → 出图 → 预览 → 人工审核。

**Platform focus / 平台重点:** Instagram (Feed preview, 4:5)  
**Publish status / 发布状态:** Instagram Graph API publishing is **paused** / Ins API 发布 **暂缓**

---

## Table of Contents / 目录

- [What SMAS Does](#what-smas-does--smas-做什么)
- [Architecture](#architecture--架构概览)
- [Post Types & Image Paths](#post-types--image-paths--帖子类型与出图路径)
- [Project Status](#project-status--项目状态)
- [Tech Stack](#tech-stack--技术栈)
- [Directory Layout](#directory-layout--目录结构)
- [Quick Start](#quick-start--快速开始)
- [Configuration](#configuration--环境配置)
- [Usage](#usage--使用方式)
- [Review Workflow](#review-workflow--审核流程)
- [Command Reference](#command-reference--指令对照)
- [Output Files](#output-files--输出文件)
- [Troubleshooting](#troubleshooting--常见问题)
- [Documentation](#documentation--更多文档)

---

## What SMAS Does / SMAS 做什么

**EN**

SMAS turns a natural-language request (plus optional product images) into an Instagram-ready draft:

1. **Classify** the post type (`product_promo`, `event_campaign`, `general`)
2. **Creative brief** — shared “director script” for caption + image
3. **Caption** — Instagram copy tailored to post type
4. **Visual Director** — chooses render path A/B/C and image prompts
5. **Image Render** — fal.ai and/or Pillow template composition
6. **Preview** — Feed-style composite (`preview_feed.png`)
7. **Human review** — approve, skip, or edit before any publish step

You interact via **CLI**, **Telegram bot**, or **OpenClaw (小龙虾) bridge** on mobile.

**中文**

SMAS 根据你的自然语言需求（可选上传商品图），生成可审核的 Instagram 草稿：

1. **分类**帖子类型（商品推广 / 活动促销 / 通用）
2. **创意简报** — 文案与图片共用的「导演稿」
3. **文案** — 按类型生成 Ins 文案
4. **Visual Director** — 选择出图路径 A/B/C 与 prompt
5. **Image Render** — 调用 fal.ai 和/或 Pillow 模板合成
6. **预览** — 合成 Feed 样式图（`preview_feed.png`）
7. **人工审核** — 确认、跳过或修改后再定稿

支持 **CLI**、**Telegram Bot**、**OpenClaw 小龙虾** 手机桥接。

---

## Architecture / 架构概览

```text
User (CLI / Telegram / OpenClaw)
        │
        ▼
Intent Router  ──►  Orchestrator  ──►  Content Pipeline
   (tag intent)        (dispatch)           │
                                            ├─ Content Classifier   → brief.json
                                            ├─ Creative Brief Agent → creative_brief.json
                                            ├─ Caption Agent        → caption.json
                                            ├─ Visual Director      → visual_spec.json
                                            ├─ Image Render (A/B/C) → image.png
                                            └─ Preview Composer     → preview_feed.png
                                            │
                                            ▼
                                    Review Gate (ok / skip / edit)
```

| Layer / 层级 | Role / 职责 | Key files |
|--------------|-------------|-----------|
| **Channels** | User entry / 用户入口 | `channels/telegram_bot.py`, `scripts/openclaw_bridge.py` |
| **Orchestration** | Routing & state / 路由与状态 | `core/intent_router.py`, `core/orchestrator.py` |
| **Agents (LLM)** | DeepSeek-powered steps / DeepSeek 推理 | `agents/content_classifier.py`, `creative_brief_agent.py`, `caption_agent.py`, `visual_director.py` |
| **Pipeline** | Image & preview execution / 出图执行 | `pipeline/image_render.py`, `preview_composer.py`, `review_gate.py` |
| **Data** | Brand & artifacts / 品牌与工件 | `data/brand_profile.json`, `state/*.json` |

Full design doc: **[docs/DEV_ARCHITECTURE.md](docs/DEV_ARCHITECTURE.md)**

---

## Post Types & Image Paths / 帖子类型与出图路径

### Post types / 帖子类型

| `post_type` | EN | 中文 | Typical use |
|-------------|----|------|-------------|
| `product_promo` | Product promo | 商品推广 | Selling points, new item, soft CTA |
| `event_campaign` | Event / sale | 活动促销 | Dates, location, urgency, overlays |
| `general` | General | 通用 | Brand presence, everyday updates |

Specify optionally in the request:

```text
type: product promo     # English
类型：商品推广            # Chinese
```

If omitted, **Content Classifier** infers the type.  
未指定时由 **Content Classifier** 自动推断。

### Image render paths / 出图路径

| Path | Method / 方式 | Tool | When / 适用 |
|------|---------------|------|-------------|
| **A** | Text-to-image / 纯 AI 文生图 | fal `nano-banana-pro` | No product asset; general mood |
| **B** | Product reference edit / 商品参考生图 | fal edit + `data/assets/products/` | Product scene with reference photo |
| **C** | Template compose / 模板合成 | Pillow (+ optional rembg) | Events, badges, price tags, text overlay |

Override in request: `path: B` or `路径：C`  
环境变量：`SMAS_PRODUCT_RENDER_PATH=auto|b|c`

---

## Project Status / 项目状态

| Phase | Scope | Status |
|-------|-------|--------|
| M1–M3 | Profile, V1 pipeline, Telegram, review | ✅ Done |
| V2-A | Classifier + Creative Brief + typed captions | ✅ Done |
| V2-B | Visual Director + Path C + local assets | ✅ Done |
| V2-C | Path B product reference rendering | ✅ Done |
| V2-D | Review edit (caption / image / path) | ✅ Done |
| MVP-1 | R2 CDN + Instagram Graph API publish | ⏸ Paused |

---

## Tech Stack / 技术栈

| Capability | Technology |
|------------|------------|
| LLM (all agents) | [DeepSeek API](https://platform.deepseek.com/) (`deepseek-chat`, JSON output) |
| Text-to-image / edit | [fal.ai](https://fal.ai/) `nano-banana-pro` |
| Template / preview | Pillow, optional rembg |
| Orchestration | Python `Orchestrator` + optional LangGraph visualization |
| Mobile bridge | OpenClaw + `scripts/smas.sh` |

---

## Directory Layout / 目录结构

```text
SMAS/
├── main.py                 # CLI entry / CLI 入口
├── config.py               # Settings from .env
├── langgraph.json          # LangGraph Studio (visualization only)
│
├── agents/                 # LLM agents (DeepSeek)
│   ├── content_classifier.py
│   ├── creative_brief_agent.py
│   ├── caption_agent.py
│   ├── visual_director.py
│   └── profile_manager.py
│
├── core/                   # Orchestration & domain logic
│   ├── intent_router.py    # Natural language → intent tags
│   ├── orchestrator.py     # Dispatch generate / review / profile
│   ├── content_pipeline.py # Main generation chain
│   ├── job_store.py        # state/state.json
│   └── ...
│
├── pipeline/               # Non-LLM execution
│   ├── image_render.py     # Path A / B / C
│   ├── preview_composer.py
│   ├── review_gate.py
│   └── review_edit.py
│
├── channels/
│   └── telegram_bot.py
│
├── scripts/
│   ├── smas.sh             # OpenClaw entry
│   └── openclaw_bridge.py
│
├── tools/
│   ├── deepseek_client.py
│   └── fal_image.py
│
├── data/
│   ├── brand_profile.json  # Your brand (gitignored)
│   └── assets/products/    # Product images for Path B/C
│
├── state/                  # Per-job artifacts (generated)
│   ├── state.json
│   ├── brief.json
│   ├── creative_brief.json
│   ├── caption.json
│   ├── visual_spec.json
│   ├── image.png
│   └── preview_feed.png
│
└── docs/
    ├── DEV_ARCHITECTURE.md
    └── ARCHITECTURE_V2.md
```

---

## Quick Start / 快速开始

### Prerequisites / 前置条件

- Python 3.11+ (3.13 tested)
- `DEEPSEEK_API_KEY` (required)
- `FAL_KEY` (required for real images when `DRY_RUN=false`)

### Install / 安装

```bash
cd ~/Desktop/SMAS
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set at minimum:

```bash
DEEPSEEK_API_KEY=your_key
FAL_KEY=your_fal_key
DRY_RUN=false                    # set true to skip paid API calls during dev
```

### Verify APIs / 检查配置

```bash
python main.py check
```

### Brand profile / 品牌建档

```bash
python main.py profile           # interactive onboarding
python main.py profile show      # show current profile
```

Ensure `data/brand_profile.json` has `onboarding_complete: true` before generating.

### Generate a preview / 生成预览

```bash
python main.py generate "Create a post promoting our new cold brew coffee"
```

Output: `state/preview_feed.png` (+ JSON artifacts under `state/`)

---

## Configuration / 环境配置

| Variable | Description EN | 说明 |
|----------|------------------|------|
| `DRY_RUN` | `true` = placeholder image, no fal billing | `true` 时不调 fal，用占位图 |
| `DEEPSEEK_API_KEY` | DeepSeek API key | DeepSeek 密钥 |
| `DEEPSEEK_MODEL` | Default `deepseek-chat` | 模型名 |
| `FAL_KEY` | fal.ai API key | fal 密钥 |
| `SMAS_PRODUCT_RENDER_PATH` | `auto` \| `b` \| `c` for product promos | 商品推广默认出图策略 |
| `SMAS_SSL_VERIFY` | Set `false` only if proxy SSL issues on macOS | macOS 代理证书问题时可设 false |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Telegram |
| `TELEGRAM_CHAT_ID` | Allowed chat ID | 允许的聊天 ID |

MVP-1 (paused): `CF_R2_*`, `INSTAGRAM_*` — see `.env.example`

---

## Usage / 使用方式

### CLI

```bash
python main.py check
python main.py profile [show|reset|chat]
python main.py generate "<your request>"
python main.py edit "<edit instruction>"    # only while status=waiting_review
python main.py telegram                       # native Telegram bot
```

### Telegram (native bot)

1. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
2. Run `python main.py telegram`
3. Send `/generate Create a post about ...` or natural language (EN/ZH)

> **Do not** run `python main.py telegram` and OpenClaw with the **same bot token** at the same time.  
> **不要**让原生 Telegram Bot 与 OpenClaw **共用同一个 bot token**。

### OpenClaw (mobile / 手机)

```text
Phone Telegram → OpenClaw → scripts/smas.sh → openclaw_bridge.py → Orchestrator
```

OpenClaw skill path (example): `~/.openclaw/workspace/smas/SKILL.md`

---

## Review Workflow / 审核流程

After generation, `state/state.json` status becomes `waiting_review`.

| Action EN | 中文 | Result |
|-----------|------|--------|
| `ok` / `publish` / `confirm` | `发布` / `确认` | Save draft, mark approved |
| `skip` / `discard` / `cancel` | `跳过` / `取消` | Drop draft |
| `edit: bigger text` | `字大一点` | Re-render with edits |
| `move product right` | `商品往右` | Adjust composition |
| `path: C` | `路径：C` | Switch render path |
| `caption: more casual` | `改文案：更轻松` | Rewrite caption |

CLI edit while waiting:

```bash
python main.py edit "bigger text"
```

Publishing to Instagram is **not** automated in the current MVP.

---

## Command Reference / 指令对照

### Natural language triggers / 自然语言触发

| Intent | English examples | 中文示例 |
|--------|------------------|----------|
| Generate | `create a post about coffee`, `generate ...` | `做一条咖啡推广`, `生成...` |
| Profile | `profile`, `brand style` | `资料`, `风格`, `账号` |
| Approve | `ok`, `publish` | `发布`, `确认` |
| Skip | `skip`, `discard` | `跳过`, `取消` |
| Status | `/status`, `status` | `状态` |
| Help | `/help`, `help` | `帮助` |

### Slash commands / 斜杠命令

```text
/generate <request>
/profile
/status
/help
/start
/edit <instruction>    # in review state
```

---

## Output Files / 输出文件

| File | Produced by | Content |
|------|-------------|---------|
| `state/state.json` | Job store | Job ID, step, status, error |
| `state/brief.json` | Content Classifier | `post_type`, intent, goal |
| `state/creative_brief.json` | Creative Brief Agent | Headline, visual scene, overlay hints |
| `state/caption.json` | Caption Agent | Hook, body, hashtags, CTA |
| `state/visual_spec.json` | Visual Director | Path A/B/C, prompts, layout |
| `state/image.png` | Image Render | Raw post image |
| `state/preview_feed.png` | Preview Composer | Instagram Feed mockup |

---

## Troubleshooting / 常见问题

**EN**

| Issue | Fix |
|-------|-----|
| `Brand profile is not ready` | Run `python main.py profile`, set `onboarding_complete: true` |
| DeepSeek fails in Cursor sandbox | Run `python main.py check` in your **local terminal** |
| Bad / placeholder images | Set `DRY_RUN=false`, add real product PNG under `data/assets/products/` |
| `waiting_review` blocks new generate | Reply `ok` or `skip` first |
| Telegram token conflict | Use OpenClaw **or** `main.py telegram`, not both |
| File save conflict in editor | **Revert File** after agent edits, don't blind Overwrite |

**中文**

| 问题 | 处理 |
|------|------|
| 品牌资料未就绪 | 运行 `python main.py profile`，设 `onboarding_complete: true` |
| Cursor 里 API 不通 | 在**本机终端**运行 `python main.py check` |
| 图片差 / 占位图 | `DRY_RUN=false`，在 `data/assets/products/` 放真实商品图 |
| 无法新生成 | 先 `ok` 或 `skip` 结束上一条审核 |
| Telegram 冲突 | OpenClaw 与原生 bot 二选一 |
| 编辑器保存冲突 | Agent 改完后用 **Revert File**，不要误点 Overwrite |

---

## Documentation / 更多文档

| Doc | Description |
|-----|-------------|
| [docs/DEV_ARCHITECTURE.md](docs/DEV_ARCHITECTURE.md) | Main architecture, milestones, acceptance / 主架构文档 |
| [docs/ARCHITECTURE_V2.md](docs/ARCHITECTURE_V2.md) | V2 design notes & examples / V2 设计补充 |

---

## Roadmap / 路线图

- [x] V2 content engine (classify → brief → caption → visual → render → preview)
- [x] Human review + edit loop
- [ ] Image prompt quality tuning & asset validation
- [ ] Instagram Graph API + R2 CDN (MVP-1, blocked on Meta SMS verification)
- [ ] Multi-brand / scheduled posting (future)

---

## License

Private project — add a license if you plan to open-source.

私人项目 — 若开源请补充 License。
