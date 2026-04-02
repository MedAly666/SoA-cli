# Configuration

This file lists runtime controls that are used by current code paths.

## Core Pipeline

- `LLM_PROVIDER`: one of `claude|gemini|qwen|gpt|glm`.
- `LLM_MODEL`: provider-specific model id.
- `LLM_TIMEOUT`: LLM call timeout seconds.
- `MAX_WORKERS`: parallelism for reader/extractor/critic map stages.
- `CLUSTER_COUNT`: set by `--clusters`; can be `auto` or integer.

## DB / Persistence

- `SOA_DB_DSN`: enables PostgreSQL persistence when reachable and `psycopg` is installed.
- `SOA_STORAGE_MODE`: keep `db` in current DB-first flow.
- `SOA_DB_AUTO_INIT`: when `true`, initializes DB schema from `db/schema.sql`.

## Theme Behavior

- `SOA_TOPIC`: optional topic context.
- `SOA_REQUIRE_THEMATIC_CONTRACT=true`: require `THEMATIC_CONTRACT.json`, otherwise fallback tries `theme_input.json` build.

## PDF Extraction

- `USE_SEMANTIC_PDF` (default true): use semantic parser when available.
- `INCLUDE_FIGURES_IN_TEXT`
- `INCLUDE_TABLES_IN_TEXT`
- `EXTRACT_PDF_IMAGES`
- `MAX_PDF_CHARS`

## Citation Style Helpers

- `CITATION_STYLE`: injected into writer/repair prompt handling.

## Paper Fetcher (helper module, not current CLI flag path)

- `PAPER_SOURCES`
- `PAPER_MAX_RESULTS`
- `PAPER_MIN_YEAR`
- `PAPER_MIN_CITATIONS`
- `PAPER_REQUIRE_WHITELIST`
