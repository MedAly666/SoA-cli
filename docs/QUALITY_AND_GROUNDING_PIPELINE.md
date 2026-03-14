# Quality and Grounding Pipeline

This document describes the new quality-control and grounding components added to SOA-CLI.

## Overview

The pipeline now includes three high-priority quality features:

1. `build_graph` (Citation Graph)
2. `reflector` (Hierarchical Reflector: L1/L2/L3)
3. `rubric_evaluator` (ARISE-style quality scoring)

These components improve factual grounding, structural quality, and targeted repair.

## Updated Pipeline Flow

```text
... -> vectorize -> build_graph -> cluster -> interpret_clusters -> synthesis -> writer -> reflector -> rubric_evaluator -> verifier -> repair
```

`reflector` uses conditional routing:
- If all levels pass (`reflector_passed_level == 3`), continue to `rubric_evaluator`.
- If not passed and rewrite attempts < 2, route back to `writer`.
- If rewrite attempts >= 2, force forward to `rubric_evaluator` to avoid infinite loops.

## 1) Citation Graph (`build_graph`)

### Purpose
Build a directed graph over extracted papers to ground cross-paper claims.

### Node/Edge Types
- Nodes: extracted paper IDs and metadata (`id`, `title`, `year`)
- Edges:
  - `citation`: explicit references from `references` / `cited_works`
  - `thematic`: cosine similarity edges (threshold > 0.65)

### Artifacts
- `artifacts/clusters/citation_graph.json`

### Prompt Integration
- `synthesis` receives `citation_graph_context` (top-k neighbors for seed papers)
- `writer` receives both `citation_graph` and `citation_graph_context`

## 2) Hierarchical Reflector (`reflector`)

### Purpose
Perform staged quality checks to avoid spending tokens on paragraph checks when outline-level quality is broken.

### Levels
- L1 (Outline): section/subsection alignment with thematic contract
- L2 (Section): argument arc per section (claim -> evidence -> synthesis)
- L3 (Paragraph): factual grounding and citation-key integrity

### Inputs
- Current LaTeX draft
- Thematic contract
- Extracted paper IDs

### Outputs
- `reflector_feedback` (includes per-level findings + correction brief)
- `reflector_passed_level` (0..3)
- `reflector_rewrite_attempts` incremented when rerouting to writer

### Artifact
- `artifacts/soa/reflector_feedback.json`

## 3) Rubric Evaluator (`rubric_evaluator`)

### Purpose
Score output quality across seven dimensions and provide failing dimensions for targeted repair.

### Dimensions (0-100)
- Scope
- Literature
- Analysis
- Originality
- Organization
- Presentation
- References

### Threshold
- Failing dimension: score < 70

### Outputs
- `rubric_scores: dict[str, float]`
- `rubric_failing: list[str]`

### Artifact
- `artifacts/soa/rubric_report.json`

Report format:
```json
{
  "scores": {
    "Scope": 81,
    "Literature": 75,
    "Analysis": 68,
    "Originality": 72,
    "Organization": 79,
    "Presentation": 77,
    "References": 64
  },
  "failing": ["Analysis", "References"],
  "threshold": 70.0
}
```

## Targeted Repair Behavior

`repair` now receives `rubric_failing` and is instructed to focus only on failing dimensions. This reduces unnecessary rewrites and preserves stable sections.

## New State Fields

Added to `SOAState`:
- `citation_graph`
- `rubric_scores`
- `rubric_failing`
- `reflector_feedback`
- `reflector_passed_level`
- `reflector_rewrite_attempts`

## Prompt Files Added

- `prompts/rubric_evaluator.system.txt`
- `prompts/reflector_L1.system.txt`
- `prompts/reflector_L2.system.txt`
- `prompts/reflector_L3.system.txt`

## Practical Debug Checklist

If quality still degrades:
1. Check `artifacts/soa/reflector_feedback.json` for specific structural failures.
2. Check `artifacts/soa/rubric_report.json` for low-scoring dimensions.
3. Check `artifacts/clusters/citation_graph.json` for sparse graph context.
4. Review `artifacts/soa/_writer_input.json` to confirm grounding context was injected.

## Recommended Workflow

1. Run pipeline.
2. Inspect reflector and rubric artifacts.
3. If repeated failures occur, tune prompts and rerun with `--clean`.
4. Use `--max-repair` only after improving grounding quality.
