# Verifier / Hallucination Checks

The active verifier in `src/graph/nodes.py` is citation-integrity focused.

## What It Checks

- parses claim lines from markdown draft
- extracts citation IDs
- validates citation IDs against `state.citation_map`
- reports violations and sets `verification_passed`

## What It Produces

- `verification_results`
- `verification_passed`
- `hallucination_report`

Repair routing uses this output through `route_after_verification` in `src/graph/builder.py`.
