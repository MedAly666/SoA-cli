# SOA-CLI: Production-Grade Multi-Agent State of the Art Generator

A CLI-based multi-agent system for generating academically rigorous State of the Art sections from research papers. Built on the principles of **traceability**, **fact-grounding**, **hallucination prevention**, and **thematic priming**.

---

## 🚀 Quick Start

```bash
# 1. Setup (installs PyMuPDF for PDF processing)
./setup.sh

# 2. Activate virtual environment (required for all commands)
source .venv/bin/activate
# OR use the convenience script:
# source activate.sh

# 3. Define your research scope (REQUIRED)
python -m src.theme_builder template
nano theme_input.json
python -m src.theme_builder build

# 4. Add your papers (PDFs)
cp /path/to/papers/*.pdf papers/

# 5. Run pipeline (automatically extracts text from PDFs)
python soa_cli.py

# Output: artifacts/soa/state_of_the_art_final.tex
```

**Time**: 25-40 minutes for 43 papers

**Features**:
- ✅ Automatic PDF text extraction (PyMuPDF)
- ✅ Smart truncation (~15-20 pages per paper, focuses on core content)
- ✅ Thematic priming for focused extraction
- ✅ No hallucinations (4-layer verification)
- ✅ Full traceability (paper IDs tracked)
- ✅ Timeout protection (30k character limit per paper)

---

## 📁 Project Structure

```
soa-cli/
├── soa_cli.py              # ⭐ MAIN ENTRY POINT
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── setup.sh                # Setup script
├──── src/                    # Core modules
│   ├── theme_builder.py    # Thematic contract (Stage 0)
│   ├── vectorize.py        # Vector database & embeddings
│   ├── similarity_cluster.py
│   ├── hallucination_detector.py
│   └── repair_loop.py
├── scripts/                # Utility scripts
│   └── check.py            # Pre-flight verification
├── docs/                   # Complete documentation
│   ├── QUICKREF.md         # ⭐ Quick reference
│   ├── THEMATIC_PRIMING.md # ⭐ Thematic guide
│   ├── USAGE.md            # Detailed usage
│   ├── SCHEMAS.md          # Data structures
│   └── ...                 # Architecture specs
├── prompts/                # Agent system prompts
├── papers/                 # Your PDFs go here
└── artifacts/              # All outputs
    ├── extracted/
    ├── clusters/
    ├── synthesis/
    └── soa/                # ⭐ Final output here
```

---
## 🔧 Installation

**Prerequisites**:
- Python 3.8+
- Qwen CLI installed and configured
- Research papers in PDF format

**Quick setup**:

```bash
# Automated setup (creates .venv virtual environment)
./setup.sh

# Activate the virtual environment
source .venv/bin/activate

# OR manual setup:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p papers artifacts
```

**Note**: Always activate the virtual environment before running the pipeline:
```bash
source .venv/bin/activate
# OR use the convenience script:
source activate.sh
```

To deactivate when done:
```bash
deactivate
```

## 📖 Usage

### Step 1: Define Your Research Scope (REQUIRED)

Before running the pipeline, you must define your thematic scope:

```bash
# Create template
python -m src.theme_builder template

# Edit with your research focus
vim theme_input.json

# Build thematic contract
python -m src.theme_builder build
```

This creates `THEMATIC_CONTRACT.json` - the **single source of truth** that guides all agents.

**Why this matters**: Without thematic priming, agents extract everything and lose focus. With it, you get 30-50% faster processing and a laser-focused SoA.

See [docs/THEMATIC_PRIMING.md](docs/THEMATIC_PRIMING.md) for detailed guide.

### Step 2: Run Complete Pipeline

**Basic Usage (Incremental Processing)**:

```bash
python soa_cli.py
```

The pipeline automatically handles incremental processing:
- ✅ **New papers detected**: Only processes papers not yet extracted
- ✅ **Corrupted files detected**: Re-processes any invalid JSON files
- ✅ **All papers processed**: Skips to clustering if nothing new
- ✅ **Smart resumption**: Continues from where it left off

