# Paper Fetcher Feature - PRISMA-Compliant Automated Paper Discovery

## Overview

The Paper Fetcher feature automates systematic literature review paper discovery following PRISMA (Preferred Reporting Items for Systematic Reviews and Meta-Analyses) methodology. It searches multiple academic databases, applies quality filters, screens papers using LLM assistance, and generates comprehensive PRISMA reports.

## Key Features

✅ **PRISMA-Compliant Workflow**
- 4-stage systematic review process (Identification → Screening → Eligibility → Inclusion)
- Complete documentation with flow diagrams
- Exclusion tracking with reasons
- Search strategy documentation

✅ **Quality Control**
- Venue whitelisting (100+ reputable conferences and journals)
- Citation count filtering
- Publication year filtering
- Predatory publisher detection
- Peer-review verification

✅ **Multi-Database Search**
- Semantic Scholar (primary source)
- arXiv (preprints)
- DBLP (computer science bibliography)

✅ **LLM-Assisted Screening**
- Automatic search query generation from thematic contract
- Title/abstract screening against research scope
- Intelligent relevance filtering

## Installation & Setup

### 1. Configure Environment Variables

Copy `.env.example` to `.env` and configure paper fetcher settings:

```bash
# Paper Fetcher Configuration
PAPER_SOURCES=semantic_scholar,arxiv          # Data sources (comma-separated)
PAPER_MAX_RESULTS=50                         # Max papers per query
PAPER_MIN_YEAR=2015                          # Minimum publication year
PAPER_MIN_CITATIONS=10                       # Minimum citation count
PAPER_REQUIRE_WHITELIST=true                 # Require venue whitelist
```

### 2. Venue Whitelist

The venue whitelist is already configured in `config/venues.json` with 100+ trusted venues:

- **Conferences**: NeurIPS, ICML, ICLR, ACL, EMNLP, CVPR, ICCV, AAAI, etc.
- **Journals**: Nature, Science, JMLR, IEEE TPAMI, ACL Transactions, etc.
- **Domains**: ML, NLP, Computer Vision, Operations Research, AI, Medical, etc.

You can customize this file to add/remove venues for your domain.

## Usage Workflow

### Automatic Paper Search (New!)

When you run the main pipeline without any papers in the `papers/` directory, the system **automatically initiates paper search**:

```bash
python soa_cli.py
```

**What happens:**
1. System detects empty `papers/` directory
2. Automatically starts PRISMA paper search
3. Generates `paper_candidates.json`
4. Prompts you to review and approve candidates
5. Exits and waits for your action

**Then you:**
1. Review `paper_candidates.json`
2. Mark papers as `"status": "approved"`
3. Run: `python soa_cli.py --download-papers`
4. Run: `python soa_cli.py` (pipeline continues with downloaded papers)

### Manual Paper Search

You can also manually trigger paper search at any time:

```bash
python soa_cli.py --search-papers
```

### Step 1: Search for Papers

Search databases and generate candidate list:

```bash
python soa_cli.py --search-papers
```

**What happens:**
1. Loads thematic contract from `theme_input.json`
2. Generates search queries using LLM
3. Searches Semantic Scholar + arXiv
4. Removes duplicates (DOI/arXiv ID matching)
5. Screens titles/abstracts with LLM
6. Applies quality filters (venue whitelist, citations, year)
7. Saves candidates to `paper_candidates.json`

**Output:**
- `paper_candidates.json` - Eligible papers for review
- `artifacts/prisma/excluded_papers.json` - Excluded papers with reasons

### Step 2: Review Candidates

Open `paper_candidates.json` and review the eligible papers:

```json
{
  "search_metadata": {
    "theme": "Machine Learning for Healthcare",
    "search_date": "2024-01-15T10:30:00",
    "total_identified": 150,
    "duplicates_removed": 25,
    "screened": 125,
    "eligible": 40
  },
  "candidates": [
    {
      "title": "Deep Learning for Medical Diagnosis",
      "authors": ["Smith, J.", "Doe, A."],
      "year": 2023,
      "venue": "Nature Medicine",
      "abstract": "...",
      "doi": "10.1234/example",
      "citation_count": 50,
      "status": "approved",  // ← Change this to "approved" or "rejected"
      "screening_status": "passed",
      "eligibility_status": "eligible",
      ...
    }
  ]
}
```

