# SMAS 开发与架构

> **S**ocial **M**edia **A**gent **S**ystem — Instagram 内容运营  
> 文档版本：**V2**（2026-06）  
> 代码现状：**V1 已完成** → 正在按 V2 演进

---

## 1. 项目目标

用户通过 **CLI** 或 **Telegram（OpenClaw 小龙虾）** 输入想法，可选指定帖子类型、上传商品图。系统结合品牌资料库，自动完成：

1. 判断帖子类型（商品推广 / 活动促销 / 通用）
2. 生成创意简报（文案与图片共用的导演稿）
3. 按类型生成 Ins 文案
4. 由 Visual Director 定图片策略，Pipeline 出图（纯 AI / 模板合成 / 商品参考生图）
5. 合成 Instagram Feed 样式预览
6. 人工审核（`ok` / `skip` / `edit`）
7. **发布 Ins API 暂缓**（等 Meta 开发者账号短信验证通过）

---

## 2. 实现状态总览

| 阶段 | 内容 | 状态 |
|------|------|------|
| **M1** 基础层 | 配置、DeepSeek、fal、建档、Brand Context | ✅ 完成 |
| **M2** 内容层 | Topic → Caption → Image → Preview | ✅ 完成 |
| **M3** 编排层 | Intent Router、Orchestrator、Telegram、Review | ✅ 完成 |
| **V2-A** | Classifier + Creative Brief + 按类型文案 | ✅ 完成 |
| **V2-B** | Visual Director + Path C 模板合成 + 本地素材 | ✅ 完成 |
| **V2-C** | Path B 商品参考生图 | ✅ 完成 |
| **V2-D** | 审核增强（按类型 edit） | ✅ 完成 |
| **MVP-1** | R2 CDN + Instagram Graph API 发布 | ⏸ 暂缓 |

**当前流水线（V1 代码）**：`Topic → Caption → Image → Preview → Review`  
**目标流水线（V2）**：见第 3 节。

---

## 3. V2 总流程

```text
用户输入
  ├─ 想法 / 主题
  ├─ 帖子类型（可选，不填则 LLM 推断）
  └─ 素材（可选：商品图、Logo）
        │
        ▼
Channel (CLI / Telegram) → Intent Router → Orchestrator
        │
        ├─ Brand Context ← data/brand_profile.json
        └─ Asset Manager ← data/assets/
        │
        ▼
Content Classifier          → state/brief.json
        ▼
Creative Brief Agent        → state/creative_brief.json
        ├──────────────────────────┐
        ▼                          ▼
Caption Agent (按类型)      Visual Director Agent
→ state/caption.json        → state/visual_spec.json
                                    ▼
                            Image Render Pipeline
                            ├─ Path A  纯 AI (fal)
                            ├─ Path B  商品参考 (fal edit)
                            └─ Path C  模板合成 (Pillow + rembg)
                                    ▼
                            state/image.png
        └──────────────────────────┘
                    ▼
        Preview Composer → state/preview_feed.png
                    ▼
        Review Gate → ok / skip / edit
                    ▼
        Publish（MVP-1，暂缓）
```

### 3.1 系统分层

