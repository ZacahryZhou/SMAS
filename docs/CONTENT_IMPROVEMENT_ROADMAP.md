# SMAS Content Generation Improvement Roadmap / 内容生成精进路线图

> Version: **V2.1** (2026-06)  
> Status: **V2.1-W1 code landed** — ready for local verification  
> Parent doc: [DEV_ARCHITECTURE.md](./DEV_ARCHITECTURE.md)

---

## 1. Goal / 目标

**EN:** Raise single-post quality (caption + image) before building a multi-user website or analytics layer.  
**中文：** 在扩网站、做用户运营之前，先把「一条帖能发」做到稳定。

**Principle / 原则**

```text
Content quality first → Thin web shell → Publish API → User ops (analytics, trends)
内容质量优先 → 薄网站 → 发布 API → 用户运营（分析、热点）
```

---

## 2. Current pipeline / 当前流水线

```text
User request (+ optional assets)
    → Content Classifier        → brief.json
    → [Type confirm if low confidence]   ← V2.1 new
    → Creative Brief Agent      → creative_brief.json
    → Caption Agent             → caption.json
    → Visual Director           → visual_spec.json (Path A/B/C)
    → Image Render              → image.png
    → Preview Composer          → preview_feed.png
    → Review (ok / skip / edit)
```

See also: [PLAYBOOKS.md](./PLAYBOOKS.md) for per-type visual/caption standards.

---

## 3. Phased plan / 分阶段计划

| Phase | Focus | Status |
|-------|-------|--------|
| **V2.1-W1** | Playbooks + path hard rules + type confirm | ✅ Done |
| **V2.1-W2** | Brief tighter binding to Caption/Visual | ✅ Done |
| **V2.1-W3** | Critic Agent + feedback store | ✅ Code done, verify locally |
| **V2.1-W4** | Win examples → few-shot in prompts | ✅ Done |
| **V2.2** | Thin web UI (generate + review) | ⏳ Next |
| **MVP-1** | Ins Graph API + R2 + scheduler | ⏸ Blocked (Meta SMS) |

---

## 4. V2.1-W1 — Playbooks & routing (this sprint)

### 4.1 Playbook files / 宣传规范底座

| File | Purpose |
|------|---------|
| `data/playbooks/product_promo.json` | Product promo layout, Path B/C rules |
| `data/playbooks/event_campaign.json` | Event overlays, Path C rules |
| `data/playbooks/general.json` | Atmospheric Path A rules |
| `core/playbook.py` | Load + format for agent prompts |

Agents that consume playbooks:

- `creative_brief_agent.py`
- `caption_agent.py`
- `visual_director.py`

Current implementation status:

| Item | Status |
|------|--------|
| Playbook docs | ✅ Done |
| Playbook JSON files | ✅ Added |
| `core/playbook.py` loader | ✅ Added |
| Brief / Caption / Visual prompt injection | ✅ Done |
| Path B/C enforcement | ✅ Done |
| Type confirmation end-to-end | ✅ Done |
| Feedback on approve → wins JSONL | ✅ Done |

### 4.2 Path hard rules / 有素材必走对应 Path

Rules (enforced in `decide_default_path` + `_apply_path_rules`):

| Condition | Path |
|-----------|------|
| `event_campaign` | **C** |
| `product_promo` + assets + no overlay labels | **B** |
| `product_promo` + assets + overlay / `SMAS_PRODUCT_RENDER_PATH=c` | **C** |
| `product_promo` + no assets | **A** |
| `general` | **A** |
| User `path: X` in request | **X** (override) |

Path B without assets → fallback to A with reason logged.

### 4.3 Type confirmation / 用户选标签

When `post_type_confidence < SMAS_TYPE_CONFIRM_THRESHOLD` (default `0.8`) and user did not specify `type:`:

1. Classifier runs and writes `brief.json`
2. Job status → `confirm_post_type`
3. Orchestrator returns numbered choices (EN/ZH)
4. User replies `1` / `2` / `3` or `type: product promo`
5. Pipeline continues from Brief step with confirmed type

Env: `SMAS_TYPE_CONFIRM_THRESHOLD=0.8`

---

## 5. V2.1-W2 — Brief binding

- Caption payload must include: `headline`, `key_message`, `caption_angle`, `cta_hint`, `visual.scene`
- Visual Director prioritizes `creative_brief.visual` over loose caption text
- Reduce caption/image drift

