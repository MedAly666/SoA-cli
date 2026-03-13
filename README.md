# SOA-CLI: Production-Grade Multi-Agent State of the Art Generator

A CLI-based multi-agent system for generating academically rigorous State of the Art sections from research papers. Built with **LangGraph** for fault-tolerant orchestration and the principles of **traceability**, **fact-grounding**, **hallucination prevention**, and **thematic priming**.

---

## 🚀 Quick Start

```bash
# 1. Setup (installs dependencies including LangGraph)
./setup.sh

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Configure environment
cp .env.example .env
# Edit .env (set LLM_PROVIDER, configure paper fetcher, etc.)

# 4. Define your research scope
python -m src.theme_builder template
nano theme_input.json
python -m src.theme_builder build

# 5. Run pipeline (auto-searches for papers if none exist!)
python3 soa_cli.py

# If papers/ is empty, system automatically:
#   → Searches academic databases (Semantic Scholar, arXiv)
#   → Generates paper_candidates.json for review
#   → Prompts you to approve candidates
# Then:
#   → Review paper_candidates.json  
#   → Run: python soa_cli.py --download-papers
#   → Run: python soa_cli.py (continues with SOA generation)

# Output: state_of_the_art.tex
```

**Key Features**:
- ✅ **Automatic paper discovery** with PRISMA methodology
- ✅ Fault tolerance with automatic checkpointing
- ✅ Explicit control flow with verification gates
- ✅ Better error handling (accumulates, doesn't crash)
- ✅ Type-safe state management
- ✅ Resume from any point if interrupted

---

## 🎯 Recent Enhancements

SOA-CLI has been enhanced with five major improvements for reliability, flexibility, and user experience:

### 1. **Unified CLI-Based LLM Client with Retry Logic**
- ✅ Routes to CLI binaries (claude, gemini, qwen, gpt, glm)
- ✅ Exponential backoff retry (3 attempts: 2s, 4s, 8s delays)
- ✅ Graceful failure handling (no pipeline crashes)
- ✅ Provider verification at startup
- 📝 Configure: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_TIMEOUT` in `.env`

### 2. **Dynamic Cluster Count Selection**
- ✅ Auto-detects optimal cluster count using silhouette analysis
- ✅ Tests k from 2 to 10, selects best
- ✅ CLI flag: `--clusters auto` or `--clusters 5`
- 📊 Handles edge cases (< 3 papers)

### 3. **Multi-Format Output Export**
- ✅ LaTeX (default), Markdown, Word formats
- ✅ CLI flag: `--format latex|markdown|docx|all`
- 📄 Output: `state_of_the_art.tex`, `.md`, `.docx`
- 🎨 Word docs with styled formatting (headings, bold, citations)

### 4. **Citation Style Configuration**
- ✅ Supports IEEE, APA, Chicago, Harvard
- ✅ Runtime injection into writer prompts
- ✅ Configure: `CITATION_STYLE=ieee` in `.env`
- 📚 Style-specific guidelines for LLMs

### 5. **Smart PDF Truncation with Warnings**
- ✅ Importance scoring (keeps Abstract/Intro/Methods/Results)
- ✅ Drops References/Appendices first
- ⚠️ Yellow console warnings with truncation stats
- 📊 Metadata tracking in artifacts

### 6. **Automatic Paper Discovery with PRISMA Methodology**
- ✅ Auto-triggers when `papers/` directory is empty
- ✅ Searches Semantic Scholar + arXiv with LLM-generated queries
- ✅ PRISMA-compliant workflow (Identification → Screening → Eligibility)
- ✅ Quality filters: venue whitelist, citation counts, year ranges
- ✅ Predatory publisher detection
- ✅ Generates `paper_candidates.json` for manual review
- ✅ Full PRISMA report with flow diagrams
- ✅ **Final SOA document includes PRISMA methodology section automatically**
- 📝 Configure: `PAPER_SOURCES`, `PAPER_MIN_YEAR`, `PAPER_MIN_CITATIONS` in `.env`
- 📚 See [PAPER_FETCHER_GUIDE.md](PAPER_FETCHER_GUIDE.md) for complete documentation

**PRISMA in Your Document**: When papers are fetched via the paper fetcher, the generated State of the Art document automatically includes a comprehensive methodology section documenting:
- Search strategy (databases, queries, dates)
- PRISMA 4-stage selection process with flow diagram
- Quality assessment criteria
- Data extraction procedures

This makes your literature review publication-ready and compliant with systematic review standards!

**Example Commands**:
```bash
# Auto-detect clusters, export as Markdown, use APA citations
python soa_cli.py --clusters auto --format markdown
# (Set CITATION_STYLE=apa in .env)

# Export all formats at once
python soa_cli.py --format all

# Manual cluster count override
python soa_cli.py --clusters 4

# Paper fetcher commands (automatic if papers/ is empty)
python soa_cli.py --search-papers        # Manual paper search
python soa_cli.py --download-papers      # Download approved papers
python soa_cli.py --prisma-report        # Generate PRISMA report
```

See [CHANGELOG.md](CHANGELOG.md) for detailed documentation of all enhancements.

---

## 📖 Documentation

For detailed documentation, see the [docs/](docs/) directory:

- **[docs/README.md](docs/README.md)** - Documentation index
- **[docs/QUICKREF.md](docs/QUICKREF.md)** - Quick reference card
- **[docs/USAGE.md](docs/USAGE.md)** - Complete usage guide
- **[docs/LANGGRAPH_GUIDE.md](docs/LANGGRAPH_GUIDE.md)** - Architecture deep dive
- **[docs/THEMATIC_PRIMING.md](docs/THEMATIC_PRIMING.md)** - Thematic contract system
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** - Environment variables

---

## 📁 Project Structure

```
soa-cli/
├── soa_cli.py              # ⭐ MAIN ENTRY POINT (LangGraph orchestration)
├── README.md               # This file
├── requirements.txt        # Dependencies (includes LangGraph)
├── setup.sh                # Automated setup script
├── activate.sh             # Virtual environment activation
│
├── src/                    # Core implementation
│   ├── graph/              # LangGraph architecture
│   │   ├── state.py        # SOAState TypedDict
│   │   ├── nodes.py        # 11 agent nodes
│   │   └── builder.py      # Graph construction
│   ├── theme_builder.py    # Thematic contract system
│   ├── paper_fetcher.py    # PRISMA paper search & screening
│   ├── pdf_parser.py       # Semantic PDF extraction
│   ├── vectorize.py        # FAISS embeddings
│   ├── similarity_cluster.py  # Clustering
│   ├── hallucination_detector.py  # Verification
│   ├── repair_loop.py      # Repair system
│   ├── llm_client.py       # Unified LLM interface
│   ├── exporter.py         # Multi-format export
│   └── citation_formatter.py  # Citation styles
│
├── prompts/                # Agent system prompts (12 files)
│   ├── theme_builder.system.txt
│   ├── theme_description_to_json.system.txt
│   ├── query_generator.system.txt
│   ├── paper_screening.system.txt
│   ├── reader.system.txt
│   ├── extractor.system.txt
│   ├── critic.system.txt
│   ├── cluster.system.txt
│   ├── synthesis.system.txt
│   ├── writer.system.txt
│   ├── verifier.system.txt
│   └── repair.system.txt
│
├── config/                 # Configuration files
│   └── venues.json         # Approved publication venues
│
├── scripts/                # Utility scripts
│   └── check.py            # Pre-flight verification
│
├── papers/                 # Input PDFs (add your papers here)
│
├── artifacts/              # All outputs (organized by stage)
│   ├── states/             # Pipeline states
│   │   ├── initial_state.json
│   │   └── final_state.json
│   ├── prisma/             # Paper search results
│   │   ├── prisma_report.json
│   │   ├── prisma_flow_diagram.md
│   │   └── excluded_papers.json
│   ├── vector_db/          # Vector database
│   │   ├── index.faiss
│   │   └── meta.json
│   ├── reader/             # Parsed papers
│   ├── extracted/          # Extracted facts
│   ├── critic/             # Quality assessments
│   ├── clusters/           # Clustering outputs
│   ├── synthesis/          # Cross-paper synthesis
│   └── soa/                # ⭐ Final outputs
│
└── docs/                   # Complete documentation
    ├── README.md           # Documentation index
    ├── QUICKREF.md         # Quick reference
    ├── USAGE.md            # Usage guide
    ├── LANGGRAPH_GUIDE.md  # Architecture guide
    ├── THEMATIC_PRIMING.md # Thematic system
    ├── PAPER_FETCHER_GUIDE.md  # Paper search
    ├── CONFIGURATION.md    # Configuration reference
    └── ...                 # Additional guides
```

---

## 🏗️ Architecture

SOA-CLI uses **LangGraph** for production-grade orchestration:

```
11 Nodes → 13 Edges → Verification Gate → Repair Loop (max 3 iterations)
```

**Pipeline:**
1. **Theme Builder** - Global research scope
2. **Reader Map** (parallel) - PDF text extraction
3. **Extractor Map** (parallel) - Fact extraction
4. **Critic Map** (parallel) - Methodology evaluation
5. **Vectorize** - FAISS embeddings
6. **Cluster** - Similarity grouping
7. **Interpret Clusters** - Thematic analysis
8. **Synthesis** - Cross-paper reasoning
9. **Writer** - LaTeX generation
10. **Verifier** - Hallucination detection
11. **Repair** (conditional) - Iterative fixes

**Key Features:**
- ✅ Automatic checkpointing (resume from any node)
- ✅ Type-safe state (TypedDict with 18 fields)
- ✅ Verification gates with conditional routing
- ✅ Repair loop with max iteration guard
- ✅ Parallel processing (Reader, Extractor, Critic)
- ✅ Error accumulation (doesn't crash)

**Performance:** ~10-15 minutes for 10 papers

---

## 🔧 Installation

**Prerequisites**:
- Python 3.8+
- LLM CLI (qwen, gemini, claude, etc.)
- Research papers in PDF format

**Setup**:

```bash
# Automated setup (creates .venv, installs dependencies)
./setup.sh

# Activate the virtual environment
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

Before running the pipeline, define your thematic scope:

```bash
# Create template
python -m src.theme_builder template

# Edit with your research focus
nano theme_input.json

# Build thematic contract
python -m src.theme_builder build
```

This creates `THEMATIC_CONTRACT.json` - the **single source of truth** that guides all agents.

**Why this matters**: Thematic priming ensures focused extraction and faster processing. See [docs/THEMATIC_PRIMING.md](docs/THEMATIC_PRIMING.md) for details.

### Step 2: Add Papers

```bash
# Copy your PDF papers to the papers directory
cp /path/to/papers/*.pdf papers/
```

### Step 3: Run Pipeline

**Basic Usage**:

```bash
python3 soa_cli.py
```

The pipeline processes all papers with:
- ✅ Automatic PDF text extraction
- ✅ Parallel processing (Reader, Extractor, Critic)
- ✅ Clustering and synthesis
- ✅ LaTeX generation
- ✅ Verification and repair (up to 3 iterations)

**Output**: `state_of_the_art.tex` in the root directory

**Advanced Options**:

```bash
# Custom papers directory
python3 soa_cli.py --papers /path/to/pdfs

# Increase repair iterations
python3 soa_cli.py --max-repair 5

# Resume from checkpoint
python3 soa_cli.py --resume --thread-id my-session
```
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

- `state_of_the_art.tex` (root) - Your complete, verified State of the Art
- `artifacts/soa/state_of_the_art_draft.tex` - Initial draft before verification (for debugging)

### Intermediate Artifacts

- `artifacts/states/initial_state.json` - Pipeline initial state
- `artifacts/states/final_state.json` - Pipeline final state  
- `artifacts/prisma/prisma_report.json` - PRISMA paper search report  
- `artifacts/prisma/excluded_papers.json` - Papers excluded during screening
- `artifacts/reader/*.json` - Parsed paper structures
- `artifacts/extracted/*.json` - Extracted facts per paper
- `artifacts/critic/*.json` - Quality assessments
- `artifacts/clusters/preclusters.json` - Raw similarity clusters
- `artifacts/clusters/clusters.json` - Interpreted clusters
- `artifacts/synthesis/synthesis.json` - Cross-paper synthesis
- `artifacts/vector_db/index.faiss` - Vector index for similarity
- `artifacts/vector_db/meta.json` - Vector database metadata

### Verification Reports

- `artifacts/soa/hallucination_report.json` - Detected violations
- `artifacts/soa/repair_failure.json` - Unrepairable issues (if any)

## ⚙️ Configuration

Set environment variables to adjust:

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

- **[docs/README.md](docs/README.md)** - Documentation index and overview
- **[docs/QUICKREF.md](docs/QUICKREF.md)** - Quick reference guide
- **[docs/USAGE.md](docs/USAGE.md)** - Detailed usage instructions
- **[docs/LANGGRAPH_GUIDE.md](docs/LANGGRAPH_GUIDE.md)** - Architecture deep dive
- **[docs/THEMATIC_PRIMING.md](docs/THEMATIC_PRIMING.md)** - Thematic system guide
- **[docs/PAPER_FETCHER_GUIDE.md](docs/PAPER_FETCHER_GUIDE.md)** - Paper search and PRISMA workflow
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** - Environment variables and configuration
- **[docs/SCHEMAS.md](docs/SCHEMAS.md)** - Data structure reference
- **[docs/PROVIDER_SETUP.md](docs/PROVIDER_SETUP.md)** - LLM provider setup instructions
- **[docs/vectordb.md](docs/vectordb.md)** - Clustering and vector database system
- **[docs/hallucination.md](docs/hallucination.md)** - Verification and hallucination detection
