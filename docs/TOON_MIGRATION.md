# TOON Format Migration Guide

## Overview

The SOA-CLI project has been fully migrated from JSON to **TOON (Token-Oriented Object Notation)** format for all intermediate artifacts. This migration provides **30-60% token reduction** when feeding data to LLM agents, significantly reducing API costs.

## What is TOON?

TOON is a highly compressed data format designed specifically for LLM consumption. It excels at representing uniform structured data (arrays of objects) in a tabular format that drastically reduces token count compared to JSON.

### Example Comparison

**JSON (verbose):**
```json
[
  {"id": 1, "name": "Alice", "role": "admin"},
  {"id": 2, "name": "Bob", "role": "user"}
]
```

**TOON (compact):**
```
users[2]{id,name,role}:
  1,Alice,admin
  2,Bob,user
```

**Token savings:** ~60% fewer tokens!

## Benefits for SOA-CLI

SOA-CLI is a perfect fit for TOON because:

1. ✅ **Uniform structured data**: Reader/Extractor/Critic outputs are arrays of structured objects
2. ✅ **Repeated LLM consumption**: Artifacts are fed to multiple downstream agents
3. ✅ **Large datasets**: Processing 40+ papers generates significant artifact data
4. ✅ **High repetition**: Same field names repeated across many papers in JSON

**Expected savings:** 30-60% reduction in token usage = Lower API costs

## Migrated Files

All artifact files now use `.toon` extension instead of `.json`:

### Artifacts
- `artifacts/reader/{paper_id}.toon` - Reader node outputs
- `artifacts/extracted/{paper_id}.toon` - Extractor node outputs
- `artifacts/critic/{paper_id}.toon` - Critic node assessments
- `artifacts/synthesis/synthesis.toon` - Synthesis results
- `artifacts/clusters/clusters.toon` - Cluster assignments
- `artifacts/initial_state.toon` - Pipeline initial state
- `artifacts/final_state.toon` - Pipeline final state

### Metadata
- `vector_db/meta.toon` - FAISS vector database metadata
- `THEMATIC_CONTRACT.toon` - Global thematic contract

### Reports
- `artifacts/soa/hallucination_report.toon` - Hallucination detection results
- `artifacts/soa/repair_failure.toon` - Repair failure reports

## Backward Compatibility

The migration includes **full backward compatibility**:

- ✅ All TOON loading functions check for `.toon` first, then fallback to `.json`
- ✅ Legacy `.json` artifacts can still be loaded
- ✅ Mixed `.toon` and `.json` artifacts work together
- ✅ Lossless conversion: TOON↔JSON round-trip is perfect

## Implementation Details

### New Utility Module

`src/toon_utils.py` provides wrapper functions:

```python
from src.toon_utils import dump_toon, load_toon, loads

# Save data as TOON
dump_toon(data, "output.toon")

# Load TOON file (with JSON fallback)
data = load_toon("output.toon")

# Parse TOON string from LLM output
data = loads(toon_string)

# Estimate token savings
savings = estimate_token_savings(json_data)
print(f"Will save {savings['percent_saved']}% tokens")
```

**Library:** Uses `simple-toon` (PyPI package `toon_parser` module)

### Updated Modules

All modules now support TOON:

1. **src/graph/nodes.py** - All node artifact operations
2. **soa_cli.py** - Artifact loading and state serialization
3. **src/theme_builder.py** - Thematic contract operations
4. **src/vectorize.py** - Vector database metadata
5. **src/similarity_cluster.py** - Cluster assignments
6. **src/hallucination_detector.py** - Detection reports
7. **src/repair_loop.py** - Repair failure reports

## Installation

Install the TOON library:

```bash
pip install -r requirements.txt
# or
pip install simple-toon>=0.2.0
```

## Testing the Migration

### Clean Start

Remove old JSON artifacts and regenerate with TOON:

```bash
# Clear all artifacts
python soa_cli.py --clean

# Run pipeline (will create .toon files)
python soa_cli.py
```

### Verify TOON Generation

Check that `.toon` files are created:

```bash
ls artifacts/reader/
ls artifacts/extracted/
ls artifacts/critic/
```

You should see `.toon` files instead of `.json` files.

### Check Token Savings

Compare file sizes:

```bash
# If you have old .json files
du -sh artifacts/reader/*.json  # Old
du -sh artifacts/reader/*.toon  # New (should be ~40-60% smaller)
```

## Troubleshooting

### TOON Library Not Installed

If `simple-toon` is not installed, the utility module automatically falls back to JSON:

```
[!] Warning: simple-toon library not found, falling back to JSON
[!] Install with: pip install simple-toon
```

### Loading Old Artifacts

Old `.json` artifacts are automatically detected and loaded:

```python
# This automatically tries .toon first, then .json
data = load_toon("artifacts/reader/paper1.toon")
```

### Converting JSON to TOON

To convert existing JSON artifacts to TOON:

```python
from src.toon_utils import load_toon, dump_toon
import json

# Load JSON
with open("old.json") as f:
    data = json.load(f)

# Save as TOON
dump_toon(data, "new.toon")
```

## Performance Impact

Expected improvements:

- **Token reduction:** 30-60% fewer tokens sent to LLMs
- **API cost reduction:** Proportional to token savings
- **File size reduction:** ~40-60% smaller artifact files
- **Parsing speed:** Similar to JSON (both are fast)
- **Accuracy:** Slightly better (73.9% vs 69.7% in benchmarks)

## When NOT to Use TOON

TOON is NOT recommended for:

- ❌ Small datasets (<100 records) - overhead not worth it
- ❌ Irregular/sparse data - JSON is better for this
- ❌ Human-editable config files - JSON is more familiar
- ❌ LLM output generation - LLMs trained on JSON, use JSON there

**Note:** User input files (`theme_input.json`) remain JSON for human editability.

## Resources

- **PyPI Package:** https://pypi.org/project/simple-toon/
- **Module:** `toon_parser` (from `simple-toon` package)
- **Original TOON Docs:** https://toontools.vercel.app/docs
- **Comprehensive Guide:** https://ramuklawjju.medium.com/toon-from-zero-to-actually-using-it-42933ffc56de

## Migration Checklist

- [x] Install `simple-toon` library
- [x] Create `src/toon_utils.py` wrapper module
- [x] Update `src/graph/nodes.py` (all nodes)
- [x] Update `soa_cli.py` (artifact loading + state)
- [x] Update `src/theme_builder.py`
- [x] Update `src/vectorize.py`
- [x] Update `src/similarity_cluster.py`
- [x] Update `src/hallucination_detector.py`
- [x] Update `src/repair_loop.py`
- [x] Test full pipeline run
- [x] Measure actual token savings (50%+ for uniform arrays)
- [x] Update documentation

## Summary

The TOON migration is **complete** and **backward compatible**. All artifacts now use the more efficient TOON format, providing significant token savings without breaking existing functionality. The migration is transparent to users - the pipeline works exactly as before, just more efficiently.
