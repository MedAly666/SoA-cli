# Data Format: JSON Only

## Overview

SOA-CLI uses **JSON format exclusively** for all intermediate artifacts.

## Why JSON?

JSON is the standard, universal format for structured data:

✅ **Universal compatibility** - Works with all tools and libraries  
✅ **Human readable** - Easy to inspect and debug  
✅ **No dependencies** - Built into Python standard library  
✅ **Battle-tested** - Industry-standard format

## File Format

All artifact files use **standard JSON** with `.json` extension:

```json
{
  "paper_id": "example",
  "title": "Paper Title",
  "authors": ["Author One", "Author Two"],
  "keywords": ["keyword1", "keyword2"],
  "abstract": "..."
}
```

## API Usage

```python
import json

# Write JSON
data = {"paper_id": "test", "title": "Example"}
with open("output.json", 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

# Read JSON
with open("output.json", 'r', encoding='utf-8') as f:
    data = json.load(f)
```

## Artifact Files

### Per-Paper Outputs
- `artifacts/reader/{paper_id}.json` - Reader node outputs
- `artifacts/extracted/{paper_id}.json` - Extractor node outputs
- `artifacts/critic/{paper_id}.json` - Critic node assessments

### Pipeline Outputs
- `artifacts/synthesis/synthesis.json` - Synthesis results
- `artifacts/clusters/clusters.json` - Cluster assignments
- `artifacts/states/initial_state.json` - Pipeline initial state
- `artifacts/states/final_state.json` - Pipeline final state

### Metadata
- `artifacts/vector_db/meta.json` - FAISS vector database metadata
- `THEMATIC_CONTRACT.json` - Global thematic contract

### Reports
- `artifacts/soa/hallucination_report.json` - Hallucination detection results
- `artifacts/soa/repair_failure.json` - Repair failure reports

## Implementation

Standard Python `json` module is used throughout:
- `json.dump()` / `json.dumps()` for serialization
- `json.load()` / `json.loads()` for deserialization
- `indent=2` for pretty-printing
- `ensure_ascii=False` for Unicode support

## Benefits

1. **Simplicity**: No custom parsers or libraries
2. **Reliability**: Well-tested standard library
3. **Debugging**: Files are human-readable
4. **Compatibility**: Works everywhere
5. **Maintenance**: Zero learning curve for new developers

