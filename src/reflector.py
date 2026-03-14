"""Hierarchical reflector agent (L1/L2/L3) for SoA quality checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


ReflectorCall = Callable[[str, dict[str, Any], str, int], str]


def _call_level(
    level_name: str,
    prompt_path: str,
    output_path: str,
    payload: dict[str, Any],
    llm_caller: ReflectorCall,
) -> tuple[bool, dict[str, Any], str | None]:
    """Run one reflector level and parse JSON safely."""
    try:
        raw = llm_caller(prompt_path, payload, output_path, 3)
        parsed = json.loads(raw)
        passed = bool(parsed.get("pass", False))
        return passed, parsed, None
    except Exception as e:
        return False, {"pass": False, "issues": [f"{level_name} parse/runtime error: {e}"]}, str(e)


def run_reflector(state: dict[str, Any], llm_caller: ReflectorCall | None = None) -> dict[str, Any]:
    """Run L1 -> L2 -> L3 reflector checks with short-circuiting."""
    print("\n[Node: Reflector]")

    if llm_caller is None:
        # Lazy import to avoid module cycles when used outside nodes.py
        from src.graph.nodes import call_llm as llm_caller  # type: ignore

    draft = state.get("soa_draft")
    if not draft:
        draft_path = Path("artifacts/soa/state_of_the_art.md")
        if not draft_path.exists():
            draft_path = Path("artifacts/soa/state_of_the_art.tex")
        if draft_path.exists():
            draft = draft_path.read_text(encoding="utf-8", errors="ignore")

    if not draft:
        print("  ERROR: No SoA draft available for reflector")
        return {
            "reflector_feedback": {},
            "reflector_passed_level": 0,
            "pipeline_stage": "reflector_failed",
            "errors": [{"node": "reflector", "error": "No SoA draft available for reflector"}],
        }

    thematic_contract = state.get("thematic_contract", {})
    extracted_ids = sorted(list((state.get("extracted_facts") or {}).keys()))

    base_payload = {
        "thematic_contract": thematic_contract,
        "soa_draft": draft,
        "extracted_paper_ids": extracted_ids,
    }

    feedback: dict[str, Any] = {}
    errors: list[dict[str, str]] = []

    # Level 1: Outline-level check
    l1_pass, l1_data, l1_err = _call_level(
        "L1",
        "prompts/reflector_L1.system.txt",
        "artifacts/soa/reflector_L1.json",
        base_payload,
        llm_caller,
    )
    feedback["L1"] = l1_data

    if l1_err:
        errors.append({"node": "reflector", "error": l1_err})

    if not l1_pass:
        print("  ✗ L1 failed (outline)")
        feedback["correction_brief"] = {
            "level": "L1",
            "issues": l1_data.get("issues", []),
            "instruction": "Fix outline and section-theme alignment before deeper edits.",
        }

        Path("artifacts/soa").mkdir(parents=True, exist_ok=True)
        with open("artifacts/soa/reflector_feedback.json", "w", encoding="utf-8") as f:
            json.dump(feedback, f, indent=2)

        return {
            "reflector_feedback": feedback,
            "reflector_passed_level": 0,
            "reflector_rewrite_attempts": int(state.get("reflector_rewrite_attempts", 0)) + 1,
            "pipeline_stage": "reflector_l1_failed",
            "errors": errors,
        }

    # Level 2: Section-level argument arc/coherence
    l2_pass, l2_data, l2_err = _call_level(
        "L2",
        "prompts/reflector_L2.system.txt",
        "artifacts/soa/reflector_L2.json",
        base_payload,
        llm_caller,
    )
    feedback["L2"] = l2_data

    if l2_err:
        errors.append({"node": "reflector", "error": l2_err})

    if not l2_pass:
        print("  ✗ L2 failed (section coherence)")
        feedback["correction_brief"] = {
            "level": "L2",
            "issues": l2_data.get("issues", {}),
            "instruction": "Fix section argument arcs (claim -> evidence -> synthesis).",
        }

        Path("artifacts/soa").mkdir(parents=True, exist_ok=True)
        with open("artifacts/soa/reflector_feedback.json", "w", encoding="utf-8") as f:
            json.dump(feedback, f, indent=2)

        return {
            "reflector_feedback": feedback,
            "reflector_passed_level": 1,
            "reflector_rewrite_attempts": int(state.get("reflector_rewrite_attempts", 0)) + 1,
            "pipeline_stage": "reflector_l2_failed",
            "errors": errors,
        }

    # Level 3: Paragraph-level factual grounding
    l3_pass, l3_data, l3_err = _call_level(
        "L3",
        "prompts/reflector_L3.system.txt",
        "artifacts/soa/reflector_L3.json",
        base_payload,
        llm_caller,
    )
    feedback["L3"] = l3_data

    if l3_err:
        errors.append({"node": "reflector", "error": l3_err})

    if not l3_pass:
        print("  ✗ L3 failed (paragraph grounding)")
        feedback["correction_brief"] = {
            "level": "L3",
            "issues": l3_data.get("issues", []),
            "instruction": "Fix unsupported factual claims and align citations to extracted IDs.",
        }

        Path("artifacts/soa").mkdir(parents=True, exist_ok=True)
        with open("artifacts/soa/reflector_feedback.json", "w", encoding="utf-8") as f:
            json.dump(feedback, f, indent=2)

        return {
            "reflector_feedback": feedback,
            "reflector_passed_level": 2,
            "reflector_rewrite_attempts": int(state.get("reflector_rewrite_attempts", 0)) + 1,
            "pipeline_stage": "reflector_l3_failed",
            "errors": errors,
        }

    print("  ✓ Reflector passed all levels (L1-L3)")
    feedback["correction_brief"] = {
        "level": "none",
        "issues": [],
        "instruction": "No reflector correction needed.",
    }

    Path("artifacts/soa").mkdir(parents=True, exist_ok=True)
    with open("artifacts/soa/reflector_feedback.json", "w", encoding="utf-8") as f:
        json.dump(feedback, f, indent=2)

    return {
        "reflector_feedback": feedback,
        "reflector_passed_level": 3,
        "pipeline_stage": "reflector_complete",
        "errors": errors,
    }