**Example scenarios**:
```bash
# First run: processes all 43 papers
python soa_cli.py

# Add 5 new papers to papers/ folder
# Second run: only processes the 5 new papers
python soa_cli.py

# If extraction failed for some papers
# Third run: re-processes only the failed papers
python soa_cli.py
```

**Force Re-processing**:

```bash
# Re-process ALL papers from scratch (ignore existing artifacts)
python soa_cli.py --force
# OR
python soa_cli.py -f
```

Use `--force` when:
- You changed the prompts and want fresh extraction
- You suspect extracted data is outdated
- You want to use a different LLM model

**Pipeline Stages**:
0. Load thematic contract (or prompt you to create one)
1. Read all PDFs from `papers/`
2. Extract structured knowledge (theme-filtered)
3. Evaluate methodological strength (theme-focused)
4. Build vector database (theme-filtered papers only)
5. Cluster papers by similarity (thematic clusters)
6. Synthesize cross-paper insights (addressing core questions)
7. Write State of the Art (theme-bounded)
8. Detect and repair hallucinations

### Run Individual Components

```bash
# Build thematic contract
python -m src.theme_builder build

# View current contract
python -m src.theme_builder show

# Just build vector database
python -m src.vectorize artifacts/extracted/

# Just run clustering
python -m src.similarity_cluster 6  # 6 clusters

# Just check for hallucinations
python -m src.hallucination_detector artifacts/soa/state_of_the_art.tex artifacts/extracted/

# Just run repair loop
python -m src.repair_loop artifacts/soa/state_of_the_art.tex artifacts/extracted/
```

## Output

### Primary Output

- `artifacts/soa/state_of_the_art_final.tex` - Your complete, verified State of the Art

### Intermediate Artifacts

- `artifacts/reader/*.json` - Parsed paper structures
- `artifacts/extracted/*.json` - Extracted facts per paper
- `artifacts/critic/*.json` - Quality assessments
- `artifacts/clusters/preclusters.json` - Raw similarity clusters
- `artifacts/clusters/clusters.json` - Interpreted clusters
- `artifacts/synthesis/synthesis.json` - Cross-paper synthesis
- `vector_db/index.faiss` - Vector index for similarity

### Verification Reports

- `artifacts/soa/hallucination_report.json` - Detected violations
- `artifacts/soa/repair_failure.json` - Unrepairable issues (if any)

## ⚙️ Configuration

Edit [soa_cli.py](soa_cli.py) to adjust:

```python
MODEL = None                 # Use default Qwen model (auto-detected)
TEMPERATURE = 0.2            # Lower = more deterministic
MAX_WORKERS = 6              # Parallel execution threads
MAX_PDF_CHARS = 30000        # Characters per paper (~15-20 pages)
```

For clustering, adjust in [src/similarity_cluster.py](src/similarity_cluster.py):

```python
n_clusters = 6               # Number of paper groups
```

**Qwen Model**: System uses default Qwen Code model (auto-detected). If you need to specify a model, set `MODEL = "coder-model"` or your preferred model name.

## Agent Constraints (IMPORTANT)

Each agent has **strict rules** encoded in system prompts:

- **Reader**: No summarization, no interpretation
- **Extractor**: Only explicit facts, no inference
- **Critic**: Skeptical but fair, evidence-based only
- **Cluster**: Interprets precomputed clusters, cannot create new ones
- **Synthesis**: Cross-paper patterns only, no single-paper descriptions
- **Writer**: Cannot invent citations or introduce new concepts

**These constraints are non-negotiable** for academic rigor.

## Hallucination Detection

4-layer verification system:

1. **Claim-Evidence Grounding** - Vector similarity check
2. **Citation Verification** - Cited papers must support claims
3. **Fact Coverage** - No out-of-vocabulary concepts
4. **Contradiction Check** - Cross-agent consistency

Threshold: < 5 violations = acceptable, > 5 = automatic repair triggered

## Repair Loop

- Max 3 iterations
- Repairs only flagged sentences
- Uses explicit evidence from cited papers
- If repair fails → generates failure report with specific issues

## Paper Input Requirements

Papers should be:
- In PDF format
- Named systematically (e.g., P01.pdf, P02.pdf, ...)
- Complete (not just abstracts)
- Readable by standard PDF parsers

