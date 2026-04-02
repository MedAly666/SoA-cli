# Quick Reference

## Run Pipeline

```bash
python soa_cli.py --papers papers --max-repair 3 --format markdown
```

## Clean Legacy Artifacts

```bash
python soa_cli.py --clean
```

## Force Cluster Count

```bash
python soa_cli.py --clusters 6 --format markdown
```

## Common Environment Setup

```bash
export LLM_PROVIDER=qwen
export LLM_TIMEOUT=180
export MAX_WORKERS=10
```

Optional DB persistence:

```bash
export SOA_DB_DSN='postgresql://user:pass@host:5432/dbname'
export SOA_STORAGE_MODE=db
```

## Outputs

- `db_outputs/soa/state_of_the_art.md`
- `STATE_OF_THE_ART.md`