**Review Actions:**
- Change `"status": "approved"` for papers you want to download
- Change `"status": "rejected"` for papers you want to exclude
- Add `"exclusion_reason": "Your reason here"` for rejected papers (optional)

### Step 3: Download Approved Papers

Download PDFs for approved papers:

```bash
python soa_cli.py --download-papers
```

**What happens:**
1. Reads `paper_candidates.json`
2. Filters papers with `status == "approved"`
3. Downloads PDFs to `papers/` directory
4. Updates candidates file with download status

**Output:**
- PDFs in `papers/` directory (ready for SOA pipeline)
- Updated `paper_candidates.json` with download status

### Step 4: Generate PRISMA Report

Generate comprehensive PRISMA documentation:

```bash
python soa_cli.py --prisma-report
```

**Output:**
- `artifacts/prisma/prisma_report.json` - Statistics, counts, and flow diagram (all-in-one)
- `artifacts/prisma/prisma_flow_diagram.md` - PRISMA flow diagram (standalone, also in JSON)
- `artifacts/prisma/excluded_papers.json` - Detailed exclusion log

### Step 5: Run SOA Pipeline

Now run the main pipeline with your downloaded papers:

```bash
python soa_cli.py --papers papers/
```

**IMPORTANT:** If you used the paper fetcher to collect papers (either automatically or via `--search-papers`), the final State of the Art document will **automatically include a PRISMA methodology section**! 

This section documents:
- Search strategy (databases, queries, date)
- PRISMA 4-stage selection process
- Quality assessment criteria
- PRISMA flow diagram
- Number of papers at each stage

This makes your literature review fully compliant with systematic review standards and publication-ready!

## PRISMA Methodology in Final Document

When papers are collected via the paper fetcher, the final State of the Art LaTeX document automatically includes a comprehensive methodology section following PRISMA guidelines:

### What's Included

**1. Systematic Search Methodology Section**
```latex
\subsection{Systematic Search Methodology}
This systematic literature review followed the PRISMA guidelines.

\subsubsection{Information Sources}
Semantic Scholar, arXiv (searched on 2024-01-15)

\subsubsection{Search Strategy}
Search queries were generated from the thematic contract using LLM-assisted process:
- Query 1: machine learning healthcare
- Query 2: deep learning medical diagnosis
...

\subsubsection{Selection Process}
Stage 1: Identification - 150 records identified
Stage 2: Screening - 125 records screened (25 duplicates removed, 45 excluded)
Stage 3: Eligibility - 80 records assessed (40 excluded for quality)
Stage 4: Included - 40 papers included in final review

\subsubsection{Quality Assessment}
- Publication venue reputation
- Citation impact (minimum 10 citations)
- Peer-review status
- Methodological rigor

\subsubsection{Data Extraction}
[Details about systematic extraction process]
```

**2. PRISMA Flow Diagram**

A visual TikZ diagram showing the 4-stage PRISMA process:

```
┌─────────────────────────┐
│  IDENTIFICATION         │
│  n=150 records          │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  Duplicates: n=25       │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐     ┌──────────────────┐
│  SCREENING              │────→│ Excluded: n=45   │
│  n=125 records          │     │ (Not relevant)   │
└───────────┬─────────────┘     └──────────────────┘
            ▼
┌─────────────────────────┐     ┌──────────────────┐
│  ELIGIBILITY            │────→│ Excluded: n=40   │
│  n=80 assessed          │     │ (Quality)        │
└───────────┬─────────────┘     └──────────────────┘
            ▼
┌─────────────────────────┐
│  INCLUDED               │
│  n=40 papers            │
└─────────────────────────┘
```

**3. Quality Criteria Documentation**

Detailed explanation of:
- Inclusion criteria (from thematic contract)
- Exclusion criteria (out-of-scope items)
- Quality filters (venue whitelist, citations, year)
- Predatory publisher screening

**4. Data Extraction Process**

