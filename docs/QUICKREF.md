# Quick Reference Card - SOA-CLI with Thematic Priming

## Initial Setup (One Time)

```bash
# 1. Setup dependencies (creates .venv)
./setup.sh

# 2. Activate virtual environment
source .venv/bin/activate
# OR use convenience script:
source activate.sh

# 3. Verify installation
python scripts/check.py
```

**Note**: Always activate the virtual environment before running:
```bash
source .venv/bin/activate  # OR: source activate.sh
```

## Define Research Scope (CRITICAL FIRST STEP)

```bash
# Create theme template
python -m src.theme_builder template

# Edit with YOUR research focus
nano theme_input.json

# Build thematic contract
python -m src.theme_builder build

# Verify contract
python -m src.theme_builder show
```

## Add Papers

```bash
cp /path/to/papers/*.pdf papers/
```

## Run Pipeline

```bash
python soa_cli.py
```

**Time**: 25-40 minutes for 43 papers

## Output Location

```
artifacts/soa/state_of_the_art_final.tex
```

---

## Thematic Contract Structure

```json
{
  "global_theme": "Your focused research theme",
  "core_questions": ["Q1", "Q2", "Q3"],
  "in_scope": ["topic1", "method1", ...],
  "out_of_scope": ["exclude1", "exclude2", ...],
  "preferred_methods": ["method1", "method2"],
  "evaluation_focus": ["metric1", "metric2"]
}
```

## Key Commands

```bash
# Theme management
python -m src.theme_builder template   # Create template
python -m src.theme_builder build      # Build contract
python -m src.theme_builder show       # View contract

# Pipeline
python soa_cli.py                       # Full pipeline

# Verification
python scripts/check.py                 # Pre-flight check
cat THEMATIC_CONTRACT.json              # View contract
```

## Pipeline Stages

```
Stage 0: Thematic Contract     ← Define scope
Stage 1: Reader                ← Parse PDFs
Stage 2: Extractor (filtered)  ← Extract relevant facts
Stage 3: Critic (focused)      ← Assess quality
Stage 4: Clustering (filtered) ← Group by similarity
Stage 5: Synthesis (driven)    ← Address core questions
Stage 6: Writer (bounded)      ← Generate SoA
Stage 7: Verify & Repair       ← Fix hallucinations
```

## What Gets Filtered?

- **Papers**: 30-50% filtered before clustering
- **Extraction**: Only theme-relevant facts
- **Synthesis**: Focused on core questions
- **Writing**: Bounded by exclusions

## Common Issues

### Contract Missing

```
[!] Thematic contract requires user input
```

**Fix**: Run `python -m src.theme_builder build`

### Too Many Papers Filtered

```
[+] Thematic filter: 12/43 papers relevant
```

**Fix**: Broaden in_scope in theme_input.json, rebuild contract

### Theme Violations in Output

```
[!] Warning: 3 theme violations detected
```

**Fix**: Review out_of_scope terms, may need adjustment

## Best Practices

1. **Be specific** in research goals (not generic)
2. **Explicitly exclude** tangential topics
3. **Define 3-5 core questions** that drive synthesis
4. **Review contract** before running pipeline
5. **Track filtering metrics** (how many papers kept)

## Directory Structure

```
soa-cli/
├── theme_input.json          ← YOUR research scope
├── THEMATIC_CONTRACT.json    ← Generated contract
├── papers/                   ← Your PDFs
├── artifacts/
│   ├── extracted_filtered/   ← Theme-relevant papers
│   └── soa/                  ← Final output
└── vector_db/               ← Filtered embeddings
```

## Performance

### Without Thematic Priming
- Process all 43 papers
- Extract everything
- 40-50 minutes
- Unfocused SoA

### With Thematic Priming
- Filter to ~30 relevant papers
- Extract only relevant facts
- 25-35 minutes
- Laser-focused SoA

## Verification Checklist

- [ ] theme_input.json created and edited
- [ ] THEMATIC_CONTRACT.json exists
- [ ] Contract has 3+ core questions
- [ ] in_scope is specific (not broad)
- [ ] out_of_scope explicitly defined
- [ ] Papers added to papers/
- [ ] ./check.py passes
- [ ] Run orchestrator.py

## Academic Defense

**Question**: "How did you ensure focused analysis?"

**Answer**: "We defined a global thematic contract specifying in-scope and out-of-scope content, core research questions, and methodological preferences. This contract was enforced across all agents, with papers filtered for thematic relevance before embedding (n=33/43 relevant) and synthesis constrained to address only the defined core questions."

---

For detailed guidance, see:
- [THEMATIC_PRIMING.md](THEMATIC_PRIMING.md) - Complete guide
- [USAGE.md](USAGE.md) - Step-by-step workflow
- [README.md](README.md) - Overview
