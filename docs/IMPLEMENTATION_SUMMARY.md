# Implementation Summary

## What Is Implemented

- DB-first LangGraph pipeline with markdown final output.
- Parallel reader/extractor/critic stages.
- Citation map generation and canonical citation-key handling.
- Optional PostgreSQL persistence for runs/artifacts/metrics.
- Verification + repair loop with configurable max iterations.

## What Is Intentionally Skipped In Current Runtime

- LaTeX patching flow in `figures_generator` (skipped node behavior in DB markdown mode).
- Multi-format export in CLI (`--format` is markdown-only).

## What Exists But Is Not Primary Runtime Path

- Legacy artifact utilities and JSON-oriented helper functions.
- Paper fetcher helper functions in `soa_cli.py` and `src/paper_fetcher.py` (not currently exposed by CLI flags).
- Vector DB legacy modules retained for compatibility but clustering in current node path is in-memory fallback.
