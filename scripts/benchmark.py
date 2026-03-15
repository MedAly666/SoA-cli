#!/usr/bin/env python3
"""Benchmark suite for SoA-CLI.

This script can:
1) Run the full pipeline (optional)
2) Compute benchmark metrics from artifacts
3) Compare SoA-CLI against surveyed systems
4) Save JSON report and print formatted console table
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.graph.nodes import call_llm  # noqa: E402

try:
    import tiktoken  # type: ignore[import-not-found]
except Exception:
    tiktoken = None

try:
    from rouge_score import rouge_scorer  # type: ignore[import-not-found]
except Exception:
    rouge_scorer = None


BASELINES: dict[str, dict[str, Any]] = {
    "ARISE": {
        "tri_judge_score": 92.48,
        "coherence": None,
        "citation_f1": None,
        "time_seconds": 12600,
        "cost_usd": 15.0,
        "sam_normalized": None,
        "rouge_l": None,
        "hsr": None,
        "hallucination_rate": None,
        "agents": 22,
        "paper": "arXiv:2511.17689",
    },
    "SciSage": {
        "tri_judge_score": None,
        "coherence": 80.37,
        "citation_f1": None,
        "time_seconds": None,
        "cost_usd": None,
        "sam_normalized": None,
        "rouge_l": None,
        "hsr": None,
        "hallucination_rate": None,
        "agents": 6,
        "paper": "arXiv:2506.12689",
    },
    "LiRA": {
        "tri_judge_score": None,
        "coherence": None,
        "citation_f1": 0.76,
        "time_seconds": None,
        "cost_usd": None,
        "sam_normalized": None,
        "rouge_l": None,
        "hsr": None,
        "hallucination_rate": None,
        "agents": 4,
        "paper": "arXiv:2510.05138",
    },
    "SurveyG": {
        "tri_judge_score": None,
        "coherence": 80.37,
        "citation_f1": None,
        "time_seconds": 1980,
        "cost_usd": 1.6,
        "sam_normalized": None,
        "rouge_l": None,
        "hsr": None,
        "hallucination_rate": None,
        "agents": 2,
        "paper": "arXiv:2510.07733",
    },
    "AutoSurvey": {
        "tri_judge_score": 82.46,
        "coherence": None,
        "citation_f1": 0.63,
        "time_seconds": 41,
        "cost_usd": 0.075,
        "sam_normalized": None,
        "rouge_l": None,
        "hsr": None,
        "hallucination_rate": None,
        "agents": 1,
        "paper": "arXiv:2406.10252",
    },
    "SurveyForge": {
        "tri_judge_score": None,
        "coherence": None,
        "citation_f1": None,
        "time_seconds": None,
        "cost_usd": 0.50,
        "sam_normalized": None,
        "rouge_l": None,
        "hsr": None,
        "hallucination_rate": None,
        "agents": 1,
        "paper": "arXiv:2503.04629",
    },
    "SoA-CLI": {},
}

JUDGE_PERSONAS = [
    "You are a strict academic reviewer with expertise in systematic literature review methodology.",
    "You are an expert in AI and computer science research evaluation, focused on technical depth and accuracy.",
    "You are a writing quality specialist focused on academic clarity, argument structure, and citation rigor.",
]

TRI_DIMS = [
    "Scope",
    "Literature",
    "Analysis",
    "Originality",
    "Organization",
    "Presentation",
    "References",
]

BENCHMARK_DIR = ROOT / "artifacts" / "benchmark"
PROMPT_DIR = BENCHMARK_DIR / "prompts"
_HSR_EMBED_MODEL: Any | None = None

DEFAULT_THRESHOLDS: dict[str, float] = {
    "tri_judge_score": 85.0,
    "citation_f1": 0.70,
    "hsr": 0.90,
    "min_checked_claims": 5.0,
}


def warn(msg: str) -> None:
    print(f"[benchmark][warn] {msg}")


def load_thresholds() -> dict[str, float]:
    thresholds = dict(DEFAULT_THRESHOLDS)
    path = BENCHMARK_DIR / "thresholds.json"
    if not path.exists():
        return thresholds
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        warn(f"Failed to parse thresholds file {path}: {exc}")
        return thresholds
    if not isinstance(obj, dict):
        return thresholds
    for key in ("tri_judge_score", "citation_f1", "hsr", "min_checked_claims"):
        val = safe_float(obj.get(key))
        if val is not None:
            thresholds[key] = val
    return thresholds


def load_json(path: Path) -> Optional[dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        warn(f"Failed to parse JSON: {path} ({exc})")
        return None


def safe_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_prompt_file(name: str, system_prompt: str) -> Path:
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    path = PROMPT_DIR / name
    path.write_text(system_prompt.strip() + "\n", encoding="utf-8")
    return path


def run_pipeline_subprocess(command: list[str]) -> dict[str, Any]:
    started = time.time()
    proc = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True)
    ended = time.time()
    return {
        "command": command,
        "return_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "started_at": started,
        "ended_at": ended,
        "wall_clock_seconds": ended - started,
    }


def get_final_tex_path() -> Optional[Path]:
    # First try canonical high-priority paths in deterministic order.
    direct_candidates = [
        ROOT / "db_outputs" / "soa" / "state_of_the_art_final.tex",
        ROOT / "db_outputs" / "soa" / "state_of_the_art.tex",
        ROOT / "artifacts" / "soa" / "state_of_the_art_final.tex",
        ROOT / "artifacts" / "soa" / "state_of_the_art.tex",
        ROOT / "state_of_the_art.tex",
        ROOT / "artifacts" / "state_of_the_art.tex",
        ROOT / "artifacts" / "state_of_the_art_final.tex",
    ]
    for p in direct_candidates:
        if p.exists() and p.is_file():
            return p

    # Fallback: search common folders for any .tex output.
    fallback: list[Path] = []
    for pattern in (
        ROOT.glob("state_of_the_art*.tex"),
        (ROOT / "db_outputs" / "soa").glob("*.tex"),
        (ROOT / "artifacts").glob("*.tex"),
        (ROOT / "artifacts" / "soa").glob("*.tex"),
    ):
        for p in pattern:
            if p.is_file():
                fallback.append(p)

    if fallback:
        # Prefer likely final SoA outputs, then newest mtime.
        def _rank(path: Path) -> tuple[int, float]:
            name = path.name.lower()
            score = 0
            if "state_of_the_art" in name:
                score += 3
            if "final" in name:
                score += 2
            if "repaired" in name:
                score += 1
            try:
                mtime = path.stat().st_mtime
            except Exception:
                mtime = 0.0
            return (score, mtime)

        fallback.sort(key=_rank, reverse=True)
        return fallback[0]

    return None


def read_text(path: Optional[Path]) -> str:
    if path is None or not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        warn(f"Failed reading text {path}: {exc}")
        return ""


def parse_llm_json(raw: str) -> Optional[dict[str, Any]]:
    try:
        return json.loads(raw)
    except Exception as exc:
        warn(f"LLM JSON parse failed: {exc}")
        return None


def safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def llm_eval_json(system_prompt: str, payload: dict[str, Any], out_name: str) -> Optional[dict[str, Any]]:
    prompt_path = ensure_prompt_file(out_name.replace(".json", ".system.txt"), system_prompt)
    out_path = BENCHMARK_DIR / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        raw = call_llm(str(prompt_path), payload, str(out_path), max_retries=2)
    except Exception as exc:
        warn(f"LLM call failed for {out_name}: {exc}")
        return None
    parsed = parse_llm_json(raw)
    if parsed is None:
        return None
    return parsed


def metric_tri_judge(final_tex: str) -> tuple[Optional[float], dict[str, Optional[float]], dict[str, Any]]:
    if not final_tex.strip():
        warn("M1 skipped: final .tex missing/empty")
        return None, {d: None for d in TRI_DIMS}, {}

    rubric = (
        "Evaluate the document strictly using these 7 dimensions (0-100):\n"
        "1) Scope: alignment with declared topic, no out-of-scope drift.\n"
        "2) Literature: coverage breadth, recency balance, key missing lines.\n"
        "3) Analysis: depth of comparison, contradictions, trade-off synthesis.\n"
        "4) Originality: synthesis beyond paper-by-paper summary.\n"
        "5) Organization: logical section flow and transitions.\n"
        "6) Presentation: clarity, precision, academic writing quality.\n"
        "7) References: citation integrity, consistency, no invented keys.\n\n"
        "Calibration guidance:\n"
        "- 90-100: excellent, publication-ready for that dimension.\n"
        "- 80-89: strong with minor weaknesses.\n"
        "- 70-79: acceptable but clear issues remain.\n"
        "- 50-69: weak, substantial revision needed.\n"
        "- 0-49: critically flawed.\n\n"
        "Penalty policy (apply strictly):\n"
        "- If claims are mostly descriptive with little synthesis, Analysis <= 65.\n"
        "- If references appear fabricated or inconsistent, References <= 40.\n"
        "- If structure drifts from topic/core questions, Scope <= 60.\n"
        "- If writing is coherent but repetitive, cap Presentation at 75.\n"
    )

    persona_focus = [
        "Focus extra weight on methodological rigor, systematic review completeness, and defensible evidence boundaries.",
        "Focus extra weight on technical depth, factual precision, and whether comparative claims are scientifically justified.",
        "Focus extra weight on narrative clarity, argument arc continuity, and citation-supported academic prose quality.",
    ]

    output_contract = (
        "Return ONLY valid JSON. No markdown, no prose, no code fences.\n"
        "Output exactly these numeric keys: Scope, Literature, Analysis, Originality, Organization, Presentation, References.\n"
        "Example: {\"Scope\":85,\"Literature\":72,\"Analysis\":68,\"Originality\":75,\"Organization\":80,\"Presentation\":77,\"References\":90}"
    )

    payload = {"document": final_tex}
    raw: dict[str, Any] = {}
    values: list[float] = []
    per_dim_collect: dict[str, list[float]] = {d: [] for d in TRI_DIMS}

    for idx, persona in enumerate(JUDGE_PERSONAS, start=1):
        prompt = "\n\n".join([
            persona,
            rubric,
            persona_focus[idx - 1],
            output_contract,
        ])
        parsed = llm_eval_json(prompt, payload, f"tri_judge_{idx}.json")
        judge_key = f"judge_{idx}"
        raw[judge_key] = parsed
        if not isinstance(parsed, dict):
            continue

        for dim in TRI_DIMS:
            score = safe_float(parsed.get(dim))
            if score is None:
                continue
            values.append(score)
            per_dim_collect[dim].append(score)

    per_dimension_mean: dict[str, Optional[float]] = {}
    for dim, arr in per_dim_collect.items():
        per_dimension_mean[dim] = round(statistics.mean(arr), 2) if arr else None

    tri = round(statistics.mean(values), 2) if values else None
    safe_write_json(BENCHMARK_DIR / "tri_judge_raw.json", raw)
    return tri, per_dimension_mean, raw


def metric_coherence(final_tex: str) -> Optional[float]:
    if not final_tex.strip():
        warn("M2 skipped: final .tex missing/empty")
        return None

    prompt = (
        "You are evaluating the structural coherence of an academic survey section. "
        "Score the document from 0 to 100 on a single coherence dimension defined as: "
        "logical progression between sections, smooth transitions, no redundancy, "
        "consistent argument arc from introduction to conclusion. "
        "Return ONLY a JSON object: {\"coherence\": <score>, \"rationale\": \"<50 words>\"}"
    )
    parsed = llm_eval_json(prompt, {"document": final_tex}, "coherence_raw.json")
    if not isinstance(parsed, dict):
        return None
    score = safe_float(parsed.get("coherence"))
    if score is None:
        warn("M2 parse failure: coherence missing/non-numeric")
        return None
    return round(score, 2)


def metric_sam(final_tex: str) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    if not final_tex.strip():
        warn("M3 skipped: final .tex missing/empty")
        return None, None, None, None

    prompts = {
        "SAM_R": (
            "Score the reference quality of this academic survey from 1 to 5. "
            "Criteria: citations are real, relevant, correctly attributed, and complete. "
            "Return ONLY: {\"SAM_R\": <1-5>, \"rationale\": \"<30 words>\"}"
        ),
        "SAM_O": (
            "Score the outline/structure quality of this academic survey from 1 to 5. "
            "Criteria: sections are logically ordered, headings are descriptive, depth is appropriate. "
            "Return ONLY: {\"SAM_O\": <1-5>, \"rationale\": \"<30 words>\"}"
        ),
        "SAM_C": (
            "Score the content quality of this academic survey from 1 to 5. "
            "Criteria: factual accuracy, depth of analysis, synthesis quality, no hallucinations. "
            "Return ONLY: {\"SAM_C\": <1-5>, \"rationale\": \"<30 words>\"}"
        ),
    }

    vals: dict[str, Optional[float]] = {"SAM_R": None, "SAM_O": None, "SAM_C": None}
    payload = {"document": final_tex}

    for key, prompt in prompts.items():
        parsed = llm_eval_json(prompt, payload, f"{key.lower()}_raw.json")
        if not isinstance(parsed, dict):
            continue
        score = safe_float(parsed.get(key))
        if score is None:
            warn(f"M3 parse failure for {key}")
            continue
        vals[key] = score

    normalized_vals = [((v - 1.0) / 4.0) * 100.0 for v in vals.values() if v is not None]
    sam_normalized = round(statistics.mean(normalized_vals), 2) if normalized_vals else None

    return vals["SAM_R"], vals["SAM_O"], vals["SAM_C"], sam_normalized


def extract_citation_keys(tex_text: str) -> set[str]:
    keys: set[str] = set()
    # LaTeX citations: \cite{..}, \citep{..}, \citet{..}, etc.
    for match in re.findall(r"\\cite[a-zA-Z]*\{([^}]*)\}", tex_text):
        for k in match.split(","):
            kk = k.strip()
            if kk:
                keys.add(kk)

    # Pandoc markdown citations: [@id; @id2]
    for match in re.findall(r"\[@([^\]]+)\]", tex_text):
        for k in re.split(r";|,", match):
            kk = k.strip().lstrip("@")
            if kk:
                keys.add(kk)

    # Inline markdown citations: @id
    for k in re.findall(r"(?<!\w)@([A-Za-z0-9_:\-.]+)", tex_text):
        kk = k.strip()
        if kk:
            keys.add(kk)

    # Avoid counting cross-reference labels as bibliography citations.
    keys = {k for k in keys if not k.startswith(("fig:", "tbl:", "tab:", "eq:", "sec:"))}
    return keys


def normalize_key(key: str) -> str:
    """Normalize IDs for robust matching between citations and extracted filenames."""
    return re.sub(r"[^A-Za-z0-9]+", "", key).lower()


def resolve_valid_keys(extracted_dir: Path) -> set[str]:
    valid: set[str] = set()
    if not extracted_dir.exists():
        return valid
    for p in extracted_dir.glob("*.json"):
        valid.add(p.stem)
    return valid


def _align_citations_to_valid(cited_keys: set[str], valid_keys: set[str]) -> set[str]:
    if not cited_keys or not valid_keys:
        return set()

    valid_by_norm = {normalize_key(v): v for v in valid_keys}
    aligned: set[str] = set()

    for ck in cited_keys:
        if ck in valid_keys:
            aligned.add(ck)
            continue
        mapped = valid_by_norm.get(normalize_key(ck))
        if mapped:
            aligned.add(mapped)

    return aligned


def metric_citation_f1(final_tex: str, extracted_dir: Path) -> tuple[Optional[float], Optional[float], Optional[float], dict[str, list[str]]]:
    if not final_tex.strip():
        warn("M4 skipped: final .tex missing/empty")
        return None, None, None, {
            "cited_keys": [],
            "valid_keys": [],
            "invented_keys": [],
            "missed_keys": [],
        }

    cited_keys = extract_citation_keys(final_tex)
    valid_keys = resolve_valid_keys(extracted_dir)
    aligned_cited = _align_citations_to_valid(cited_keys, valid_keys)

    inter = aligned_cited & valid_keys
    precision = (len(inter) / len(cited_keys)) if cited_keys else 0.0
    recall = (len(inter) / len(valid_keys)) if valid_keys else 0.0
    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    details = {
        "cited_keys": sorted(cited_keys),
        "aligned_cited_keys": sorted(aligned_cited),
        "valid_keys": sorted(valid_keys),
        "invented_keys": sorted(cited_keys - aligned_cited),
        "missed_keys": sorted(valid_keys - aligned_cited),
    }

    return round(precision, 4), round(recall, 4), round(f1, 4), details


def flatten_strings(value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, str):
        if value.strip():
            out.append(value.strip())
        return out
    if isinstance(value, list):
        for item in value:
            out.extend(flatten_strings(item))
        return out
    if isinstance(value, dict):
        for vv in value.values():
            out.extend(flatten_strings(vv))
    return out


def strip_latex_to_text(tex_text: str) -> str:
    # Remove environments
    text = re.sub(r"\\begin\{[^}]+\}.*?\\end\{[^}]+\}", " ", tex_text, flags=re.DOTALL)
    # Remove commands with braces (simple approximation requested)
    text = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?\{[^{}]*\}", " ", text)
    # Remove standalone commands
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)
    # Remove braces and collapse whitespace
    text = text.replace("{", " ").replace("}", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_reference_text(extracted_dir: Path) -> str:
    chunks: list[str] = []
    if not extracted_dir.exists():
        return ""

    for fp in sorted(extracted_dir.glob("*.json")):
        obj = load_json(fp)
        if not isinstance(obj, dict):
            continue
        chunks.extend(flatten_strings(obj.get("key_findings", [])))
        chunks.extend(flatten_strings(obj.get("claims", [])))

    return "\n".join(chunks)


def metric_rouge_l(final_tex: str, extracted_dir: Path) -> Optional[float]:
    if rouge_scorer is None:
        warn("M5 skipped: rouge-score not installed")
        return None

    hypothesis = strip_latex_to_text(final_tex)
    reference = build_reference_text(extracted_dir)
    if not hypothesis or not reference:
        warn("M5 skipped: hypothesis/reference text missing")
        return None

    try:
        scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
        score = scorer.score(reference, hypothesis)["rougeL"].fmeasure
        return round(float(score), 4)
    except Exception as exc:
        warn(f"M5 failed: {exc}")
        return None


def extract_headings(tex_text: str) -> list[str]:
    headings: list[str] = []
    # LaTeX headings
    headings.extend(re.findall(r"\\section\*?\{([^}]*)\}", tex_text))
    headings.extend(re.findall(r"\\subsection\*?\{([^}]*)\}", tex_text))
    # Markdown headings fallback (markdown-first pipeline)
    headings.extend(re.findall(r"(?m)^#{1,3}\s+(.+)$", tex_text))
    return [h.strip() for h in headings if h.strip()]


def maybe_embedding_match(phrase: str, headings: list[str], threshold: float = 0.6) -> bool:
    global _HSR_EMBED_MODEL
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except Exception:
        return False

    try:
        if _HSR_EMBED_MODEL is None:
            _HSR_EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = _HSR_EMBED_MODEL.encode([phrase] + headings, convert_to_numpy=True)
        p = embeddings[0]
        hs = embeddings[1:]
        p_norm = np.linalg.norm(p)
        if p_norm == 0 or hs.size == 0:
            return False
        hs_norm = np.linalg.norm(hs, axis=1)
        hs_norm[hs_norm == 0] = 1.0
        sims = (hs @ p) / (hs_norm * p_norm)
        return bool((sims > threshold).any())
    except Exception:
        return False


def metric_hsr(contract: Optional[dict[str, Any]], final_tex: str) -> Optional[float]:
    if not isinstance(contract, dict):
        warn("M6 skipped: THEMATIC_CONTRACT.json missing/invalid")
        return None
    if not final_tex.strip():
        warn("M6 skipped: final .tex missing/empty")
        return None

    targets = []
    for k in ("themes", "core_questions", "key_concepts"):
        targets.extend(flatten_strings(contract.get(k, [])))

    # Deduplicate while preserving order
    seen: set[str] = set()
    uniq_targets: list[str] = []
    for t in targets:
        tl = t.lower().strip()
        if tl and tl not in seen:
            seen.add(tl)
            uniq_targets.append(t)

    if not uniq_targets:
        warn("M6 skipped: no target phrases in thematic contract")
        return None

    headings = extract_headings(final_tex)
    if not headings:
        warn("M6 skipped: no section/subsection headings found")
        return None

    headings_l = [h.lower() for h in headings]
    matched = 0

    # Lazy model loading only if needed.
    for phrase in uniq_targets:
        p = phrase.lower()
        sub = any(p in h for h in headings_l)
        if sub:
            matched += 1
            continue
        if maybe_embedding_match(phrase, headings, threshold=0.6):
            matched += 1

    return round(matched / len(uniq_targets), 4)


def metric_hallucination(report_path: Path) -> tuple[Optional[float], Optional[bool], Optional[int], Optional[int]]:
    report = load_json(report_path)
    if not isinstance(report, dict):
        warn("M7 skipped: hallucination report missing/invalid")
        return None, None, None, None

    violations_obj = report.get("violations", [])
    details = report.get("details", [])
    if isinstance(details, list):
        total_violations = len(details)
    elif isinstance(violations_obj, list):
        total_violations = len(violations_obj)
    elif isinstance(violations_obj, dict):
        total_violations = int(report.get("total_violations", 0) or 0)
    else:
        total_violations = int(report.get("total_violations", 0) or 0)
    try:
        total_claims_checked = int(report.get("total_claims_checked", 0) or 0)
    except Exception:
        total_claims_checked = 0
    try:
        total_claims_all = int(report.get("total_claims", 0) or 0)
    except Exception:
        total_claims_all = 0

    # Prefer checked claims when sample size is meaningful; otherwise fall back.
    min_checked_claims = int(report.get("min_checked_claims_required", 5) or 5)
    total_claims = total_claims_checked if total_claims_checked >= min_checked_claims else total_claims_all
    try:
        total_claims_num = int(total_claims)
    except Exception:
        total_claims_num = 1
    if total_claims_num <= 0:
        warn("M7 low-confidence: verifier checked too few claims; hallucination rate suppressed")
        return None, bool(report.get("repair_triggered", False)), total_violations, total_claims_checked

    rate = total_violations / total_claims_num
    return round(rate, 4), bool(report.get("repair_triggered", False)), total_violations, total_claims_num


def estimate_tokens_and_cost(final_tex_path: Optional[Path], extracted_dir: Path) -> tuple[Optional[int], Optional[float]]:
    chunks: list[str] = []

    if final_tex_path and final_tex_path.exists():
        chunks.append(read_text(final_tex_path))

    if extracted_dir.exists():
        for fp in sorted(extracted_dir.glob("*.json")):
            chunks.append(read_text(fp))

    if not chunks:
        return None, None

    merged = "\n".join(chunks)

    if tiktoken is None:
        warn("tiktoken not installed; token count uses char/4 approximation")
        token_count = max(1, len(merged) // 4)
    else:
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            token_count = len(enc.encode(merged))
        except Exception as exc:
            warn(f"Tokenization failed; fallback char/4 ({exc})")
            token_count = max(1, len(merged) // 4)

    cost = (token_count / 1000.0) * 0.001
    return int(token_count), round(cost, 6)


def latest_mtime(paths: list[Path]) -> Optional[float]:
    mtimes: list[float] = []
    for p in paths:
        if p.exists():
            try:
                mtimes.append(p.stat().st_mtime)
            except Exception:
                continue
    return max(mtimes) if mtimes else None


def gather_stage_timings(pipeline_start: Optional[float] = None) -> dict[str, Any]:
    stage_files: list[tuple[str, list[Path]]] = [
        ("theme_builder", [ROOT / "THEMATIC_CONTRACT.json"]),
        ("reader", list((ROOT / "artifacts" / "reader").glob("*.json"))),
        ("extractor", list((ROOT / "artifacts" / "extracted").glob("*.json"))),
        ("critic", list((ROOT / "artifacts" / "critic").glob("*.json"))),
        ("vectorize", [ROOT / "artifacts" / "vector_db" / "index.faiss", ROOT / "artifacts" / "vector_db" / "meta.json"]),
        ("build_graph", [ROOT / "artifacts" / "clusters" / "citation_graph.json"]),
        ("cluster", [ROOT / "artifacts" / "clusters" / "clusters.json", ROOT / "artifacts" / "clusters" / "preclusters.json"]),
        ("synthesis", [ROOT / "artifacts" / "synthesis" / "synthesis.json"]),
        ("writer", [ROOT / "artifacts" / "soa" / "state_of_the_art_draft.md", ROOT / "artifacts" / "soa" / "state_of_the_art.md", ROOT / "artifacts" / "soa" / "state_of_the_art.tex"]),
        ("reflector", [ROOT / "artifacts" / "soa" / "reflector_feedback.json"]),
        ("rubric_evaluator", [ROOT / "artifacts" / "soa" / "rubric_report.json"]),
        ("verifier", [ROOT / "artifacts" / "soa" / "hallucination_report.json"]),
        ("repair", [ROOT / "artifacts" / "soa" / "state_of_the_art_repaired.tex"]),
        ("final_output", [ROOT / "state_of_the_art.tex", ROOT / "artifacts" / "soa" / "state_of_the_art_final.tex", ROOT / "artifacts" / "soa" / "state_of_the_art.tex"]),
    ]

    stage_end_epoch: dict[str, Optional[float]] = {}
    for stage, files in stage_files:
        stage_end_epoch[stage] = latest_mtime(files)

    stage_seconds: dict[str, Optional[float]] = {}
    prev_t = pipeline_start
    for stage, _ in stage_files:
        t = stage_end_epoch.get(stage)
        if t is None:
            stage_seconds[stage] = None
            continue
        if prev_t is None:
            stage_seconds[stage] = None
            prev_t = t
            continue
        stage_seconds[stage] = round(max(0.0, t - prev_t), 3)
        prev_t = t

    return {
        "pipeline_start_epoch": pipeline_start,
        "stage_end_epoch": stage_end_epoch,
        "stage_seconds": stage_seconds,
    }


def fmt(v: Optional[float], digits: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v:.{digits}f}"


def fmt_time(seconds: Optional[float]) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds:.0f}sec"
    if seconds < 3600:
        return f"{seconds/60:.1f}min"
    return f"{seconds/3600:.2f}h"


def print_console_report(
    results: dict[str, Any],
    topic: str,
    paper_count: int,
    wall_clock_seconds: Optional[float],
) -> None:
    print("=" * 65)
    print("  SoA-CLI BENCHMARK — Comparison Against Survey Systems")
    print("=" * 65)
    print()
    print("QUALITY METRICS (higher is better)")
    print("System        Tri-judge   Coherence   Citation F1   ROUGE-L   HSR")
    print("------------------------------------------------------------------")
    print("ARISE           92.48        —            —            —        —")
    print("SciSage           —         80.37         —            —        —")
    print("LiRA              —          —           0.76          —        —")
    print("SurveyG           —         80.37         —            —        —")
    print("AutoSurvey      82.46        —           0.63          —        —")
    print("SurveyForge       —          —            —            —        —")
    print(
        f"SoA-CLI        {fmt(results.get('tri_judge_score')):>6}      "
        f"{fmt(results.get('coherence_score')):>6}       "
        f"{fmt(results.get('citation_f1'), 4):>6}       "
        f"{fmt(results.get('rouge_l'), 4):>6}  "
        f"{fmt(results.get('hsr'), 4):>6}"
    )
    print()
    print("EFFICIENCY METRICS")
    print("System        Time          Cost      Agents   Hallucination rate")
    print("------------------------------------------------------------------")
    print("ARISE           3.5h        $10-20      22         —")
    print("SurveyG        33min         $1.6        2         —")
    print("AutoSurvey      41sec        $0.08       1         —")
    print("SurveyForge      —           <$0.50      1         —")
    est_cost = results.get("estimated_cost_usd")
    est_cost_str = f"${est_cost:.4f}" if isinstance(est_cost, (int, float)) else "—"
    print(
        f"SoA-CLI        {fmt_time(wall_clock_seconds):>8}      {est_cost_str:>8}      "
        f"11        {fmt(results.get('hallucination_rate'), 4)}"
    )
    print()
    print("SAM METRICS (1-5 scale, higher is better)")
    print("System        SAM-R    SAM-O    SAM-C")
    print("--------------------------------------")
    print("AutoSurvey      —        —        —    (reported but values not in survey)")
    print("SurveyForge     —        —        —    (reported but values not in survey)")
    print(
        f"SoA-CLI        {fmt(results.get('sam_r')):>5}  {fmt(results.get('sam_o')):>5}   {fmt(results.get('sam_c')):>5}"
    )
    print()
    threshold_results = results.get("threshold_results") or {}
    failed = results.get("failed_threshold_metrics") or []
    if isinstance(threshold_results, dict) and threshold_results:
        print("THRESHOLD GATES")
        for metric_name, payload in threshold_results.items():
            if not isinstance(payload, dict):
                continue
            required = payload.get("required")
            actual = payload.get("actual")
            passed = bool(payload.get("passed"))
            print(
                f"- {metric_name}: actual={actual} required={required} -> "
                f"{'PASS' if passed else 'FAIL'}"
            )
        print(f"Overall threshold status: {'PASS' if not failed else 'FAIL'}")
        print()

    print(f"Note: \"—\" means the system did not report this metric.")
    print(f"      SoA-CLI results on {paper_count} papers, topic: {topic}.")
    print()
    print("=" * 65)
    print("  BENCHMARK SAVED TO: artifacts/benchmark/benchmark_report.json")
    print("=" * 65)


def evaluate_all_metrics(
    wall_clock_seconds: Optional[float],
    pipeline_started_at: Optional[float] = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str], str, int]:
    missing: list[str] = []

    contract = load_json(ROOT / "THEMATIC_CONTRACT.json")
    topic = "unknown"
    if isinstance(contract, dict):
        topic = str(contract.get("topic") or contract.get("global_theme") or "unknown")
    else:
        missing.append("THEMATIC_CONTRACT.json")

    extracted_dir = ROOT / "artifacts" / "extracted"
    paper_count = len(list(extracted_dir.glob("*.json"))) if extracted_dir.exists() else 0
    if paper_count == 0:
        missing.append("artifacts/extracted/*.json")

    final_tex_path = get_final_tex_path()
    final_tex = read_text(final_tex_path)
    if not final_tex:
        missing.append("state_of_the_art.tex or artifacts/soa/state_of_the_art_final.tex")

    tri_judge_score, tri_per_dim, tri_raw = metric_tri_judge(final_tex)
    coherence_score = metric_coherence(final_tex)
    sam_r, sam_o, sam_c, sam_normalized = metric_sam(final_tex)
    citation_precision, citation_recall, citation_f1, citation_details = metric_citation_f1(final_tex, extracted_dir)
    rouge_l = metric_rouge_l(final_tex, extracted_dir)
    hsr = metric_hsr(contract if isinstance(contract, dict) else None, final_tex)

    hallu_report_path = ROOT / "db_outputs" / "soa" / "hallucination_report.json"
    if not hallu_report_path.exists():
        hallu_report_path = ROOT / "artifacts" / "soa" / "hallucination_report.json"

    hallucination_rate, repair_triggered, total_violations, total_claims = metric_hallucination(hallu_report_path)
    if hallucination_rate is None:
        missing.append("db_outputs/soa/hallucination_report.json or artifacts/soa/hallucination_report.json")

    token_count, estimated_cost = estimate_tokens_and_cost(final_tex_path, extracted_dir)
    if token_count is None:
        missing.append("token proxy inputs (final tex + extracted json)")

    stage_timing = gather_stage_timings(pipeline_started_at)
    thresholds = load_thresholds()

    threshold_results = {
        "tri_judge_score": {
            "required": thresholds["tri_judge_score"],
            "actual": tri_judge_score,
            "passed": tri_judge_score is not None and tri_judge_score >= thresholds["tri_judge_score"],
        },
        "citation_f1": {
            "required": thresholds["citation_f1"],
            "actual": citation_f1,
            "passed": citation_f1 is not None and citation_f1 >= thresholds["citation_f1"],
        },
        "hsr": {
            "required": thresholds["hsr"],
            "actual": hsr,
            "passed": hsr is not None and hsr >= thresholds["hsr"],
        },
        "min_checked_claims": {
            "required": int(thresholds["min_checked_claims"]),
            "actual": total_claims,
            "passed": (total_claims or 0) >= int(thresholds["min_checked_claims"]),
        },
    }

    failed_metrics = [k for k, v in threshold_results.items() if not bool(v.get("passed"))]
    benchmark_passed = len(failed_metrics) == 0

    soa_results: dict[str, Any] = {
        "tri_judge_score": tri_judge_score,
        "tri_judge_per_dimension": tri_per_dim,
        "coherence_score": coherence_score,
        "sam_r": sam_r,
        "sam_o": sam_o,
        "sam_c": sam_c,
        "sam_normalized": sam_normalized,
        "citation_precision": citation_precision,
        "citation_recall": citation_recall,
        "citation_f1": citation_f1,
        "rouge_l": rouge_l,
        "hsr": hsr,
        "hallucination_rate": hallucination_rate,
        "repair_triggered": repair_triggered,
        "total_violations": total_violations,
        "total_claims_checked": total_claims,
        "wall_clock_seconds": wall_clock_seconds,
        "estimated_cost_usd": estimated_cost,
        "token_count_proxy": token_count,
        "agent_count": 11,
        "stage_timing": stage_timing,
        "thresholds": thresholds,
        "threshold_results": threshold_results,
        "failed_threshold_metrics": failed_metrics,
        "benchmark_passed": benchmark_passed,
        "cost_note": "Estimated using cl100k_base tokenization and fixed rate $0.001 per 1K tokens.",
        "hallucination_note": "SoA-CLI exclusive advantage metric.",
    }

    return soa_results, tri_raw, citation_details, missing, topic, paper_count


def build_report(
    soa_results: dict[str, Any],
    tri_raw: dict[str, Any],
    citation_details: dict[str, Any],
    topic: str,
    paper_count: int,
    missing: list[str],
) -> dict[str, Any]:
    baselines = deepcopy(BASELINES)
    baselines["SoA-CLI"] = {
        "tri_judge_score": soa_results.get("tri_judge_score"),
        "coherence": soa_results.get("coherence_score"),
        "citation_f1": soa_results.get("citation_f1"),
        "time_seconds": soa_results.get("wall_clock_seconds"),
        "cost_usd": soa_results.get("estimated_cost_usd"),
        "sam_normalized": soa_results.get("sam_normalized"),
        "rouge_l": soa_results.get("rouge_l"),
        "hsr": soa_results.get("hsr"),
        "hallucination_rate": soa_results.get("hallucination_rate"),
        "agents": 11,
        "paper": "This work",
    }

    return {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
        "paper_count": paper_count,
        "soa_cli_results": soa_results,
        "baselines": baselines,
        "tri_judge_raw": tri_raw,
        "citation_details": citation_details,
        "missing_artifacts": sorted(set(missing)),
    }


def run_benchmark(run_pipeline: bool = True, pipeline_cmd: Optional[list[str]] = None) -> dict[str, Any]:
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)

    wall_clock = None
    pipeline_started = None

    if run_pipeline:
        cmd = pipeline_cmd or [sys.executable, "soa_cli.py"]
        print(f"[benchmark] Running pipeline: {' '.join(cmd)}")
        run_result = run_pipeline_subprocess(cmd)
        pipeline_started = run_result["started_at"]
        wall_clock = run_result["wall_clock_seconds"]
        (BENCHMARK_DIR / "pipeline_stdout.log").write_text(run_result["stdout"], encoding="utf-8")
        (BENCHMARK_DIR / "pipeline_stderr.log").write_text(run_result["stderr"], encoding="utf-8")
        if run_result["return_code"] != 0:
            warn(f"Pipeline exited with code {run_result['return_code']}. Metrics will still be attempted.")

    soa_results, tri_raw, citation_details, missing, topic, paper_count = evaluate_all_metrics(
        wall_clock_seconds=wall_clock,
        pipeline_started_at=pipeline_started,
    )

    report = build_report(soa_results, tri_raw, citation_details, topic, paper_count, missing)
    report_path = BENCHMARK_DIR / "benchmark_report.json"
    safe_write_json(report_path, report)

    print_console_report(
        results=soa_results,
        topic=topic,
        paper_count=paper_count,
        wall_clock_seconds=wall_clock,
    )

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="SoA-CLI benchmark runner")
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Skip pipeline execution and only evaluate existing artifacts.",
    )
    parser.add_argument(
        "--pipeline-cmd",
        nargs="+",
        default=None,
        help="Override pipeline command (default: python soa_cli.py)",
    )
    args = parser.parse_args()

    run_benchmark(run_pipeline=not args.skip_run, pipeline_cmd=args.pipeline_cmd)


if __name__ == "__main__":
    main()
