# JSON Schema Documentation

This document describes all JSON structures used in the SOA-CLI pipeline.

## 1. Reader Agent Output

**File**: `artifacts/reader/PX.json`

```json
{
  "paper_id": "PX",
  "title": "Paper Title",
  "year": "2023",
  "sections": {
    "abstract": "Full abstract text...",
    "introduction": "Introduction text...",
    "related_work": "Related work text...",
    "methodology": "Methodology text...",
    "results": "Results text...",
    "discussion": "Discussion text...",
    "limitations": "Limitations text...",
    "conclusion": "Conclusion text..."
  }
}
```

## 2. Extractor Agent Output

**File**: `artifacts/extracted/PX.json`

```json
{
  "paper_id": "PX",
  "research_problem": "Emergency vehicle relocation under uncertainty",
  "application_domain": "Emergency Medical Services",
  "decision_variables": "Binary ambulance assignment to stations",
  "prediction_component": {
    "used": true,
    "method": "LSTM neural network",
    "target": "demand by region",
    "temporal_resolution": "hourly"
  },
  "optimization_component": {
    "used": true,
    "method": "Mixed-Integer Programming",
    "objective_function": "minimize expected response time",
    "constraints": "capacity, coverage, workload balance"
  },
  "learning_paradigm": "supervised",
  "data": {
    "type": "real",
    "source": "City EMS dispatch records",
    "city_or_region": "Toronto, Canada"
  },
  "evaluation_metrics": [
    "response time",
    "coverage percentage",
    "utilization rate"
  ],
  "baselines_compared": [
    "static deployment",
    "myopic relocation"
  ],
  "assumptions": [
    "perfect compliance with relocation",
    "deterministic travel times",
    "no relocation cost"
  ],
  "limitations_explicit": [
    "offline evaluation only",
    "single city dataset",
    "no real-time deployment"
  ],
  "claimed_contributions": [
    "first to combine LSTM prediction with MIP optimization",
    "achieves 12% improvement over myopic baseline"
  ]
}
```

## 3. Critic Agent Output

**File**: `artifacts/critic/PX.json`

```json
{
  "paper_id": "PX",
  "methodological_strength": "medium",
  "evaluation_quality": "acceptable",
  "scalability_addressed": false,
  "real_time_applicability": false,
  "main_weaknesses": [
    "no real-time deployment validation",
    "limited to single city",
    "ignores relocation costs"
  ],
  "potential_biases": [
    "dataset from only high-density urban area"
  ],
  "reproducibility_score": 0.65
}
```

## 4. Vector Database Metadata

**File**: `vector_db/meta.json`

```json
[
  {"paper_id": "P01"},
  {"paper_id": "P02"},
  {"paper_id": "P03"}
]
```

## 5. Pre-Clustering Output (Mathematical)

**File**: `artifacts/clusters/preclusters.json`

```json
{
  "C0": ["P01", "P12", "P19", "P27"],
  "C1": ["P03", "P14", "P22"],
  "C2": ["P05", "P08", "P11", "P31"],
  "C3": ["P02", "P07", "P15"],
  "C4": ["P04", "P09", "P20"],
  "C5": ["P06", "P10", "P13"]
}
```

## 6. Cluster Agent Output (Interpreted)

**File**: `artifacts/clusters/clusters.json`

```json
[
  {
    "cluster_id": "C0",
    "cluster_name": "Predict-then-Optimize Approaches",
    "methodological_theme": "Sequential pipeline: demand prediction followed by optimization",
    "papers": ["P01", "P12", "P19", "P27"],
    "shared_characteristics": [
      "two-stage methodology",
      "supervised learning for prediction",
      "MIP or heuristic optimization"
    ],
    "common_assumptions": [
      "prediction errors do not affect optimization",
      "static demand patterns within prediction window"
    ],
    "common_limitations": [
      "no joint learning",
      "prediction-optimization gap not addressed"
    ]
  },
  {
    "cluster_id": "C1",
    "cluster_name": "End-to-End Reinforcement Learning",
    "methodological_theme": "Direct policy learning without explicit prediction or optimization",
    "papers": ["P03", "P14", "P22"],
    "shared_characteristics": [
      "reinforcement learning paradigm",
      "no separate prediction module",
      "learns decision policy directly"
    ],
    "common_assumptions": [
      "sufficient training data available",
      "reward function adequately captures objectives"
    ],
    "common_limitations": [
      "black-box decision making",
      "requires extensive training data"
    ]
  }
]
```

## 7. Synthesis Agent Output

**File**: `artifacts/synthesis/synthesis.json`

