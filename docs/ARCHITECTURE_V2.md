# SMAS 架构 V2 — 设计补充

> **主文档已合并至 [DEV_ARCHITECTURE.md](./DEV_ARCHITECTURE.md)**（架构、开发里程碑、模块清单、验收标准）。  
> 本文保留 V2 设计讨论中的细节与示例，便于查阅。V2.1 的执行计划见 [CONTENT_IMPROVEMENT_ROADMAP.md](./CONTENT_IMPROVEMENT_ROADMAP.md)。

---

## 与主文档的关系

| 内容 | 位置 |
|------|------|
| 流程、模块、里程碑、验收 | [DEV_ARCHITECTURE.md](./DEV_ARCHITECTURE.md) |
| 创意简报 / visual_spec 示例、类型扩展说明 | 本文 |

**代码现状**：V2 内容流水线已完成；V2.1 正在增强内容质量、Path 规则和类型确认。

---

## 1. 为什么要从 V1 升级到 V2

V1 假设所有帖子同一套路：`Topic → Caption → Image → Preview`。

V2 增加：

1. **帖子类型** — 推广、活动、通用，文案与图片策略不同  
2. **创意简报** — 文案与图片共用一份导演稿  
3. **专门图片 Agent** — Visual Director 定策略，Pipeline 执行 A/B/C 三条路径  
4. **用户素材** — 商品图可进入 Path B 参考生图或 Path C 模板合成
5. **V2.1 playbooks** — 每种帖子类型有稳定的文案、构图和 Path 规则

---

## 2. V2 总流程

```text
用户输入（想法 + 可选类型 + 可选素材）
        │
        ▼
Content Classifier → brief.json
        │
        ├─ 低置信度时：Type Confirm（用户回复 1/2/3）
        │
        ▼
Creative Brief Agent → creative_brief.json
        ├────────────────────┐
        ▼                    ▼
Caption Agent          Visual Director Agent → visual_spec.json
        │                    ▼
        │            Image Render Pipeline (A / B / C)
        │                    ▼
        └──────────► image.png
                    ▼
        Preview Composer → preview_feed.png
                    ▼
        Review Gate
```

---

## 3. 帖子类型

**第一版 MVP（已确认）**：`product_promo`、`event_campaign`、`general`

| 类型 | 文案 | 默认图片 |
|------|------|----------|
| product_promo | 卖点 + 场景 + CTA | 无素材 A；有素材 B；需要价签/叠字 C |
| event_campaign | 时间地点 + 紧迫感 | C（叠字） |
| general | V1 结构 | A |

**暂不实现**：`educational`（教程）  
**后期扩展**：`new_arrival`、`brand_story`、`seasonal`、`engagement`、`testimonial`

---

## 4. Creative Brief 示例

```json
{
  "post_type": "product_promo",
  "headline": "Lightweight bottle for summer commutes",
  "key_message": "12oz, fits car cup holder, keeps cold 24h",
  "caption_angle": "problem-solution, friendly, not pushy",
  "cta": "Ask if they want this color",
  "visual": {
    "scene": "clean desk by window, morning light",
    "product_placement": "center-right, hero shot",
    "composition": "rule_of_thirds, leave top-left for optional text",
    "color_mood": "warm, brand palette #F5F0EB",
    "text_on_image": {
      "enabled": true,
      "elements": ["NEW", "24h cold"],
      "style": "minimal sans-serif, small badge"
    },
    "use_user_assets": true,
    "asset_roles": { "product_01.png": "hero_product" }
  }
}
```

---

## 5. Visual Director + Image Render

```text
Creative Brief
      ▼
Visual Director Agent (LLM)  →  visual_spec.json
      ▼
Image Render Pipeline (代码)
  Path A — fal 文生图
  Path B — fal edit + 参考图（V2-C）
  Path C — 抠图 + Pillow 叠字（V2-B）
      ▼
image.png
```

| 概念 | 说明 |
|------|------|
| 构图 | 商品位置、留白区（如左上给 POP-UP） |
| 色彩 | 品牌色 + 活动对比色 |
| 图上文字 | 活动/推广用 Pillow；通用尽量无字 |

---

## 6. 已确认决策

- [x] 3 种帖子类型；教程去掉  
- [x] Visual Director Agent + Image Render Pipeline  
- [x] 活动允许叠字；商品先 Path C 后 Path B；素材先 `data/assets/`

---

## 7. 开发阶段（详见 DEV_ARCHITECTURE 第 6 节）

| 阶段 | 内容 |
|------|------|
| V2-A | Classifier + Brief + 按类型文案 |
| V2-B | Visual Director + Path C + 素材 |
| V2-C | Path B 商品参考生图 |
| V2-D | 审核 edit 增强 |
| V2.1-W1 | Playbooks + Path 硬规则 + 类型确认 |
| V2.1-W3 | Critic + Feedback Loop + wins JSONL |
| MVP-1 | Ins API（暂缓） |
