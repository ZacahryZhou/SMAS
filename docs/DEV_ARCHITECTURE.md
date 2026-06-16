# SMAS 开发架构

> Social Media Agent System — Phase 1：Instagram 内容运营

## 1. 项目目标

用户通过 Telegram 或 CLI 输入一句话，例如「帮我做一条关于夏季收纳的 Instagram 帖」，系统会：

1. 读取品牌资料库（`data/brand_profile.json`）
2. 根据频道类型、风格、受众理解需求
3. 生成选题 → 文案 → 图片（fal `nano-banana-pro`，4:5）
4. 合成 Instagram Feed 样式预览图
5. 返回用户审核（MVP-0 本地；MVP-1 Telegram）

---

## 2. 阶段范围

| 阶段 | 内容 | 时间 |
|------|------|------|
| **MVP-0** | 建档、一句话生成、预览图、本地 `state/` | 3–5 天 |
| **MVP-1** | R2、Ins 发布、Telegram 审核、24h 数据 | 1–2 周 |
| **MVP-2** | Web、多账号、FB/WhatsApp、视频 | 2–4 周 |

MVP-0 **不做**：真发布、FB、WhatsApp、Reels、自动评论。

---

## 3. 架构图

```text
User → Channel (CLI / Telegram) → Orchestrator
                                      ├─ Intent Router
                                      ├─ Brand Context ← brand_profile.json
                                      └─ Pipeline
                                           Topic → Caption → Image
                                           → Preview Composer → Review Gate
                                           → Publisher / Analytics (MVP-1+)
```

---

## 4. 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| Profile Manager | `agents/profile_manager.py` | 对话建档、修改资料库 |
| Brand Context | `core/brand_context.py` | 读取 profile，生成 prompt 片段 |
| Intent Router | `core/intent_router.py` | 识别建档 / 生成 / 审核 |
| Topic Agent | `agents/topic_agent.py` | guided / auto 选题 |
| Caption Agent | `agents/caption_agent.py` | Ins 文案 JSON |
| Image Agent | `agents/image_agent.py` | prompt + fal 生图 |
| Preview Composer | `pipeline/preview_composer.py` | Ins 样式合图 |
| Review Gate | `pipeline/review_gate.py` | ok / skip / edit |
| Orchestrator | `core/orchestrator.py` | 状态机、落盘 |

---

## 5. 里程碑与实现顺序

### M1：基础层（Step 1–2）

- `config.py`
- `tools/deepseek_client.py`
- `tools/fal_client.py`
- `core/brand_context.py`
- `agents/profile_manager.py`
- CLI：`python main.py profile`

**验收**：能对话建档并写入 `data/brand_profile.json`。

### M2：内容层（Step 3–4）

- `agents/topic_agent.py`
- `agents/caption_agent.py`
- `agents/image_agent.py`
- `pipeline/preview_composer.py`

**验收**：`python main.py generate "..."` 产出 `state/preview_feed.png`。

### M3：编排层（Step 5–6）

- `core/intent_router.py`
- `core/orchestrator.py`
- `main.py`
- `channels/telegram_bot.py`
- `pipeline/review_gate.py`

**验收**：Telegram 收预览、回复 ok/skip。

---

## 6. 数据文件

```text
data/brand_profile.json     # 品牌资料库
state/state.json            # 任务状态
state/topic.json
state/caption.json
state/image.png
state/preview_feed.png
```

`brand_profile.json` 核心字段：`account`、`niche`、`voice`、`visual`、`topic_sources`、`onboarding_complete`。

---

## 7. 技术选型

- **LLM**：DeepSeek，`response_format: json_object`，Pydantic 校验
- **生图**：`fal-ai/nano-banana-pro`，`aspect_ratio=4:5`，`resolution=1K`
- **预览**：Pillow，1080 宽，主图 1080×1350
- **发布（MVP-1）**：Instagram Graph API v25+，Cloudflare R2

---

## 8. 环境变量

MVP-0：

```text
DRY_RUN=true
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
FAL_KEY=
```

MVP-1 增加：`TELEGRAM_*`、`CF_R2_*`、`INSTAGRAM_*`。

---

## 9. MVP-0 验收清单

- [ ] CLI 建档 / 改资料
- [ ] 一句话 → `topic.json`
- [ ] `caption.json`
- [ ] fal → `image.png`
- [ ] `preview_feed.png`
- [ ] 工件均在 `state/`
