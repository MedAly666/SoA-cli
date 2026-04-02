# SOA-CLI User Guide

Complete guide to using SOA-CLI efficiently for generating publication-quality surveys.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Workflow Overview](#workflow-overview)
3. [Defining Your Research Theme](#defining-your-research-theme)
4. [Preparing Papers](#preparing-papers)
5. [Running the Pipeline](#running-the-pipeline)
6. [Understanding Output](#understanding-output)
7. [Optimizing Quality](#optimizing-quality)
8. [Advanced Features](#advanced-features)
9. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

1. **Python 3.8+**
2. **LLM CLI Tool** - One of:
   - `qwen` (recommended)
   - `claude`
   - `gemini`
   - `gpt`
   - `glm`

### Installation

```bash
# Clone and install
git clone <repo-url>
cd SOA-CLI
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env: set LLM_PROVIDER and other settings
```

### First Run

```bash
# Add papers
mkdir -p papers
cp /path/to/papers/*.pdf papers/

# Run
python soa_cli.py

# Output: STATE_OF_THE_ART.md
```

## Workflow Overview

### Standard Workflow

```
1. Define Theme → 2. Add Papers → 3. Run Pipeline → 4. Review Output
```

### Detailed Steps

1. **Theme Definition**
   - Interactive prompt OR manual `theme_input.json`
   - System generates `THEMATIC_CONTRACT.json`

2. **Paper Collection**
   - Manual: Drop PDFs in `papers/`
   - Automatic: Use `--search-papers` (PRISMA methodology)

3. **Pipeline Execution**
   - 16-stage LangGraph pipeline
   - Parallel processing (reader, extractor, critic)
   - Automatic quality validation and repair

4. **Output Review**
   - `STATE_OF_THE_ART.md` - Final survey
   - Quality reports in `db_outputs/soa/`

## Defining Your Research Theme

### Why Theme Matters

The thematic contract:
- Defines scope boundaries (in/out)
- Lists core research questions
- Guides all agents to focus on relevant content
- Prevents scope drift

### Method 1: Interactive (Recommended)

```bash
python soa_cli.py
# Prompt: "Enter theme description:"
# Example: "Deep learning methods for medical image segmentation"
```

System generates:
- `theme_input.json` - Structured input
- `THEMATIC_CONTRACT.json` - Final contract

### Method 2: Manual Control

```bash
# Create template
python src/theme_builder.py template

# Edit theme_input.json
{
  "title": "Your Research Title",
  "research_goals": [
    "Goal 1: Analyze X methods",
    "Goal 2: Compare Y approaches",
    "Goal 3: Identify gaps in Z"
  ],
  "specific_constraints": [
    "Focus on supervised learning only",
    "Papers from 2020-2024",
    "Medical imaging domain"
  ],
  "what_to_exclude": [
    "Unsupervised methods",
    "Non-medical applications",
    "Theoretical-only papers"
  ]
}

# Build contract
python src/theme_builder.py build

# Review
python src/theme_builder.py show
```

### Theme Best Practices

**Good Theme**:
```json
{
  "title": "Transformer Architectures for Time Series Forecasting",
  "research_goals": [
    "Compare attention mechanisms for temporal data",
    "Analyze scalability to long sequences",
    "Evaluate performance on multivariate forecasting"
  ],
  "specific_constraints": [
    "Transformer-based models only",
    "Time series domain",
    "Empirical evaluation required"
  ],
  "what_to_exclude": [
    "RNN/LSTM architectures",
    "Image/text domains",
    "Purely theoretical work"
  ]
}
```

**Bad Theme** (too vague):
```json
{
  "title": "Machine Learning",
  "research_goals": ["Study ML methods"],
  "specific_constraints": ["Recent papers"],
  "what_to_exclude": ["Old papers"]
}
```

## Preparing Papers

### Manual Collection

```bash
# Simply add PDFs
cp ~/Downloads/*.pdf papers/
python soa_cli.py
```

**Recommendations**:
- 10-50 papers: Focused survey
- 50-100 papers: Comprehensive survey
- 100+ papers: May need to increase `MAX_WORKERS` and `LLM_TIMEOUT`

### Automatic Paper Search (PRISMA)

```bash
# Step 1: Search
python soa_cli.py --search-papers
# Generates: paper_candidates.json

# Step 2: Review candidates
# Edit paper_candidates.json:
# - Set "status": "approved" for papers you want
# - Set "status": "rejected" for papers to exclude

# Step 3: Download
python soa_cli.py --download-papers
# Downloads approved papers to papers/

# Step 4: Run pipeline
python soa_cli.py
```

**Configure Search** (in `.env`):
```bash
PAPER_SOURCES=semantic_scholar,arxiv
PAPER_MAX_RESULTS=50
PAPER_MIN_YEAR=2015
PAPER_MIN_CITATIONS=10
PAPER_REQUIRE_WHITELIST=true
```

### Paper Quality Tips

**Include**:
- Peer-reviewed conference/journal papers
- Papers with clear methodology
- Papers with empirical evaluation
- Papers from reputable venues

**Exclude**:
- Preprints without peer review (unless very recent)
- Papers without methodology section
- Papers without results
- Duplicate papers (same work, different venues)

## Running the Pipeline

### Basic Run

```bash
python soa_cli.py
```

### Common Options

```bash
# Clean start (clear cache)
python soa_cli.py --clean

# More repair iterations (better quality)
python soa_cli.py --max-repair 5

# Auto-detect cluster count
python soa_cli.py --clusters auto

# Custom cluster count
python soa_cli.py --clusters 8

# Resume from checkpoint
python soa_cli.py --resume

# Custom papers directory
python soa_cli.py --papers /path/to/papers
```

### Configuration Tuning

Edit `.env` for your needs:

**For Speed**:
```bash
MAX_WORKERS=20          # More parallel processing
LLM_TIMEOUT=60          # Shorter timeout
MAX_PDF_CHARS=20000     # Less text per paper
```

**For Quality**:
```bash
MAX_WORKERS=5           # More careful processing
LLM_TIMEOUT=600         # Allow longer LLM calls
MAX_PDF_CHARS=50000     # More text per paper
USE_SEMANTIC_PDF=true   # Extract figures/tables
```

**For Large Surveys (100+ papers)**:
```bash
MAX_WORKERS=15
LLM_TIMEOUT=900
CLUSTER_COUNT=12
```

### Pipeline Stages

The pipeline runs 16 stages automatically:

1. **theme_builder**: Create thematic contract
2. **reader_map**: Parse PDFs (parallel)
3. **extractor_map**: Extract facts (parallel)
4. **critic_map**: Assess quality (parallel)
5. **vectorize**: Create embeddings
6. **build_graph**: Build citation network
7. **cluster**: Group similar papers
8. **interpret_clusters**: Name clusters
9. **synthesis**: Cross-paper insights
10. **writer**: Generate survey
11. **reflector**: Quality check (may loop to writer)
12. **rubric_evaluator**: Score quality
13. **verifier**: Detect hallucinations
14. **repair**: Fix issues (may loop to verifier)
15. **final_output**: Finalize
16. **figures_generator**: (skipped in markdown mode)

**Typical Runtime**:
- 10 papers: 10-20 minutes
- 50 papers: 30-60 minutes
- 100 papers: 1-2 hours

## Understanding Output

### Primary Output

**STATE_OF_THE_ART.md**
- Final survey in Markdown format
- Pandoc-compatible (can convert to LaTeX, PDF, DOCX)
- Ready for submission after manual review

**Structure**:
```markdown
# Title

## Abstract

## Introduction

## Background

## Methodology Taxonomy

## Comparative Analysis

## Cross-Cutting Synthesis

## Research Gaps

## Future Directions

## Conclusion

## References
```

### Quality Reports

**db_outputs/soa/rubric_report.json**
```json
{
  "scores": {
    "thematic_coherence": 4.5,
    "technical_depth": 4.2,
    "synthesis_quality": 4.8,
    "evidence_citation_integrity": 4.6,
    "critical_analysis_rigor": 4.3,
    "writing_quality": 4.4,
    "structural_completeness": 4.7,
    "publication_readiness": 4.5
  },
  "overall_assessment": "ready"
}
```

**Interpretation**:
- 5.0: Exceptional (top 5%)
- 4.0-4.9: Strong (top 20%)
- 3.0-3.9: Adequate (top 50%)
- 2.0-2.9: Weak (needs work)
- 1.0-1.9: Poor (major revision)

**db_outputs/soa/hallucination_report.json**
```json
{
  "total_claims_checked": 150,
  "total_violations": 2,
  "hallucination_rate": 0.013,
  "repair_triggered": true,
  "status": "completed"
}
```

**Interpretation**:
- 0% violations: Perfect
- <5% violations: Excellent
- 5-10% violations: Good (repaired)
- >10% violations: Needs manual review

### Intermediate Artifacts

**THEMATIC_CONTRACT.json**
- Research scope definition
- Core questions
- In/out scope boundaries

**db_outputs/soa/citation_map.json**
- Maps canonical IDs (P001, P002) to paper titles
- Used for citation resolution

**logs/soa_pipeline_*.log**
- Detailed execution log
- Useful for debugging

## Optimizing Quality

### Quality Checklist

Before considering output final:

1. **Thematic Coherence**
   - [ ] All content aligns with theme
   - [ ] No off-topic sections
   - [ ] Core questions answered

2. **Technical Depth**
   - [ ] Equations/algorithms included where relevant
   - [ ] Quantitative results cited
   - [ ] Methodological details sufficient

3. **Synthesis Quality**
   - [ ] Cross-paper patterns identified
   - [ ] Contradictions explained
   - [ ] Trade-offs analyzed
   - [ ] Gaps identified

4. **Citation Integrity**
   - [ ] All claims cited
   - [ ] No invalid citations
   - [ ] Citation density >60%

5. **Critical Analysis**
   - [ ] Limitations discussed
   - [ ] Evidence quality assessed
   - [ ] Uncertainty acknowledged

### Improving Quality

**If rubric scores <4.0**:

```bash
# Increase repair iterations
python soa_cli.py --max-repair 5 --clean

# Adjust LLM settings
# In .env:
LLM_TIMEOUT=600
LLM_TEMPERATURE=0.2  # More deterministic
```

**If synthesis is weak**:

```bash
# Ensure enough papers
# Minimum: 10 papers
# Recommended: 20-50 papers

# Check cluster count
python soa_cli.py --clusters auto
```

**If citations are missing**:

```bash
# Check citation_map.json
# Ensure all papers were extracted successfully
# Re-run with --clean if needed
```

### Manual Review

Always perform manual review:

1. **Read Abstract and Introduction**
   - Does it match your research goals?
   - Is the scope clear?

2. **Check Core Sections**
   - Are all core questions answered?
   - Is technical depth appropriate?

3. **Verify Citations**
   - Spot-check 5-10 citations
   - Ensure claims match cited papers

4. **Review Gaps Section**
   - Are gaps meaningful?
   - Are they evidence-based?

5. **Polish Writing**
   - Fix any awkward phrasing
   - Ensure consistent terminology
   - Add domain-specific nuance

## Advanced Features

### Custom Prompts

All prompts are in `prompts/` directory:

```bash
# Edit prompts to customize behavior
prompts/writer.system.txt       # Survey writing style
prompts/synthesis.system.txt    # Synthesis approach
prompts/extractor.system.txt    # Fact extraction
# ... etc
```

**After editing prompts**:
```bash
python soa_cli.py --clean  # Force re-run with new prompts
```

### Semantic PDF Extraction

Enhanced extraction mode (default: enabled):

```bash
# In .env:
USE_SEMANTIC_PDF=true           # Extract structure
INCLUDE_FIGURES_IN_TEXT=true    # Include figure captions
INCLUDE_TABLES_IN_TEXT=true     # Include tables
EXTRACT_PDF_IMAGES=false        # Save images (for vision LLM)
```

**Benefits**:
- 60-80% more information vs plain text
- Preserves figures, tables, equations
- Maintains section structure
- Better context understanding

**Fallback**:
- If semantic parsing fails, auto-falls back to text-only
- No manual intervention needed

### Citation Styles

```bash
# In .env:
CITATION_STYLE=ieee     # [1], [2], [3]
CITATION_STYLE=apa      # (Author, Year)
CITATION_STYLE=chicago  # (Author Year)
CITATION_STYLE=harvard  # (Surname Year)
```

### Batch Processing

Process multiple surveys:

```bash
# Survey 1
cp papers-set1/*.pdf papers/
python soa_cli.py
mv STATE_OF_THE_ART.md survey1.md

# Survey 2
python soa_cli.py --clean
cp papers-set2/*.pdf papers/
python soa_cli.py
mv STATE_OF_THE_ART.md survey2.md
```

### PostgreSQL Persistence (Optional)

Enable database persistence:

```bash
# In .env:
SOA_DB_DSN=postgresql://user:pass@localhost/soa_db
SOA_STORAGE_MODE=db
SOA_DB_AUTO_INIT=true

# Initialize schema
python scripts/init_db.py
```

**Benefits**:
- Persistent run history
- Artifact versioning
- Metrics tracking
- Multi-user support

## Troubleshooting

### Common Issues

#### "CLI binary not found"

```bash
# Check if CLI is installed
which qwen  # or claude, gemini, etc.

# If not found, install your chosen CLI
# Then verify:
qwen --help
```

#### "Timeout during writer/synthesis"

```bash
# Increase timeout in .env
LLM_TIMEOUT=600

# Or reduce input size
MAX_PDF_CHARS=20000
```

#### "Low citation density"

```bash
# Increase repair iterations
python soa_cli.py --max-repair 5

# Check citation_map.json exists
ls db_outputs/soa/citation_map.json
```

#### "Papers not clustering well"

```bash
# Try auto-detection
python soa_cli.py --clusters auto

# Or adjust manually
python soa_cli.py --clusters 8  # More clusters
python soa_cli.py --clusters 4  # Fewer clusters
```

#### "PDF extraction truncated"

```bash
# Increase max chars
# In .env:
MAX_PDF_CHARS=50000

# Or enable semantic parsing
USE_SEMANTIC_PDF=true
```

#### "Semantic parsing failed"

```bash
# Check logs
tail -f logs/soa_pipeline_*.log

# System auto-falls back to text-only
# To force text-only mode:
USE_SEMANTIC_PDF=false
```

#### "Out of memory"

```bash
# Reduce parallel workers
MAX_WORKERS=5

# Reduce PDF chars
MAX_PDF_CHARS=20000

# Process in batches
# Split papers into smaller sets
```

### Debug Mode

```bash
# Enable detailed logging
export DEBUG=true
python soa_cli.py

# Check logs
tail -f logs/soa_pipeline_*.log

# Check intermediate artifacts
ls -la db_outputs/soa/
```

### Getting Help

1. **Check logs**: `logs/soa_pipeline_*.log`
2. **Review quality reports**: `db_outputs/soa/*.json`
3. **Verify configuration**: `.env`
4. **Check documentation**: `docs/`
5. **Open issue**: GitHub Issues

## Best Practices

### For Best Results

1. **Start Small**: Test with 10-20 papers first
2. **Define Theme Clearly**: Specific scope = better output
3. **Curate Papers**: Quality over quantity
4. **Review Incrementally**: Check rubric scores after each run
5. **Iterate**: Use `--max-repair` to improve quality
6. **Manual Polish**: Always review and refine output

### Workflow Tips

1. **Theme First**: Define theme before collecting papers
2. **Pilot Run**: Test with subset of papers
3. **Adjust Settings**: Tune based on pilot results
4. **Full Run**: Process all papers
5. **Quality Check**: Review rubric and hallucination reports
6. **Manual Review**: Read and polish output
7. **Iterate**: Re-run with adjustments if needed

### Time Management

- **Quick draft** (1 hour): 10 papers, default settings
- **Quality survey** (2-4 hours): 30-50 papers, `--max-repair 5`
- **Comprehensive survey** (4-8 hours): 100+ papers, tuned settings

## Next Steps

- **[Configuration Guide](CONFIGURATION.md)**: Detailed settings reference
- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)**: Technical architecture
- **[LangGraph Guide](LANGGRAPH_GUIDE.md)**: Pipeline internals
- **[Provider Setup](PROVIDER_SETUP.md)**: LLM CLI installation

---

**Ready to generate your survey?**

```bash
python soa_cli.py
```
