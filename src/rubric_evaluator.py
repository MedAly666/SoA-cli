"""Rubric evaluator for multi-dimensional SoA quality scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


RubricCall = Callable[[str, dict[str, Any], str, int], str]


def run_rubric_evaluator(state: dict[str, Any], llm_caller: RubricCall | None = None) -> dict[str, Any]:
    """Evaluate SoA draft with 7-dimension rubric and update state fields.

    Args:
        state: Pipeline state dictionary.
        llm_caller: Existing call_llm helper (injected by caller).

    Returns:
        Partial state update dict.
    """
    print("\n[Node: Rubric Evaluator]")

    draft_path = Path("artifacts/soa/state_of_the_art.tex")
    if not draft_path.exists():
        fallback = state.get("soa_draft") or ""
        if not fallback:
            print("  ERROR: No SoA draft available for rubric evaluation")
            return {
                "rubric_scores": {},
                "rubric_failing": [],
                "pipeline_stage": "rubric_evaluator_failed",
                "errors": [
                    {
                        "node": "rubric_evaluator",
                        "error": "No SoA draft available for rubric evaluation",
                    }
                ],
            }
        draft_text = fallback
    else:
        draft_text = draft_path.read_text(encoding="utf-8", errors="ignore")

    if llm_caller is None:
        # Lazy import to avoid module cycles when used outside nodes.py
        from src.graph.nodes import call_llm as llm_caller  # type: ignore

    contract = state.get("thematic_contract", {})
    input_payload = {
        "thematic_contract": contract,
        "soa_draft": draft_text,
        "dimensions": [
            "Scope",
            "Literature",
            "Analysis",
            "Originality",
            "Organization",
            "Presentation",
            "References",
        ],
    }

    output_path = "artifacts/soa/rubric_report.json"

    try:
        raw = llm_caller(
            "prompts/rubric_evaluator.system.txt",
            input_payload,
            output_path,
            3,
        )

        parsed = json.loads(raw)
        expected_dims = [
            "Scope",
            "Literature",
            "Analysis",
            "Originality",
            "Organization",
            "Presentation",
            "References",
        ]

        scores: dict[str, float] = {}
        for dim in expected_dims:
            value = parsed.get(dim, 0)
            try:
                scores[dim] = float(value)
            except Exception:
                scores[dim] = 0.0

        threshold = 70.0
        failing = [dim for dim, score in scores.items() if score < threshold]

        # Save full rubric report for downstream readers.
        report = {
            "scores": scores,
            "failing": failing,
            "threshold": threshold,
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        print(f"  ✓ Rubric scored ({len(scores)} dimensions)")
        print(f"  → Failing dimensions (<70): {', '.join(failing) if failing else 'None'}")

        return {
            "rubric_scores": scores,
            "rubric_failing": failing,
            "pipeline_stage": "rubric_evaluator_complete",
            "errors": [],
        }

    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "rubric_scores": {},
            "rubric_failing": [],
            "pipeline_stage": "rubric_evaluator_failed",
            "errors": [
                {
                    "node": "rubric_evaluator",
                    "error": str(e),
                }
            ],
        }