Documentation of how data was extracted:
- Semantic PDF parsing
- Multi-agent review process
- Fact-grounding verification
- Hallucination prevention

### Benefits

✅ **Academic Credibility**: PRISMA is the gold standard for systematic reviews
✅ **Transparency**: Complete documentation of search and selection process
✅ **Reproducibility**: Other researchers can replicate your search
✅ **Publication-Ready**: Meets journal requirements for systematic reviews
✅ **Audit Trail**: Clear record of why papers were included/excluded

### Example Output

Your final `state_of_the_art.tex` will include:

```latex
\section{Introduction}
\subsection{Background and Motivation}
[Your thematic context]

\subsection{Review Scope and Methodology}
This review addresses the following research questions:
[From thematic contract]

The search was conducted following PRISMA guidelines...

\subsection{Systematic Search Methodology}
This systematic literature review followed the PRISMA (Preferred 
Reporting Items for Systematic Reviews and Meta-Analyses) guidelines.

\subsubsection{Information Sources}
The search was conducted on January 15, 2024, using the following 
academic databases:
\begin{itemize}
\item Semantic Scholar (comprehensive cross-domain database)
\item arXiv (preprint repository for computer science and related fields)
\end{itemize}

\subsubsection{Search Strategy}
Search queries were systematically generated from the thematic contract 
using an LLM-assisted process to ensure comprehensive coverage...

[Full PRISMA documentation continues]

\begin{figure}[htbp]
\centering
[TikZ PRISMA flow diagram]
\caption{PRISMA Flow Diagram showing the systematic selection process}
\label{fig:prisma_flow}
\end{figure}
```

This section appears **before** the main content sections, establishing the methodological rigor of your review upfront.

## Alternative Workflow: Automatic Download

For fully automated workflow (no manual review):

```bash
python soa_cli.py --search-and-download
```

This combines search + download in one command. **Not recommended** for rigorous systematic reviews.

## PRISMA Flow Diagram

The generated PRISMA flow diagram follows the standard format:

```
┌─────────────────────────────────────┐
│  IDENTIFICATION                     │
│  Records identified: n=150          │
│  (Semantic Scholar: 100, arXiv: 50) │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Duplicates removed: n=25           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  SCREENING                          │
│  Records screened: n=125            │
└──────┬──────────────────────────┬───┘
       │                          │
       │                   Records excluded: n=45
       │                   (Not relevant to theme)
       ▼
┌─────────────────────────────────────┐
│  ELIGIBILITY                        │
│  Full-text assessed: n=80           │
└──────┬──────────────────────────┬───┘
       │                          │
       │                   Records excluded: n=40
       │                   (Quality criteria)
       ▼
┌─────────────────────────────────────┐
│  INCLUDED                           │
│  Studies included: n=40             │
└─────────────────────────────────────┘
```

## Configuration Details

### Data Sources

**Semantic Scholar** (Recommended Primary Source)
- Free API with excellent metadata
- Citation counts, venue information
- Open access status
- 200M+ papers across all domains

**arXiv** (Preprints)
- Open access preprints
- Latest research (not yet peer-reviewed)
- PDF URLs always available
- Limited to: CS, Physics, Math, Stats, Bio

**DBLP** (Computer Science)
- Comprehensive CS bibliography
- High-quality metadata
- Conference/journal focus
- No PDF URLs (indexing only)

### Quality Filters

**Venue Whitelist** (`PAPER_REQUIRE_WHITELIST=true`)
- Only papers from `config/venues.json` are included
- Excludes: workshops, posters, predatory publishers
- Exceptions: Highly cited arXiv papers (50+ citations)

**Citation Filter** (`PAPER_MIN_CITATIONS=10`)
- Applied to papers older than 1 year
- Recent papers (last year) exempt
- Prevents low-impact papers

**Year Filter** (`PAPER_MIN_YEAR=2015`)
- Only papers from 2015 onwards
- Ensures recent research
- Adjustable for historical reviews

**Publication Type Filter**
- Excludes: workshops, posters, abstracts, demos
- Includes: conferences, journals, preprints

### Predatory Publisher Detection

Automatic detection and exclusion:

