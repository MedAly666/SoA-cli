# SOA-CLI Docs

This documentation reflects the current codebase behavior as of April 2026.

## What This System Does

SOA-CLI generates a State of the Art survey from PDFs using a LangGraph pipeline.

Current runtime mode is DB-first:
- State flows in-memory through LangGraph.
- PostgreSQL persistence is optional and enabled only when `SOA_DB_DSN` is configured and reachable.
- Core pipeline execution does not require JSON artifact handoff between stages.
- Primary output is markdown: `db_outputs/soa/state_of_the_art.md`.

## Read First

- `docs/USAGE.md`: fastest way to run successfully.
- `docs/QUICKREF.md`: copy-paste commands.
- `docs/CONFIGURATION.md`: environment variables that actually affect runtime.

## Internals

- `docs/LANGGRAPH_GUIDE.md`: real node order, routing, and loop behavior.
- `docs/SCHEMAS.md`: LangGraph state schema and PostgreSQL schema.
- `docs/QUALITY_AND_GROUNDING_PIPELINE.md`: writer, reflector, rubric, verifier, repair.
- `docs/IMPLEMENTATION_SUMMARY.md`: what is implemented vs legacy/disabled.

## Specialized / Historical Notes

These pages are kept for context and migration history, but are explicitly aligned with current behavior:
- `docs/ARTIFACTS_GUIDE.md`
- `docs/PAPER_FETCHER_GUIDE.md`
- `docs/PROVIDER_SETUP.md`
- `docs/SEMANTIC_PDF_IMPLEMENTATION.md`
- `docs/MULTIMODAL_PDF_SOLUTION.md`
- `docs/THEMATIC_PRIMING.md`
- `docs/THEMATIC_IMPLEMENTATION.md`
- `docs/TOON_MIGRATION.md`
- `docs/VECTOR_DB_AND_CLEAN.md`
- `docs/hallucination.md`
- `docs/vectordb.md`
