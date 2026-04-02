# LangGraph Guide

Graph builder: `src/graph/builder.py`

State schema: `src/graph/state.py`

## Node Order

1. `theme_builder`
2. `reader_map`
3. `extractor_map`
4. `critic_map`
5. `vectorize`
6. `build_graph`
7. `cluster`
8. `interpret_clusters`
9. `synthesis`
10. `writer`
11. `reflector`
12. `rubric_evaluator`
13. `verifier`
14. `repair` (loop)
15. `final_output`
16. `figures_generator`

## Conditional Routing

### After `reflector`

- If `reflector_passed_level >= 3` -> `rubric_evaluator`
- Else if `reflector_rewrite_attempts >= 2` -> `rubric_evaluator`
- Else -> back to `writer` (rewrite loop)

### After `verifier`

- If `verification_passed == true` -> `final_output`
- Else if `repair_iteration >= max_repair_iterations` -> `final_output`
- Else -> `repair` -> `verifier`

## Practical Internals

- Reader/extractor/critic run in parallel using `ThreadPoolExecutor` with `MAX_WORKERS`.
- Writer stores markdown to `db_outputs/soa/state_of_the_art.md`.
- `figures_generator` is intentionally skipped in markdown-only DB mode.
- Timing metrics are accumulated in state and optionally persisted to PostgreSQL.