**Publisher Blacklist:**
- SCIRP (Scientific Research Publishing)
- OMICS Group
- Bentham Open (specific journals)
- WASET (fake conferences)

**Suspicious Patterns:**
- "international journal of advanced..."
- "proceedings of the international conference on advanced..."
- Multiple similar titles with different years

## Advanced Usage

### Custom Thematic Contract

The paper fetcher uses your `theme_input.json` to:
1. Generate relevant search queries
2. Screen papers for relevance
3. Check inclusion/exclusion criteria

Example `theme_input.json`:

```json
{
  "title": "Machine Learning for Healthcare",
  "research_goals": [
    "Survey deep learning applications in medical diagnosis",
    "Analyze clinical decision support systems using AI"
  ],
  "specific_constraints": [
    "Focus on supervised learning methods",
    "Include only peer-reviewed papers",
    "Minimum 10 citations"
  ],
  "what_to_exclude": [
    "Hardware optimization studies",
    "Robotics applications",
    "Non-clinical research"
  ]
}
```

### Customizing Venue Whitelist

Edit `config/venues.json` to add your domain-specific venues:

```json
{
  "conferences": {
    "your_domain": [
      "Your Conference 1",
      "Your Conference 2"
    ]
  },
  "journals": {
    "your_domain": [
      "Your Journal 1",
      "Your Journal 2"
    ]
  }
}
```

### Adjusting Search Parameters

For different review types:

**Comprehensive Survey** (200-500 papers):
```bash
PAPER_MAX_RESULTS=200
PAPER_MIN_YEAR=2010
PAPER_MIN_CITATIONS=5
PAPER_REQUIRE_WHITELIST=false
```

**Focused Review** (20-50 papers):
```bash
PAPER_MAX_RESULTS=50
PAPER_MIN_YEAR=2020
PAPER_MIN_CITATIONS=20
PAPER_REQUIRE_WHITELIST=true
```

**Cutting-Edge Survey** (recent papers only):
```bash
PAPER_MAX_RESULTS=100
PAPER_MIN_YEAR=2023
PAPER_MIN_CITATIONS=0
PAPER_SOURCES=arxiv,semantic_scholar
```

## Troubleshooting

### Issue: No papers found

**Possible causes:**
1. Search queries too specific
2. Venue whitelist too restrictive
3. Quality filters too strict

**Solutions:**
- Reduce `PAPER_MIN_CITATIONS`
- Increase `PAPER_MAX_RESULTS`
- Set `PAPER_REQUIRE_WHITELIST=false`
- Adjust thematic contract (broader scope)

### Issue: Too many irrelevant papers

**Solutions:**
- Tighten thematic contract constraints
- Add more exclusion criteria
- Increase `PAPER_MIN_CITATIONS`
- Set `PAPER_REQUIRE_WHITELIST=true`

### Issue: API rate limiting

**Semantic Scholar:** 100 requests/5 minutes
**Solution:** Wait 5 minutes and retry

**arXiv:** 3 seconds between requests (automatically handled)

### Issue: Download failures

**Possible causes:**
1. PDF not openly available
2. Network issues
3. Incorrect PDF URL

**Solutions:**
- Papers without open access PDFs will be skipped
- Manually download from publisher website
- Check paper URL in candidates file

## Output Files Reference

| File | Description | When Created |
|------|-------------|--------------|
| `paper_candidates.json` | Eligible papers for review | After `--search-papers` |
| `artifacts/prisma/prisma_report.json` | PRISMA statistics + flow diagram | After `--search-papers` or `--prisma-report` |
| `artifacts/prisma/prisma_flow_diagram.md` | PRISMA flow diagram (standalone) | After `--search-papers` or `--prisma-report` |
| `artifacts/prisma/excluded_papers.json` | Detailed exclusion log | After `--search-papers` |
| `papers/*.pdf` | Downloaded papers | After `--download-papers` |

## Example Complete Workflow

### Option 1: Automatic (Recommended)

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your LLM provider and paper fetcher settings