**Implementation:**

| Item | File | Status |
|------|------|--------|
| Brief binding helpers | `core/brief_binding.py` | ✅ |
| Caption brief_directives + brief_refs | `agents/caption_agent.py` | ✅ |
| Visual visual_directives + brief_refs | `agents/visual_director.py` | ✅ |
| Enforce path prompts from brief scene | `agents/visual_director.py` | ✅ |
| Review shows headline/scene alignment | `pipeline/review_gate.py` | ✅ |
| Brief completeness gaps logged | `agents/creative_brief_agent.py` | ✅ |

**Acceptance:** Same brief → caption hook and image scene clearly aligned.

---

## 6. V2.1-W3 — Quality feedback loop

Not the same as "harness evolution" (research-level). We use a **practical feedback loop**:

```text
Generate → Critic scores (1-10) → User review (ok/skip/edit)
                ↓
         data/feedback/jobs/{job_id}.json
                ↓
    On approve → data/feedback/wins/{post_type}.jsonl
                ↓
    Next similar job → inject 1-2 win examples into prompts
```

| Component | File | Status |
|-----------|------|--------|
| Critic Agent | `agents/critic_agent.py` | ✅ |
| Feedback store | `core/feedback_store.py` | ✅ |
| Pipeline integration | `core/content_pipeline.py` | ✅ |
| Review prompt scores | `pipeline/review_gate.py` | ✅ |
| Re-score after edit | `pipeline/review_edit.py` | ✅ |
| Win examples | `data/feedback/wins/*.jsonl` | ✅ on approve |
| Job feedback | `data/feedback/jobs/*.json` | ✅ on generate + review |

References:

- [AWS Evaluator reflect-refine loop](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/evaluator-reflect-refine-loop-patterns.html)
- [Anthropic — Demystifying evals for agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

---

## 7. V2.1-W4 — Learning from wins

- After `approve`, append compact record to wins JSONL
- `core/playbook.py` loads top N wins for same `post_type`, ranked by `overall_score`
- Inject as few-shot block in Brief / Caption / Visual / Critic prompts
- Optional later: DSPy / vector search when N > 50

**Implementation:**

| Item | Status |
|------|--------|
| Rich win record on approve (`headline`, `key_message`, `body_preview`, score) | ✅ |
| Rank wins by critic score + dedupe similar hooks | ✅ |
| Config: `SMAS_WINS_EXAMPLE_LIMIT`, `SMAS_WINS_MIN_SCORE` | ✅ |
| Critic compares draft to approved benchmarks | ✅ |

---

## 8. What we are NOT doing yet

- Full multi-user SaaS
- Trend scanner / analytics dashboard
- LangGraph runtime migration (keep visualization only)
- share.js-style web share links (not Ins API publish)

---

## 9. Acceptance checklist / 验收清单 (Dario coffee example)

- [ ] `DRY_RUN=false`, real product PNG in `data/assets/products/`
- [ ] `product_promo` + asset → Path B or C (never A)
- [ ] `visual_spec.json` has non-empty `path_b_edit_prompt` on Path B
- [ ] Preview looks acceptable for brand (subjective, 3/5 runs)
- [ ] Type confirm appears when confidence low
- [x] `ok` saves feedback job record + wins JSONL
- [ ] Critic scores appear in review prompt after generate

---

## 10. Implementation log / 实施记录

| Date | Change |
|------|--------|
| 2026-06 | Added `docs/CONTENT_IMPROVEMENT_ROADMAP.md`, `docs/PLAYBOOKS.md` |
| 2026-06 | Documented V2.1 playbooks, Path A/B/C rules, type confirmation, and feedback loop |
| 2026-06 | Added `data/playbooks/*.json`, `core/playbook.py` |
| 2026-06 | Wired playbooks into Brief / Caption / Visual Director |
| 2026-06 | Type confirmation in pipeline + orchestrator + intent_router + CLI `confirm` |
| 2026-06 | Path hard rules + playbook Path B/A prompts in visual_director |
| 2026-06 | V2.1-W4 ranked wins few-shot, rich win records, critic benchmarks |

---

## 11. Related docs

- [PLAYBOOKS.md](./PLAYBOOKS.md) — Per-type promo standards
- [DEV_ARCHITECTURE.md](./DEV_ARCHITECTURE.md) — System architecture
- [../README.md](../README.md) — Quick start
