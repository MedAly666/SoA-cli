# SOA-CLI Documentation

Welcome to the SOA-CLI documentation. This system uses LangGraph for production-grade orchestration of multi-agent State of the Art generation.

---

## 📚 Documentation Index

### Getting Started
- **[Quick Reference (QUICKREF.md)](QUICKREF.md)** - Essential commands and quick start
- **[Usage Guide (USAGE.md)](USAGE.md)** - Detailed usage instructions
- **[Configuration (CONFIGURATION.md)](CONFIGURATION.md)** - Environment variables and settings
- **[Provider Setup (PROVIDER_SETUP.md)](PROVIDER_SETUP.md)** - LLM provider configuration

### Architecture & Design
- **[LangGraph Architecture (LANGGRAPH_GUIDE.md)](LANGGRAPH_GUIDE.md)** - Complete architecture guide
- **[Implementation Summary (IMPLEMENTATION_SUMMARY.md)](IMPLEMENTATION_SUMMARY.md)** - Current implementation status
- **[Data Schemas (SCHEMAS.md)](SCHEMAS.md)** - JSON schema reference

### Core Systems
- **[Thematic Priming (THEMATIC_PRIMING.md)](THEMATIC_PRIMING.md)** - Thematic contract system
- **[Thematic Implementation (THEMATIC_IMPLEMENTATION.md)](THEMATIC_IMPLEMENTATION.md)** - Implementation details
- **[Paper Fetcher Guide (PAPER_FETCHER_GUIDE.md)](PAPER_FETCHER_GUIDE.md)** - PRISMA-compliant paper search
- **[Hallucination Detection (hallucination.md)](hallucination.md)** - Verification system
- **[Vector Database (vectordb.md)](vectordb.md)** - Clustering system

### Features & Enhancements
- **[Vector DB & Clean Command (VECTOR_DB_AND_CLEAN.md)](VECTOR_DB_AND_CLEAN.md)** - Vector DB location and clean command behavior
- **[Artifacts Guide (ARTIFACTS_GUIDE.md)](ARTIFACTS_GUIDE.md)** - Understanding generated artifacts
- **[Semantic PDF Implementation (SEMANTIC_PDF_IMPLEMENTATION.md)](SEMANTIC_PDF_IMPLEMENTATION.md)** - PDF parsing enhancements
- **[Multimodal PDF Solution (MULTIMODAL_PDF_SOLUTION.md)](MULTIMODAL_PDF_SOLUTION.md)** - Figure and table extraction

### Migration & Technical Notes
- **[TOON Migration (TOON_MIGRATION.md)](TOON_MIGRATION.md)** - Migration to JSON-based pipeline

---

## 🚀 Quick Start

```bash
# Setup (first time)
./setup.sh

# Activate environment
source .venv/bin/activate

# Define research scope
python -m src.theme_builder template
nano theme_input.json
python -m src.theme_builder build

# Add papers
cp /path/to/papers/*.pdf papers/

# Run pipeline
python3 soa_cli.py

# Output: STATE_OF_THE_ART.tex
```

---

## 🏗️ Architecture Overview

SOA-CLI uses **LangGraph** for fault-tolerant orchestration:

```
11 Nodes → 13 Edges → Verification Gate → Repair Loop (max 3 iterations)
```

**Key Features:**
- ✅ Automatic checkpointing (resume from any node)
- ✅ Type-safe state management (TypedDict)
- ✅ Explicit control flow (verification gates, loops)
- ✅ Better error handling (accumulates, doesn't crash)
- ✅ Parallel processing (Reader, Extractor, Critic)

**Pipeline Stages:**

1. **Theme Builder** - Creates global thematic contract
2. **Reader Map** (parallel) - Extracts text from PDFs
3. **Extractor Map** (parallel) - Extracts structured facts
4. **Critic Map** (parallel) - Evaluates methodology
5. **Vectorize** - Creates embeddings
6. **Cluster** - Similarity-based grouping
7. **Interpret Clusters** - LLM interpretation
8. **Synthesis** - Cross-paper synthesis
9. **Writer** - Generates LaTeX draft
10. **Verifier** - Checks for hallucinations
11. **Repair** (conditional, 0-3 times) - Fixes issues

---

## 📊 State Management

The pipeline state is a TypedDict with:

**Immutable Inputs:**
- `thematic_contract` - Global research scope
- `paper_paths` - List of PDF paths
- `max_repair_iterations` - Maximum repair attempts

**Aggregating Collections:**
- `reader_outputs` - Per-paper text extraction
- `extracted_facts` - Per-paper structured facts
- `critic_assessments` - Per-paper methodology evaluation

**Single Values:**
- `clusters` - Paper groupings
- `synthesis` - Cross-paper synthesis
- `soa_draft` - LaTeX State of the Art

**Verification:**
- `verification_results` - Hallucination violations
- `verification_passed` - Boolean gate
- `repair_iteration` - Current repair attempt

---

## 🔍 Key Concepts

### Thematic Priming
Every LLM call receives the **thematic contract** to maintain focus:
- Global research theme
- Core research questions
- Scope constraints
- Preferred methodologies

### Verification Gates
Conditional routing based on verification results:
- **Pass** → END (success!)
- **Max iterations reached** → END (give up)
- **Fail** → Repair node (try to fix)

### Repair Loop
Up to 3 iterations to fix hallucinated claims:
1. Identify violations
2. Generate repair suggestions
3. Rewrite problematic sentences
4. Re-verify

### Error Accumulation
Errors don't crash the pipeline:
- Each node catches exceptions
- Errors stored in state
- Pipeline continues
- Final report shows all errors

---

## 🛠️ Tools

- **`python3 soa_cli.py`** - Main pipeline
- **`python3 test_langgraph.py`** - Validation tests
- **`python3 visualize_graph.py`** - Graph visualization
- **`python -m src.theme_builder`** - Thematic contract tools

---

## 📈 Performance

For **10 papers** on Gemini 2.0 Flash:
- Theme Builder: ~30s
- Reader/Extractor/Critic (parallel): ~7 min total
- Clustering: ~7s
- Synthesis: ~45s
- Writer: ~1 min
- Verifier: ~30s
- **Total: ~10-15 minutes** (without repairs)

---

## 🐛 Troubleshooting

### Import Errors
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### No Papers Found
```bash
ls papers/*.pdf  # Verify PDFs exist
python3 soa_cli.py --papers /path/to/pdfs  # Custom directory
```

### Verification Failures
```bash
# Check verification results
cat artifacts/states/final_state.json | jq '.verification_results'

# Increase repair iterations
python3 soa_cli.py --max-repair 5
```

### Resume Interrupted Run
```bash
python3 soa_cli.py --resume --thread-id my-session
```

---

## 📖 Further Reading

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [State Management Concepts](https://langchain-ai.github.io/langgraph/concepts/low_level/#state)
- [Checkpointing Guide](https://langchain-ai.github.io/langgraph/concepts/persistence/)

---

*Documentation updated: February 18, 2026*  
*SOA-CLI Version: LangGraph-based (Production)*