## LLM Provider Integration

This system supports multiple LLM CLI providers through a unified interface:

### Supported Providers
- **Qwen** (default) - Open-source LLM
- **Claude** - Anthropic's Claude models (Sonnet, Opus, Haiku)
- **Gemini** - Google's Gemini models
- **OpenAI** - GPT models
- **Kilo** - Kilo AI models
- **GLM** - Zhipu AI's GLM models

### Configuration

Set your provider in [.env](.env):

```env
# Choose your provider
LLM_PROVIDER=qwen  # or claude, gemini, openai, kilo, glm

# Specify model (optional, uses default if empty)
LLM_MODEL=claude-sonnet-4.5  # or gpt-5.2, gemini-3-pro, etc.
```

### Requirements

Install the CLI for your chosen provider:

```bash
# Qwen
pip install qwen-cli

# Claude
npm install -g @anthropic/claude-cli

# Gemini
pip install google-generativeai

# OpenAI
pip install openai

# GLM
pip install zhipuai
```

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for detailed setup instructions.

## Academic Defense

When questioned in your thesis defense:

> "How did you ensure no hallucinations?"
> 
> → "We implemented a 4-layer verification system with automatic repair loops, ensuring every claim is grounded in extracted facts and supported by cited papers."

> "How did you group the papers?"
> 
> → "We used cosine similarity on methodological embeddings, followed by agglomerative clustering, with LLM interpretation only for naming and explanation."

> "Can you trace claims to sources?"
> 
> → "Yes, every claim includes paper IDs, and we maintain structured artifacts showing the complete chain from PDF to final text."

## Troubleshooting

### "No PDF files found"
- Ensure PDFs are in `papers/` directory
- Check file extensions are `.pdf`

### "Qwen failed"
- Verify Qwen CLI is installed: `which qwen`
- Check model name is correct
- Ensure sufficient API quota/resources

### "Vector DB not available"
- Run extraction first: extracted files needed before vectorization
- Check `faiss-cpu` is installed: `pip install faiss-cpu`

### "Unrepairable hallucinations"
- Check `artifacts/soa/repair_failure.json` for specific issues
- May indicate genuine gaps in your literature corpus
- Consider adding more papers or narrowing scope

## Performance

For 43 papers:
- **Reader**: ~5-10 min (depends on PDF complexity)
- **Extractor + Critic**: ~10-15 min (parallel)
- **Clustering**: ~2-3 min
- **Synthesis**: ~3-5 min
- **Writer**: ~2-3 min
- **Verification**: ~2-3 min

**Total**: ~25-40 minutes for complete pipeline

## Citation

If you use this system in your research:

```
This State of the Art was generated using a multi-agent verification system
with mathematical clustering and iterative hallucination repair, ensuring
full traceability and fact-grounding to the source literature.
```

## License

Production research tool. Use responsibly. Ensure human verification of final output before submission.

---

## Hard Truth (Coach Mode)

If you:
- Skip clustering
- Let one agent do everything
- Don't verify for hallucinations
- Allow "creative" writing

👉 Your SoA will be **academically weak**.

This architecture is the **minimum viable serious system** for AI-assisted literature review.

Reviewers **will** spot AI-generated content that lacks grounding. This system prevents that.

---

## 📚 Documentation

- [docs/QUICKREF.md](docs/QUICKREF.md) - Quick reference guide
- [docs/THEMATIC_PRIMING.md](docs/THEMATIC_PRIMING.md) - Thematic system guide
- [docs/USAGE.md](docs/USAGE.md) - Detailed usage instructions
- [docs/SCHEMAS.md](docs/SCHEMAS.md) - Data structure reference
- [docs/main.md](docs/main.md) - Architecture specification
- [docs/orchestrator.md](docs/orchestrator.md) - Pipeline design
- [docs/prompts.md](docs/prompts.md) - Agent constraints
- [docs/vectordb.md](docs/vectordb.md) - Clustering system
- [docs/hallucination.md](docs/hallucination.md) - Verification system
- [docs/rewriter.md](docs/rewriter.md) - Repair system
