# SOA-CLI: Automated State-of-the-Art Survey Generator

**SOA-CLI** is a production-grade, multi-agent system that automatically generates publication-quality State-of-the-Art surveys from research papers. Built on LangGraph, it orchestrates 16 specialized agents through a fault-tolerant pipeline to produce academically rigorous surveys ready for submission to top-tier venues.

## 🎯 What Does It Do?

**Input**: A folder of PDF research papers + your research theme  
**Output**: A publication-ready State-of-the-Art survey in Markdown format

The system:
- ✅ Extracts structured facts from papers (methods, results, limitations)
- ✅ Performs cross-paper synthesis (identifies patterns, contradictions, gaps)
- ✅ Generates publication-grade prose with proper citations
- ✅ Self-validates and repairs hallucinations automatically
- ✅ Produces surveys that meet standards of Nature Reviews, ACM Computing Surveys, IEEE TPAMI

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **LLM CLI Tool** - Install one of:
   - `qwen` (recommended for getting started)
   - `claude` (Anthropic)
   - `gemini` (Google)
   - `gpt` (OpenAI)
   - `glm` (Zhipu AI)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd SOA-CLI

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env to set your LLM_PROVIDER and other settings
```

### Basic Usage

```bash
# 1. Add your PDF papers to the papers/ directory
mkdir -p papers
cp /path/to/your/papers/*.pdf papers/

# 2. Run the pipeline
python soa_cli.py

# 3. Find your survey
# Output: STATE_OF_THE_ART.md
```

That's it! The system will:
1. Build a thematic contract from your papers
2. Extract facts from all PDFs in parallel
3. Cluster papers by similarity
4. Synthesize cross-paper insights
5. Write a publication-grade survey
6. Verify and repair any hallucinations
7. Output the final markdown document

## 📖 How to Use This Efficiently

### 1. Define Your Research Theme

**Option A: Interactive (Recommended for First-Time Users)**
```bash
# Just run the pipeline - it will prompt you
python soa_cli.py
# Enter: "Analyze deep learning methods for image generation quality assessment"
```

**Option B: Manual Control**
```bash
# Create theme input
python src/theme_builder.py template
# Edit theme_input.json with your research scope
python src/theme_builder.py build
# Review THEMATIC_CONTRACT.json
python soa_cli.py
```

**What is a Thematic Contract?**
- Defines your research scope (what's in, what's out)
- Lists core questions your survey will answer
- Guides all agents to focus on relevant content
- Prevents scope drift and off-topic content

### 2. Prepare Your Papers

**Manual Collection**
```bash
# Simply drop PDFs into papers/
cp ~/Downloads/*.pdf papers/
python soa_cli.py
```

**Automatic Paper Search (PRISMA Methodology)**
```bash
# Search for papers automatically
python soa_cli.py --search-papers
# Review candidates in paper_candidates.json
# Edit 'status' field: 'approved' or 'rejected'
python soa_cli.py --download-papers
# Run pipeline
python soa_cli.py
```

### 3. Configure for Your Needs

Edit `.env` to customize:

```bash
# LLM Configuration
LLM_PROVIDER=qwen          # Your CLI tool
LLM_MODEL=                 # Leave empty for default
LLM_TIMEOUT=300            # Increase for large surveys

# Pipeline Settings
MAX_WORKERS=10             # Parallel processing (adjust for your CPU)
MAX_PDF_CHARS=30000        # ~15-20 pages per paper
CLUSTER_COUNT=6            # Number of paper clusters (or 'auto')

# PDF Extraction
USE_SEMANTIC_PDF=true      # Extract figures/tables (recommended)
INCLUDE_FIGURES_IN_TEXT=true
INCLUDE_TABLES_IN_TEXT=true

# Citation Style
CITATION_STYLE=ieee        # ieee, apa, chicago, harvard
```

### 4. Advanced Usage

**Resume from Checkpoint**
```bash
# If pipeline crashes, resume where it left off
python soa_cli.py --resume
```

**Clean Start**
```bash
# Clear all cached artifacts
python soa_cli.py --clean
```

**Custom Repair Iterations**
```bash
# Allow more repair attempts for better quality
python soa_cli.py --max-repair 5
```

**Auto-detect Cluster Count**
```bash
# Let the system determine optimal clusters
python soa_cli.py --clusters auto
```

### 5. Understanding Output

**Primary Output**
- `STATE_OF_THE_ART.md` - Your final survey (Markdown)
- `db_outputs/soa/state_of_the_art.md` - Same content (canonical location)

**Intermediate Artifacts** (for debugging)
- `THEMATIC_CONTRACT.json` - Research scope definition
- `db_outputs/soa/citation_map.json` - Paper ID mappings
- `db_outputs/soa/rubric_report.json` - Quality scores
- `db_outputs/soa/hallucination_report.json` - Verification results
- `logs/` - Detailed execution logs

## 🏗️ How the System Works Internally

### Architecture Overview

SOA-CLI uses **LangGraph** to orchestrate a 16-node pipeline where each node is a specialized agent:

```
┌─────────────────────────────────────────────────────────────┐
│                    LANGGRAPH PIPELINE                        │
│                                                              │
│  theme_builder → reader_map → extractor_map → critic_map    │
│       ↓              ↓             ↓              ↓          │
│  vectorize → build_graph → cluster → interpret_clusters     │
│       ↓              ↓             ↓              ↓          │
│  synthesis → writer → reflector → rubric_evaluator          │
│       ↓              ↓             ↓              ↓          │
│  verifier → repair (loop) → final_output → figures_gen      │
└─────────────────────────────────────────────────────────────┘
```

### Pipeline Stages Explained

#### Stage 1: Theme Building
**Node**: `theme_builder`  
**Purpose**: Create immutable thematic contract  
**Input**: `theme_input.json` or interactive prompt  
**Output**: `THEMATIC_CONTRACT.json`

Defines:
- Global research theme
- Core questions to answer
- In-scope topics (what to include)
- Out-of-scope topics (what to exclude)
- Preferred methods and evaluation criteria

#### Stage 2: Paper Reading (Parallel)
**Node**: `reader_map`  
**Purpose**: Parse PDFs into structured text  
**Parallelism**: Up to `MAX_WORKERS` papers simultaneously  
**Output**: Structured JSON per paper

Features:
- **Semantic PDF parsing**: Extracts sections, figures, tables with context
- **Smart truncation**: Prioritizes Abstract, Intro, Methods, Results over References
- **Fallback**: Plain text extraction if semantic parsing fails

#### Stage 3: Fact Extraction (Parallel)
**Node**: `extractor_map`  
**Purpose**: Extract structured facts from papers  
**Parallelism**: Up to `MAX_WORKERS` papers simultaneously  
**Output**: Structured facts per paper

Extracts:
- Research context (problem, questions, scope)
- Methodology (algorithms, architectures, complexity)
- Data & evaluation (datasets, baselines, metrics)
- Results (quantitative findings, ablations, error analysis)
- Assumptions and limitations

#### Stage 4: Methodological Critique (Parallel)
**Node**: `critic_map`  
**Purpose**: Assess methodological quality  
**Parallelism**: Up to `MAX_WORKERS` papers simultaneously  
**Output**: Quality assessment per paper

Evaluates:
- Problem-method fit
- Experimental rigor
- Baseline fairness
- Statistical validity
- Reproducibility
- Thematic relevance

#### Stage 5: Vectorization
**Node**: `vectorize`  
**Purpose**: Create embeddings for clustering  
**Technology**: FAISS + sentence-transformers  
**Output**: Vector database

#### Stage 6: Citation Graph Building
**Node**: `build_graph`  
**Purpose**: Build citation network  
**Output**: Directed graph of paper relationships

Captures:
- Citation links between papers
- Thematic similarity edges
- Hierarchical structure

#### Stage 7: Clustering
**Node**: `cluster`  
**Purpose**: Group papers by similarity  
**Method**: K-means or auto-detection (silhouette analysis)  
**Output**: Paper clusters

#### Stage 8: Cluster Interpretation
**Node**: `interpret_clusters`  
**Purpose**: LLM interprets cluster meaning  
**Output**: Named clusters with themes

Identifies:
- Cluster names (e.g., "Attention-Based Sequence Models")
- Methodological cohesion
- Within-cluster variations
- Shared assumptions and limitations

#### Stage 9: Cross-Paper Synthesis
**Node**: `synthesis`  
**Purpose**: Synthesize insights across papers  
**Output**: Cross-paper patterns

Generates:
- Convergences (what papers agree on)
- Contradictions (conflicting findings + explanations)
- Methodological trade-offs
- Temporal evolution
- Research gaps

#### Stage 10: Survey Writing
**Node**: `writer`  
**Purpose**: Generate publication-grade prose  
**Output**: Markdown document

Features:
- Cross-paper synthesis (not paper-by-paper summaries)
- Proper citation formatting (Pandoc-compatible)
- Technical depth (equations, algorithms, tables)
- Structured sections (Abstract, Intro, Methods, Analysis, Gaps, Conclusion)

#### Stage 11: Hierarchical Reflection
**Node**: `reflector`  
**Purpose**: Multi-level quality check  
**Levels**: L1 (structure), L2 (sections), L3 (paragraphs)  
**Output**: Feedback for rewriting

Checks:
- Heading count and depth
- Citation density
- Section completeness
- Logical flow

**Loop**: If reflector fails, returns to writer (max 2 rewrites)

#### Stage 12: Rubric Evaluation
**Node**: `rubric_evaluator`  
**Purpose**: Multi-dimensional quality scoring  
**Output**: Scores + failing dimensions

Dimensions:
- Thematic coherence
- Technical depth
- Synthesis quality
- Evidence & citation integrity
- Critical analysis rigor
- Writing quality
- Structural completeness
- Publication readiness

#### Stage 13: Verification
**Node**: `verifier`  
**Purpose**: Detect hallucinations  
**Output**: Violation list

Checks:
- Invalid citation IDs
- Uncited claims
- Citation-claim mismatches
- Overgeneralizations

#### Stage 14: Repair (Loop)
**Node**: `repair`  
**Purpose**: Fix hallucinations  
**Loop**: Repair → Verifier (max `--max-repair` iterations)  
**Output**: Corrected document

#### Stage 15: Final Output
**Node**: `final_output`  
**Purpose**: Finalize and persist  
**Output**: Timing summary, metadata

#### Stage 16: Figures Generation (Skipped in DB Mode)
**Node**: `figures_generator`  
**Purpose**: Generate TikZ figures (LaTeX only)  
**Status**: Skipped in current markdown-only mode

### State Management

**LangGraph State** (`SOAState`):
- **Immutable inputs**: `thematic_contract`, `paper_paths`, `max_repair_iterations`
- **Aggregating collections**: `reader_outputs`, `extracted_facts`, `critic_assessments` (merge across parallel ops)
- **Single-value fields**: `embeddings`, `clusters`, `synthesis`, `soa_draft` (last write wins)
- **Quality signals**: `rubric_scores`, `reflector_feedback`, `verification_results`
- **Timing**: `stage_durations`, `total_wall_clock_seconds`

**Persistence**:
- **In-memory**: LangGraph state (checkpointed with MemorySaver)
- **Disk**: Final markdown + intermediate JSON artifacts
- **PostgreSQL** (optional): Run metadata, artifacts, metrics

### Fault Tolerance

**Parallel Processing**:
- ThreadPoolExecutor for reader/extractor/critic stages
- Errors isolated per paper (don't crash entire pipeline)
- Partial results preserved

**Retry Logic**:
- LLM calls: 3 retries with exponential backoff
- JSON parsing errors: Retry with stronger instructions
- Markdown validation: Retry with completion instructions

**Checkpointing**:
- LangGraph MemorySaver enables `--resume`
- Artifacts cached on disk (skip reprocessing)

**Error Handling**:
- Errors collected in `state["errors"]`
- Pipeline continues despite individual failures
- Final report shows all errors

## 🔧 Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `qwen` | CLI tool: qwen, claude, gemini, gpt, glm |
| `LLM_MODEL` | (empty) | Specific model or empty for default |
| `LLM_TIMEOUT` | `120` | Timeout in seconds (increase for large tasks) |
| `LLM_TEMPERATURE` | `0.3` | 0.0-1.0 (lower = more deterministic) |
| `CITATION_STYLE` | `ieee` | ieee, apa, chicago, harvard |
| `MAX_WORKERS` | `10` | Parallel processing threads |
| `MAX_PDF_CHARS` | `30000` | Max chars per PDF (~15-20 pages) |
| `CLUSTER_COUNT` | `6` | Number of clusters or 'auto' |
| `USE_SEMANTIC_PDF` | `true` | Extract figures/tables/structure |
| `EXTRACT_PDF_IMAGES` | `false` | Save figure images |
| `INCLUDE_FIGURES_IN_TEXT` | `true` | Include figure captions in LLM input |
| `INCLUDE_TABLES_IN_TEXT` | `true` | Include tables in LLM input |

### Command-Line Options

```bash
python soa_cli.py [OPTIONS]

Options:
  --papers DIR          Papers directory (default: papers)
  --max-repair N        Max repair iterations (default: 3)
  --thread-id ID        Thread ID for checkpointing (default: default)
  --resume              Resume from checkpoint
  --clean               Clear all artifacts before running
  --clusters N|auto     Number of clusters or 'auto' (default: auto)
  --format FORMAT       Output format: markdown (default: markdown)
```

## 📊 Quality Assurance

### Multi-Layer Validation

1. **Reflector** (L1-L3): Structural and content quality
2. **Rubric Evaluator**: 8-dimensional scoring
3. **Verifier**: Hallucination detection
4. **Repair Loop**: Automatic correction (up to `--max-repair` iterations)

### Quality Metrics

The system tracks:
- Citation density (target: 60%+ of paragraphs cited)
- Heading count (target: 6+ major sections)
- Invalid citation rate (target: 0%)
- Synthesis paper coverage (target: 50%+ papers referenced)
- Rubric scores (target: 3.5+ on all dimensions)

### Output Quality

Generated surveys meet standards of:
- Nature Reviews
- ACM Computing Surveys
- IEEE TPAMI
- Annual Reviews
- JMLR

## 🐛 Troubleshooting

### Common Issues

**"CLI binary not found"**
```bash
# Install your chosen LLM CLI tool
# For qwen: follow installation instructions
# Verify: which qwen
```

**"Timeout during writer/synthesis"**
```bash
# Increase timeout in .env
LLM_TIMEOUT=600
```

**"Low citation density"**
```bash
# Increase repair iterations
python soa_cli.py --max-repair 5
```

**"Papers not clustering well"**
```bash
# Try auto-detection
python soa_cli.py --clusters auto
# Or adjust manually
python soa_cli.py --clusters 8
```

**"PDF extraction truncated"**
```bash
# Increase max chars in .env
MAX_PDF_CHARS=50000
```

**"Semantic parsing failed"**
```bash
# System auto-falls back to text-only
# To force text-only mode:
USE_SEMANTIC_PDF=false
```

### Debug Mode

```bash
# Enable detailed logging
export DEBUG=true
python soa_cli.py

# Check logs
tail -f logs/soa_pipeline_*.log
```

## 📚 Documentation

- **[User Guide](docs/USAGE.md)**: Detailed usage instructions
- **[Configuration Guide](docs/CONFIGURATION.md)**: All settings explained
- **[Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)**: Technical architecture
- **[LangGraph Guide](docs/LANGGRAPH_GUIDE.md)**: Pipeline orchestration details
- **[Provider Setup](docs/PROVIDER_SETUP.md)**: LLM CLI installation
- **[Paper Fetcher Guide](docs/PAPER_FETCHER_GUIDE.md)**: Automatic paper search
- **[Semantic PDF Guide](docs/SEMANTIC_PDF_IMPLEMENTATION.md)**: Enhanced extraction

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional LLM providers
- Enhanced figure generation
- Multi-language support
- Web interface
- Batch processing

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

Built with:
- **LangGraph**: Pipeline orchestration
- **FAISS**: Vector similarity search
- **PyMuPDF**: PDF parsing
- **sentence-transformers**: Embeddings
- **scikit-learn**: Clustering

## 📞 Support

- Issues: [GitHub Issues](your-repo-url/issues)
- Documentation: [docs/](docs/)
- Examples: [examples/](examples/)

---

**Ready to generate your first survey?**

```bash
python soa_cli.py
```

The system will guide you through the process interactively!