```json
[
  {
    "theme": "Predict-then-Optimize vs End-to-End Learning",
    "dominant_approaches": [
      "Sequential predict-then-optimize (18 papers)",
      "End-to-end reinforcement learning (7 papers)",
      "Direct optimization without prediction (6 papers)"
    ],
    "strengths_observed": [
      "Predict-then-optimize: interpretable, modular, well-established theory",
      "End-to-end RL: no modeling assumptions, can capture complex dynamics",
      "Direct optimization: computationally efficient, guaranteed optimality under assumptions"
    ],
    "systematic_weaknesses": [
      "Predict-then-optimize: prediction errors propagate to optimization",
      "End-to-end RL: requires extensive data, lacks interpretability",
      "Direct optimization: unrealistic assumptions about demand knowledge"
    ],
    "conflicting_findings": [
      "Papers P12 and P19 report contradictory results on LSTM effectiveness",
      "Real-time feasibility claimed by P03 but questioned by P14's computational analysis"
    ],
    "research_gaps": [
      "Joint learning of prediction and optimization objectives",
      "Real-time deployment validation beyond simulation",
      "Incorporation of relocation costs and operational constraints",
      "Cross-city generalization and transfer learning"
    ],
    "why_gap_exists": "Most studies optimize for offline metrics without considering online deployment constraints, and evaluation remains simulation-based due to practical barriers in real-world testing"
  },
  {
    "theme": "Data and Evaluation Practices",
    "dominant_approaches": [
      "Single-city real data (25 papers)",
      "Synthetic data only (8 papers)",
      "Multi-city comparison (10 papers)"
    ],
    "strengths_observed": [
      "Real data: captures actual operational patterns",
      "Synthetic: enables controlled experiments",
      "Multi-city: tests generalization"
    ],
    "systematic_weaknesses": [
      "Lack of standardized benchmarks",
      "No common baseline implementations",
      "Inconsistent evaluation metrics across studies"
    ],
    "conflicting_findings": [],
    "research_gaps": [
      "Standardized benchmark datasets",
      "Common baseline implementations for fair comparison",
      "Real-time deployment case studies"
    ],
    "why_gap_exists": "No community-wide coordination on benchmarking, and institutional barriers prevent sharing of real EMS data"
  }
]
```

## 8. Hallucination Detection Report

**File**: `artifacts/soa/hallucination_report.json`

```json
{
  "severity": "medium",
  "total_claims": 142,
  "violations": {
    "ungrounded": 3,
    "bad_citations": 2,
    "new_concepts": 1,
    "contradictions": 0
  },
  "total_violations": 6,
  "details": [
    {
      "claim": "Most studies demonstrate real-time feasibility.",
      "issue": "no supporting papers",
      "detector": "claim_evidence_grounding"
    },
    {
      "claim": "Papers P12 and P14 show superior performance.",
      "issue": "citation does not support claim",
      "citations": ["P12", "P14"],
      "detector": "citation_verification"
    },
    {
      "issue": "new concepts not in corpus",
      "concepts": ["transformer", "attention-mechanism"],
      "detector": "fact_coverage"
    }
  ]
}
```

## 9. Repair Input (Internal)

**File**: `artifacts/soa/_repair_input.json`

```json
{
  "original_sentence": "Most studies demonstrate real-time feasibility.",
  "issue_type": "ungrounded",
  "allowed_evidence": {
    "paper_id": ["P03", "P07"],
    "facts": [
      "evaluated via simulation",
      "offline experiments only",
      "computational time under 5 seconds",
      "no real-time deployment tested"
    ]
  }
}
```

## 10. Repair Failure Report

**File**: `artifacts/soa/repair_failure.json`

```json
{
  "status": "failed",
  "iterations": 3,
  "unrepairable_claims": [
    {
      "sentence": "Recent advances in deep learning have revolutionized the field.",
      "reason": "no supporting evidence in corpus"
    },
    {
      "sentence": "All methods achieve near-optimal performance.",
      "reason": "contradicts critic assessments for multiple papers"
    }
  ]
}
```

## Data Flow

```
PDFs
  ↓
[Reader] → reader/*.json
  ↓
[Extractor] → extracted/*.json
  ↓
[Critic] → critic/*.json
  ↓
[Vectorize] → vector_db/index.faiss + meta.json
  ↓
[Similarity Cluster] → clusters/preclusters.json
  ↓
[Cluster Agent] → clusters/clusters.json
  ↓
[Synthesis Agent] → synthesis/synthesis.json
  ↓
[Writer Agent] → soa/state_of_the_art.tex
  ↓
[Hallucination Check] → soa/hallucination_report.json
  ↓
[Repair Loop] → soa/state_of_the_art_repaired.tex (if needed) + state_of_the_art.tex
```

## Key Principles

1. **Every JSON is an artifact** - Can be inspected, validated, reused
2. **Paper IDs are preserved** - Full traceability from source to output
3. **No information loss** - Each stage adds structure, doesn't remove data
4. **Deterministic outputs** - Same input → same output (with fixed seeds)

## Validation

All JSON files should validate against their schemas. Common validation checks:

- `paper_id` field present and consistent
- Arrays are not empty where required
- Enum values match specifications (e.g., "low/medium/high")
- Citations reference valid paper IDs

## Extending the Schema

To add new fields:

1. Update the relevant agent's system prompt
2. Document the field here
3. Update downstream consumers (if any)
4. Test with a small subset first

**Critical**: Never remove existing fields - only add. Maintains backward compatibility.
