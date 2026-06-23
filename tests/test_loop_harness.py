from __future__ import annotations

from core.asset_alignment import (
    apply_asset_alignment,
    build_product_corpus,
    pick_best_asset,
    score_asset_fit,
)
from core.auto_refine import choose_refine_scope, should_auto_refine


def test_score_asset_fit_gelato_bottle_mismatch():
    corpus = "handcrafted gelato in a white ceramic bowl on a cafe table"
    assert score_asset_fit("assets/products/sample_bottle.png", corpus) < 0.2


def test_score_asset_fit_neutral_when_no_signal():
    assert score_asset_fit("assets/products/item.png", "abstract brand mood") == 0.5


def test_pick_best_asset_prefers_matching_name():
    corpus = "gelato scoop in bowl summer promo"
    assets = ["assets/products/sample_bottle.png", "assets/products/gelato_bowl.png"]
    assert pick_best_asset(assets, corpus) == "assets/products/gelato_bowl.png"


def test_apply_asset_alignment_fallback_path_b_to_a():
    creative_brief = {
        "headline": "Summer gelato",
        "visual": {"scene": "gelato in ceramic bowl on wooden cafe table"},
    }
    classification = {
        "user_request": "Gelato promo",
        "assets_available": ["assets/products/sample_bottle.png"],
    }
    visual_spec = {
        "path": "B",
        "path_reason": "test",
        "assets_used": [{"path": "assets/products/sample_bottle.png", "role": "hero_product"}],
    }
    report = apply_asset_alignment(
        visual_spec,
        creative_brief=creative_brief,
        classification=classification,
    )
    assert report["issues"]
    assert visual_spec["path"] == "A"
    assert visual_spec["assets_used"] == []
    assert any("Fallback Path B" in action for action in report["actions"])


def test_should_auto_refine_on_asset_critic_flag():
    critic = {
        "overall_score": 9,
        "caption_score": 9,
        "visual_score": 8,
        "alignment_score": 9,
        "issues": ["Asset sample_bottle.png mismatches gelato scene"],
        "suggestions": [],
    }
    ok, reason = should_auto_refine(critic, retry_count=0)
    assert ok is True
    assert "asset" in reason.lower()


def test_should_auto_refine_respects_max_retries():
    critic = {"overall_score": 4, "issues": [], "suggestions": []}
    ok, _ = should_auto_refine(critic, retry_count=1, max_retries=1)
    assert ok is False


def test_choose_refine_scope_visual_for_asset_issue():
    critic = {
        "overall_score": 9,
        "caption_score": 9,
        "visual_score": 8,
        "alignment_score": 9,
        "issues": ["Visual spec uses sample_bottle.png but scene describes gelato"],
        "suggestions": [],
    }
    assert choose_refine_scope(critic) == "visual"


def test_build_product_corpus_includes_scene():
    corpus = build_product_corpus(
        creative_brief={"visual": {"scene": "gelato bowl"}, "headline": "Summer"},
        classification={"user_request": "gelato promo"},
    )
    assert "gelato" in corpus
    assert "summer" in corpus