```text
┌─────────────────────────────────────────────────────────────┐
│ 渠道 channels/          CLI · Telegram · OpenClaw 桥接       │
├─────────────────────────────────────────────────────────────┤
│ 编排 core/              Intent Router · Orchestrator         │
├─────────────────────────────────────────────────────────────┤
│ Agent agents/           Classifier · Brief · Caption         │
│                         Visual Director · Profile Manager    │
├─────────────────────────────────────────────────────────────┤
│ Pipeline pipeline/      Image Render · Preview · Review      │
├─────────────────────────────────────────────────────────────┤
│ 工具 tools/             DeepSeek · fal · Pillow · rembg    │
├─────────────────────────────────────────────────────────────┤
│ 数据 data/ + state/     品牌资料 · 素材库 · 任务工件         │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 帖子类型（Post Type）

**第一版 MVP 只做 3 种**（已确认）：

| `post_type` | 中文 | 文案结构 | 默认图片路径 |
|-------------|------|----------|--------------|
| `product_promo` | 商品推广 | hook → 3 卖点 → 场景 → CTA → 标签 | 无素材：**A**；有素材：**C** |
| `event_campaign` | 活动促销 | hook → 时间地点 → 紧迫感 → CTA | **C**（Pillow 叠字） |
| `general` | 通用 | V1 结构 | **A** |

用户可主动指定；未指定时 **Content Classifier** 推断。  
`educational`（教程）及 `brand_story`、`seasonal` 等 **后期扩展**，枚举预留。

---

## 5. 模块职责

### 5.1 已实现（V1）

| 模块 | 文件 | 职责 |
|------|------|------|
| Profile Manager | `agents/profile_manager.py` | 对话建档、修改资料库 |
| Brand Context | `core/brand_context.py` | 读取 profile，生成 prompt 片段 |
| Intent Router | `core/intent_router.py` | 建档 / 生成 / 审核 |
| Orchestrator | `core/orchestrator.py` | 状态机、任务调度 |
| Topic Agent | `agents/topic_agent.py` | guided 选题（V2 可并入 Brief） |
| Caption Agent | `agents/caption_agent.py` | Ins 文案 JSON |
| Image Agent | `agents/image_agent.py` | V1：prompt + fal 文生图 |
| Content Pipeline | `core/content_pipeline.py` | V1 串联 Topic→Caption→Image→Preview |
| Preview Composer | `pipeline/preview_composer.py` | Ins Feed 样式合图 |
| Review Gate | `pipeline/review_gate.py` | ok / skip / edit |
| Job Store | `core/job_store.py` | `state/state.json` 任务状态 |
| Telegram Bot | `channels/telegram_bot.py` | Telegram 交互（勿与 OpenClaw 同 token 并行） |
| OpenClaw 桥接 | `scripts/openclaw_bridge.py`, `scripts/smas.sh` | 小龙虾调 SMAS |

### 5.2 待开发（V2）

| 模块 | 计划文件 | 职责 |
|------|----------|------|
| Content Classifier | `agents/content_classifier.py` | 判断 post_type、用户意图 |
| Creative Brief Agent | `agents/creative_brief_agent.py` | 创意简报（导演稿） |
| Caption Agent V2 | `agents/caption_agent.py` | 按 3 种 post_type 分模板 |
| Visual Director Agent | `agents/visual_director.py` | 图片策略、构图、色彩、叠字规格 |
| Image Render Pipeline | `pipeline/image_render.py` | Path A/B/C 执行 |
| Asset Manager | `core/asset_manager.py` | 素材存取、校验、抠图预处理 |
| Content Pipeline V2 | `core/content_pipeline.py` | 串联 V2 全流程 |

### 5.3 图片层：导演 vs 执行

| 层 | 角色 | 说明 |
|----|------|------|
| **Visual Director Agent** | LLM 导演 | 读 brief + 素材，输出 `visual_spec.json` |
| **Image Render Pipeline** | 代码执行 | 调 fal / Pillow / rembg，产出 `image.png` |
| **Asset Manager** | 工具 | 被 Director 与 Pipeline 共用 |

**三条路径**

| Path | 做法 | 工具 | 适用 |
|------|------|------|------|
| **A** | 纯 AI 文生图 | fal `nano-banana-pro` | general；无素材推广氛围图 |
| **B** | 商品参考生图 | fal edit / reference | 有商品图、要场景感（V2-C） |
| **C** | 模板合成 | Pillow + rembg 抠图 + 叠字 | 活动类；推广价签/NEW |

实现顺序：**A → C → B**（均已完成）。

---

## 6. 开发里程碑与验收

### M1–M3（已完成）

**M1 验收**：`python main.py profile` 可建档 → `data/brand_profile.json`

**M2 验收**：`python main.py generate "..."` → `state/preview_feed.png`

**M3 验收**：Telegram / OpenClaw 收预览、回复 ok/skip

### V2-A：分类 + 简报 + 按类型文案

**新增**

- `agents/content_classifier.py`
- `agents/creative_brief_agent.py`
- `schemas/brief.py`, `schemas/creative_brief.py`
- 更新 `agents/caption_agent.py`（3 种模板）
- 更新 `core/content_pipeline.py`（接入 Classifier + Brief）

**验收**

- [x] 一句话自动推断 `post_type` 写入 `state/brief.json`
- [x] 产出 `state/creative_brief.json`
- [x] `caption.json` 含 `post_type` 且结构因类型而异
- [x] 图片由 Visual Director + Image Render Pipeline（Path A / C）

### V2-B：Visual Director + Path C + 素材

**新增**

- `agents/visual_director.py`
- `pipeline/image_render.py`（Path A + Path C）
- `core/asset_manager.py`
- `data/assets/products/`, `data/assets/logos/`
- `pipeline/templates/`（活动/推广模板）

**验收**

- [x] `event_campaign` 产出带叠字的 `image.png`（Pillow，非 AI 写字）
- [x] 本地 `data/assets/products/*.png` 可抠图合成进预览
- [x] `visual_spec.json` 记录 path、构图、叠字规格

### V2-C：Path B 商品参考生图

**新增**

- `pipeline/image_render.py` 扩展 Path B
- fal edit / reference images 集成

**验收**

- [x] `product_promo` + 商品图默认走 Path B（场景参考生图）
- [x] 带价签/叠字需求走 Path C；可用 `SMAS_PRODUCT_RENDER_PATH=c` 强制模板
- [x] 用户可在请求里写 `路径：B` / `路径：C` 覆盖
- [x] fal `nano-banana-pro/edit` 上传本地商品图作 reference

### V2-D：审核增强

**新增 / 更新**

- `core/edit_parser.py`：解析修改指令
- `pipeline/review_edit.py`：局部重跑 caption / image / preview
- `core/intent_router.py`、`core/orchestrator.py`：审核态识别 edit
- `main.py edit`：CLI 修改命令

**验收**

- [x] `edit: 字大一点` / `字小一点` 调整 Path C 叠字大小
- [x] `商品往右/左/上/下` 调整商品位置
- [x] `路径：B/C/A` 切换出图路径并重生图
- [x] `改文案：...` 局部重写 caption 并更新预览
- [x] Telegram / OpenClaw 审核态直接发修改意见

### MVP-1：发布（暂缓）

- `tools/cdn_uploader.py`（Cloudflare R2）
- `tools/instagram_api.py`
- `pipeline/publisher.py`
- **阻塞**：Meta 开发者账号 SMS 验证未通过

---

## 7. 数据与目录

### 7.1 品牌与素材

```text
data/
├── brand_profile.json       # 品牌资料（gitignore）
├── brand_profile.example.json
└── assets/
    ├── products/            # 商品图（V2-B）
    ├── logos/
    └── uploads/             # 单次任务临时上传
```

`brand_profile.json` 核心字段：`account`、`niche`、`voice`、`visual`、`topic_sources`、`onboarding_complete`。  
V2 扩展（计划）：`assets.default_product`、`assets.logo`。

### 7.2 任务工件

**V1（当前）**

```text
state/
├── state.json
├── topic.json
├── caption.json
├── image.png
└── preview_feed.png
```

**V2（目标）**

```text
state/
├── state.json
├── brief.json              # Classifier 输出
├── creative_brief.json     # 创意简报
├── caption.json
├── visual_spec.json        # Visual Director 输出
├── image.png
└── preview_feed.png
```

### 7.3 `visual_spec.json` 示例

```json
{
  "path": "C",
  "path_reason": "event_campaign needs reliable text overlay",
  "composition": { "layout": "hero_center", "product_position": [0.55, 0.5] },
  "color": { "background": "#F5F0EB", "accent": "#E85D4C" },
  "text_overlay": {
    "enabled": true,
    "lines": [
      { "text": "POP-UP", "zone": "top-left", "size": "large" },
      { "text": "Sat 2PM · Vancouver", "zone": "bottom-center", "size": "medium" }
    ]
  },
  "assets_used": [{ "path": "data/assets/products/bottle.png", "role": "hero_product" }]
}
```

---

## 8. 用户交互

| 方式 | 示例 |
|------|------|
| 一句话 | 「帮我做一条推广水杯的 Ins 帖，强调轻便」 |
| 指定类型 | 「类型：活动促销。周六 2pm 温哥华 pop-up」 |
| 带素材 | 上传 `product.jpg` + 「用这张图做商品推广」 |
| 审核 | 预览图 → `ok` / `skip` / `edit: 字大一点` |

**渠道**

- 本地：`python main.py generate "..."`  
- Telegram：通过 OpenClaw 小龙虾 + `scripts/smas.sh`（勿与 `python main.py telegram` 同 bot token 并行）

---

## 9. 技术选型

| 能力 | 技术 |
|------|------|
| LLM | DeepSeek API，`response_format: json_object`，Pydantic 校验 |
| 文生图 Path A | `fal-ai/nano-banana-pro`，`aspect_ratio=4:5`，`resolution=1K` |
| 参考生图 Path B | fal edit / reference images |
| 模板合成 Path C | Pillow + rembg |
| 预览 | Pillow，1080 宽，主图 1080×1350 |
| 发布（暂缓） | Instagram Graph API v25+，Cloudflare R2 |

---

## 10. 环境变量

```text
# MVP-0 / V2
DRY_RUN=true
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
FAL_KEY=
SMAS_SSL_VERIFY=true          # macOS SSL 问题时可为 false

# M3 / Telegram（与 OpenClaw 二选一）
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# MVP-1（暂缓）
CF_R2_*
INSTAGRAM_*
```

---

## 11. 风险与边界

| 项 | 说明 |
|----|------|
| 商品还原度 | Path B 不保证 100% 一致；Path C 抠图更准 |
| 图上文字 | 活动类用 Pillow 叠字，不靠 AI 写字 |
| Ins API | Meta SMS 验证通过前，手动发帖 |
| OpenClaw | 与 SMAS 原生 Telegram bot 勿共用 token |

---

## 12. 已确认的产品决策

- [x] 帖子类型先做 3 种：`product_promo`、`event_campaign`、`general`
- [x] 教程 `educational` 暂不实现
- [x] 图片层：**Visual Director Agent** + **Image Render Pipeline**
- [x] 活动类允许图上文字（Pillow 叠字）
- [x] 商品进图：先 Path C，后 Path B
- [x] 素材上传：先本地 `data/assets/`

---

## 13. 相关文档

- [ARCHITECTURE_V2.md](./ARCHITECTURE_V2.md) — V2 设计细节与历史讨论记录
- [../README.md](../README.md) — 项目概览与快速开始
