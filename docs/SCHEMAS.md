# Schemas

## LangGraph State

Defined in `src/graph/state.py` (`SOAState`).

### Key Inputs

- `thematic_contract`
- `paper_paths`
- `max_repair_iterations`

### Aggregating Maps

- `reader_outputs`
- `extracted_facts`
- `critic_assessments`
- `errors` (append behavior)

### Core Single-Value Fields

- `raw_clusters`, `clusters`, `synthesis`, `soa_draft`
- `citation_map`, `db_run_id`, `citation_graph`
- `verification_results`, `verification_passed`, `hallucination_report`
- `repair_iteration`
- timing fields: `pipeline_start_time`, `stage_durations`, `total_wall_clock_seconds`

## PostgreSQL Schema

Defined in `db/schema.sql`.

Main tables:
- `runs`
- `papers`, `paper_aliases`
- `paper_embeddings`
- `citations`, `sections`, `claims`, `claim_evidence`
- `artifacts`
- `metrics`
- `benchmark_thresholds`

Notes:
- `vector` extension is required (`pgvector`).
- persistence is optional and controlled by `SOA_DB_DSN`.
