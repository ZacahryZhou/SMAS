# SMAS Playbooks / 宣传规范底座

> Used by Creative Brief, Caption, and Visual Director agents.  
> 供简报、文案、视觉导演 Agent 注入 prompt，提高稳定性。

Files live in `data/playbooks/{post_type}.json`.

---

## 1. Why playbooks? / 为什么需要

| Without | With playbook |
|---------|---------------|
| LLM invents layout each time | Consistent 4:5 Ins standards |
| Weak Path B prompts | Scene + product placement templates |
| Caption/image drift | Shared vocabulary per post type |

Based on industry practice: 4:5 (1080×1350), product 60–80% frame, minimal on-image text for Path A/B, overlays only on Path C.

References:

- [Instagram product photos guide](https://retouchable.ai/blog/instagram-ready-product-photos-guide/)
- [4:5 aspect ratio ads](https://cropink.com/4-5-aspect-ratio)
- [Instagram post design 2026](https://usekodo.ai/guides/instagram-post-design-guide-2026)

---

## 2. File structure

```json
{
  "post_type": "product_promo",
  "label_en": "Product promo",
  "label_zh": "商品推广",
  "caption_guidance": "...",
  "visual_guidance": "...",
  "path_rules": "...",
  "composition": {
    "aspect_ratio": "4:5",
    "resolution": "1080x1350",
    "product_frame_pct": "60-80",
    "safe_zone": "center, avoid top/bottom 10% for UI"
  },
  "prompt_snippets": {
    "path_a": "...",
    "path_b": "...",
    "path_c": "..."
  }
}
```

---

## 3. Per-type summary

### product_promo

| Item | Rule |
|------|------|
| Default path (with asset) | B (scene) or C (badges/price) |
| Image | Hero product, clean background, lifestyle context |
| Caption | Hook + 3 bullets + soft CTA |
| On-image text | Path C only (Pillow), not AI text |

### event_campaign

| Item | Rule |
|------|------|
| Default path | C |
| Image | Bold focal area, room for date/time overlay |
| Caption | Time, place, urgency |
| On-image text | 1–3 short uppercase labels |

### general

| Item | Rule |
|------|------|
| Default path | A |
| Image | Atmospheric, minimal promo |
| Caption | Brand voice, light engagement |
| On-image text | Usually off |

---

## 4. Code integration

```python
from core.playbook import load_playbook, format_playbook_block

playbook = load_playbook("product_promo")
block = format_playbook_block("product_promo")  # injected into SYSTEM_PROMPT
```

---

## 5. Wins / 成功案例（V2.1-W4）

Approved jobs append to:

```text
data/feedback/wins/product_promo.jsonl
data/feedback/wins/event_campaign.jsonl
data/feedback/wins/general.jsonl
```

`format_win_examples(post_type)` returns few-shot text for agents. Wins are ranked by `overall_score` (highest first), deduped by hook, and filtered by `SMAS_WINS_MIN_SCORE` when set.

Each approved win stores: `headline`, `hook`, `key_message`, `scene`, `path`, `body_preview`, `overall_score`.

---

## 6. Editing playbooks

1. Edit JSON under `data/playbooks/`
2. Run `python main.py generate "..."` for that type
3. Compare `state/visual_spec.json` and `state/caption.json`
4. Update roadmap checklist in [CONTENT_IMPROVEMENT_ROADMAP.md](./CONTENT_IMPROVEMENT_ROADMAP.md)

Do not put secrets in playbook files.