# 2. Create thematic contract
cat > theme_input.json << EOF
{
  "title": "Machine Learning for Healthcare",
  "research_goals": [
    "Survey deep learning in medical diagnosis"
  ],
  "specific_constraints": [
    "Peer-reviewed papers only"
  ],
  "what_to_exclude": [
    "Hardware optimization"
  ]
}
EOF

# 3. Run pipeline (automatically triggers paper search if no papers exist)
python soa_cli.py

# Output:
# ========================================
# No papers found in papers/
# AUTOMATIC PAPER SEARCH
# ========================================
# 
# STAGE 1: IDENTIFICATION
# [Search Queries Generated]: 5
#   1. machine learning healthcare
#   2. deep learning medical diagnosis
#   ...
# [Total Identified]: 130 records
#
# STAGE 2: SCREENING
# [Results]: ✓ Passed: 75, ✗ Excluded: 40
#
# STAGE 3: ELIGIBILITY  
# [Results]: ✓ Eligible: 45
#
# ✓ Candidates saved: paper_candidates.json
#
# 📋 Next steps:
#   1. Review candidates: paper_candidates.json
#   2. Edit 'status' field: 'approved' or 'rejected'
#   3. Download papers: python soa_cli.py --download-papers
#   4. Run pipeline again: python soa_cli.py

# 4. Review and edit candidates
nano paper_candidates.json
# Change status to "approved" for papers you want

# 5. Download approved papers
python soa_cli.py --download-papers

# 6. Run pipeline again to generate SOA
python soa_cli.py
```

### Option 2: Manual Control

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your LLM provider and paper fetcher settings

# 2. Create or check thematic contract
cat theme_input.json

# 3. Manually search for papers
python soa_cli.py --search-papers

# Output:
# ========================================
# STAGE 1: IDENTIFICATION
# [Search Queries Generated]: 5
#   1. machine learning healthcare
#   2. deep learning medical diagnosis
#   ...
# [Searching: SEMANTIC_SCHOLAR]
#   ✓ Found 85 records
# [Searching: ARXIV]
#   ✓ Found 45 records
# [Total Identified]: 130 records
#
# STAGE 2: SCREENING
# [Duplicates Removed]: 15
# [Title/Abstract Screening]: 115 records
# [Results]:
#   ✓ Passed: 75
#   ✗ Excluded: 40
#
# STAGE 3: ELIGIBILITY
# [Quality Assessment]: 75 papers
# [Results]:
#   ✓ Eligible: 45
#   ✗ Excluded: 30
#
# ✓ Candidates saved: paper_candidates.json

# 4. Review candidates
cat paper_candidates.json
# Edit status field for each paper

# 5. Download approved papers
python soa_cli.py --download-papers

# Output:
# [Download] Found 40 approved papers
# [1/40] ✓ Deep_Learning_for_Medical_Diagnosis_2023.pdf
# [2/40] ✓ Clinical_Decision_Support_with_AI_2022.pdf
# ...
# ✓ Successfully downloaded 38 papers to papers/
# ✓ Candidates file updated

# 6. Generate PRISMA report
python soa_cli.py --prisma-report

# 7. Run main SOA pipeline
python soa_cli.py --papers papers/
```

## Best Practices

### 1. Start Conservative
- Use strict quality filters initially
- Review first batch manually
- Adjust filters based on results

### 2. Document Search Strategy
- Save your search queries
- Document inclusion/exclusion criteria
- Keep PRISMA reports for reproducibility

### 3. Iterative Refinement
- Run multiple searches with different parameters
- Merge results (deduplication handles this)
- Track why papers were excluded

### 4. Manual Review Recommended
- Always review candidates before downloading
- Don't rely solely on LLM screening
- Use domain expertise to filter edge cases

### 5. Venue Whitelist Maintenance
- Update `config/venues.json` annually
- Add new conferences/journals from your domain
- Remove defunct venues

## Credits & Methodology

This implementation follows:
- PRISMA 2020 Guidelines
- Cochrane Handbook for Systematic Reviews
- Best practices from systematic literature review methodology

Quality control inspired by:
- Beall's List (predatory publishers)
- CORE Rankings (conference quality)
- SCImago Journal Rank (journal quality)

## License

Part of SOA-CLI. See main repository for license information.
