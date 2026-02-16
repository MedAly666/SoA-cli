# Project Structure

This document describes the organized structure of SOA-CLI following the reorganization for clarity and professionalism.

## Directory Layout

```
soa-cli/
│
├── soa_cli.py              ⭐ MAIN ENTRY POINT
│   └── Orchestrates entire 7-stage pipeline
│
├── README.md               Complete project overview
├── requirements.txt        Python dependencies
├── setup.sh               Automated setup script
├── PROJECT_STRUCTURE.md   This file
│
├── src/                   📦 Core Python modules
│   ├── __init__.py        Package initialization (clean exports)
│   ├── theme_builder.py   Stage 0: Thematic contract builder
│   ├── vectorize.py       Vector DB & embeddings (FAISS)
│   ├── similarity_cluster.py  Mathematical clustering
│   ├── hallucination_detector.py  4-layer verification
│   └── repair_loop.py     Iterative repair system
│
├── scripts/               🛠 Utility scripts
│   └── check.py           Pre-flight verification
│
├── docs/                  📚 Complete documentation
│   ├── QUICKREF.md        ⭐ Quick reference guide
│   ├── THEMATIC_PRIMING.md ⭐ Thematic system guide
│   ├── USAGE.md           Detailed usage instructions
│   ├── SCHEMAS.md         Data structure reference
│   ├── IMPLEMENTATION.md  Implementation status
│   ├── main.md            Architecture specification
│   ├── orchestrator.md    Pipeline design
│   ├── prompts.md         Agent constraints
│   ├── vectordb.md        Clustering system
│   ├── hallucination.md   Verification system
│   └── rewriter.md        Repair system
│
├── prompts/               🤖 Agent system prompts
│   ├── theme_builder.system.txt
│   ├── reader.system.txt
│   ├── extractor.system.txt
│   ├── critic.system.txt
│   ├── cluster.system.txt
│   ├── synthesis.system.txt
│   ├── writer.system.txt
│   ├── repair.system.txt
│   └── verifier.system.txt
│
├── papers/                📄 Input PDFs (user-provided)
│   └── *.pdf
│
├── artifacts/             💾 All pipeline outputs
│   ├── reader/            Parsed paper structures
│   ├── extracted/         Extracted facts per paper
│   ├── critic/            Quality assessments
│   ├── clusters/          Similarity clusters
│   ├── synthesis/         Cross-paper synthesis
│   └── soa/               ⭐ Final State of the Art
│       └── state_of_the_art_final.tex
│
└── vector_db/             🔍 FAISS index (generated)
    └── index.faiss
```

## Entry Points

### Primary Entry Point

```bash
python soa_cli.py
```

Runs the complete 7-stage pipeline from thematic contract to final LaTeX output.

### Module Entry Points

Each core module can be run independently:

```bash
# Thematic contract management
python -m src.theme_builder template
python -m src.theme_builder build
python -m src.theme_builder show

# Vector DB
python -m src.vectorize artifacts/extracted/

# Clustering
python -m src.similarity_cluster 6

# Verification
python -m src.hallucination_detector artifacts/soa/state_of_the_art.tex artifacts/extracted/

# Repair
python -m src.repair_loop artifacts/soa/state_of_the_art.tex artifacts/extracted/
```

### Utility Scripts

```bash
# Pre-flight verification
python scripts/check.py
```

## Import Structure

### From Main Entry Point (soa_cli.py)

```python
from src.theme_builder import build_thematic_contract, load_thematic_contract
from src.vectorize import build_vector_db, load_vector_db
from src.similarity_cluster import run_similarity_clustering
from src.hallucination_detector import detect_hallucinations
from src.repair_loop import repair_pipeline
```

### Within src/ Modules (Relative Imports)

```python
# In src/hallucination_detector.py
from .vectorize import load_vector_db, get_embedder

# In src/repair_loop.py
from .hallucination_detector import detect_hallucinations
```

### Clean Package Exports (src/__init__.py)

The `src/__init__.py` file exports all major functions, allowing clean imports:

```python
from src import (
    build_thematic_contract,
    build_vector_db,
    run_similarity_clustering,
    detect_hallucinations,
    repair_pipeline
)
```

## Generated Files & Directories

The following are created during pipeline execution:

- `THEMATIC_CONTRACT.json` - Global research scope (Stage 0)
- `theme_input.json` - User input for contract builder
- `artifacts/` - All stage outputs
- `vector_db/` - FAISS index and metadata
- `__pycache__/` - Python bytecode (git ignored)

## Design Principles

### 1. Clear Entry Point
- **Problem**: Root folder had 20+ files, unclear where to start
- **Solution**: Single obvious entry point `soa_cli.py` at root

### 2. Code Organization
- **Problem**: Core modules mixed with scripts and docs
- **Solution**: 
  - `src/` for core functionality (proper Python package)
  - `scripts/` for utilities
  - `docs/` for documentation

### 3. Professional Structure
- **Problem**: Looked like prototype, not production code
- **Solution**: Industry-standard directory layout
  - Source code in `src/`
  - Documentation in `docs/`
  - Clean root with only essentials

### 4. Import Clarity
- **Problem**: Absolute imports made refactoring difficult
- **Solution**: 
  - Package structure with `__init__.py`
  - Relative imports within package
  - Clean exports for external use

## File Count by Directory

```
Root:           4 files (soa_cli.py, README.md, requirements.txt, setup.sh)
src/:           6 files (5 modules + __init__.py)
scripts/:       1 file  (check.py)
docs/:          12 files (comprehensive documentation)
prompts/:       9 files (agent system prompts)
papers/:        User-provided PDFs
artifacts/:     Generated outputs
```

**Total source files in root**: 4 (down from 20+)

## Migration Notes

### What Changed

1. **Renamed**: `orchestrator.py` → `soa_cli.py`
2. **Moved**: 5 core modules → `src/`
3. **Moved**: All documentation → `docs/`
4. **Moved**: Utility scripts → `scripts/`
5. **Created**: `src/__init__.py` for package structure
6. **Updated**: All imports to use new structure
7. **Updated**: All documentation to reference new paths

### What Stayed the Same

- Pipeline architecture (7 stages)
- Agent system prompts
- Data schemas
- Artifact structure
- Functional behavior

### Backward Compatibility

Old command style still works via module invocation:

```bash
# Old style (still works)
python -m src.theme_builder build

# Direct invocation (works if in PYTHONPATH)
python src/theme_builder.py build
```

## Quick Start Commands

### First Time Setup
```bash
./setup.sh
python scripts/check.py
```

### Define Research Scope
```bash
python -m src.theme_builder template
nano theme_input.json
python -m src.theme_builder build
```

### Run Pipeline
```bash
cp /path/to/papers/*.pdf papers/
python soa_cli.py
```

### Output Location
```bash
cat artifacts/soa/state_of_the_art_final.tex
```

---

## Summary

This structure provides:
- ✅ Clear entry point (`soa_cli.py`)
- ✅ Professional organization (src/, docs/, scripts/)
- ✅ Clean root directory (4 files vs 20+)
- ✅ Proper Python package structure
- ✅ Easy navigation and maintenance
- ✅ Industry-standard layout

**Before**: Cluttered prototype with unclear entry point  
**After**: Production-ready structure with obvious organization
