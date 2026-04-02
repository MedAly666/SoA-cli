# Quality And Grounding Pipeline

Current quality loop in code:

1. `writer` creates markdown draft with citation constraints.
2. `reflector` performs structural/citation-count gate and may force rewrite.
3. `rubric_evaluator` scores coverage/grounding/organization/clarity.
4. `verifier` checks citation-key validity against `citation_map` and computes violation report.
5. `repair` rewrites only when verifier route requests it.

## Important Implementation Detail

Current `reflector` and `rubric_evaluator` nodes are heuristic implementations in `src/graph/nodes.py` (not full external evaluator modules at runtime path).

## Verifier Behavior

- Extracts non-heading lines from markdown draft.
- Parses citation IDs.
- Flags invalid citation IDs not present in `citation_map`.
- Sets `verification_passed` when no violations and minimum checked claim count is satisfied.

## Repair Behavior

- Uses `prompts/repair.system.txt`.
- Re-validates output with acceptance gates.
- Writes updated markdown back to `db_outputs/soa/state_of_the_art.md`.
