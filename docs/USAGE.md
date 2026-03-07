# Usage Guide - SOA-CLI

## Initial Setup (One Time)

```bash
# 1. Run setup script (creates .venv, installs dependencies)
./setup.sh

# 2. Activate virtual environment (ALWAYS REQUIRED)
source .venv/bin/activate

# 3. Verify installation
python3 test_langgraph.py

# 4. Add your papers
cp /path/to/your/papers/*.pdf papers/
```

**Important**: Always activate the virtual environment before running any commands:
```bash
source .venv/bin/activate
```

## Running the Pipeline

### Complete Pipeline (Recommended)

```bash
python3 soa_cli.py
```

This will:
- Process all PDFs with LangGraph orchestration
- Generate State of the Art with automatic checkpointing
- Detect and fix hallucinations (up to 3 repair iterations)
- Output: `STATE_OF_THE_ART.tex`

**Time**: 10-15 minutes for 10 papers (scales with paper count)

---

## Advanced Options

### Custom Papers Directory

```bash
python3 soa_cli.py --papers /path/to/pdfs
```

### Adjust Repair Iterations

```bash
# Default is 3, increase for more repair attempts
python3 soa_cli.py --max-repair 5
```

### Resume from Checkpoint

```bash
# If pipeline was interrupted, resume where it left off
python3 soa_cli.py --resume --thread-id my-session-id
```

### Custom Thread ID

```bash
# Use different thread IDs for parallel experiments
python3 soa_cli.py --thread-id experiment-1
```

---

## Testing with Subset

To test with just a few papers:

```bash
# 1. Create test directory
mkdir papers_test
cp papers/P01.pdf papers/P02.pdf papers/P03.pdf papers_test/

# 2. Run with custom directory
python3 soa_cli.py --papers papers_test

# Output will be in STATE_OF_THE_ART.tex
```

---

## Checking Progress

All intermediate outputs are saved in `artifacts/`:

```bash
# Check extraction progress
ls artifacts/extracted/*.json | wc -l

# Check current state
cat artifacts/states/final_state.json | jq '.pipeline_stage'

# Check clustering
cat artifacts/clusters/preclusters.json

# Check synthesis
cat artifacts/synthesis/synthesis.json

# Check for hallucinations
cat artifacts/soa/hallucination_report.json
```

---

## Troubleshooting

### Pipeline Stops at Reader Stage

**Problem**: PDF parsing fails

**Solution**:
```bash
# Install PDF processing library
pip install PyMuPDF
```

### "Qwen failed" Error

**Problem**: Qwen CLI not working

**Check**:
```bash
which qwen
qwen --version
```

**Solution**: Ensure Qwen is installed and configured

### High Hallucination Count

**Problem**: Many violations detected

**Solutions**:
1. Check `artifacts/soa/hallucination_report.json` for details
2. Review extracted data quality: `artifacts/extracted/P*.json`
3. May need more papers or better quality papers
4. System will auto-repair up to 3 iterations

### Papers Not Found

**Problem**: `[!] No PDF files found in papers/ directory`

**Solution**:
```bash
# Check papers directory
ls -la papers/

# Verify PDF extensions
ls papers/*.pdf

# Add papers
cp /path/to/pdfs/*.pdf papers/
```

---

## Configuration

### Adjust Number of Clusters

Edit `orchestrator.py`, line ~210:

```python
cluster_file = run_clustering(extracted, critics, n_clusters=8)  # Change 6 to 8
```

### Change Model or Temperature

Edit `orchestrator.py`, lines 20-21:

```python
MODEL = "qwen3.5-32b"           # Change model
TEMPERATURE = 0.2               # Lower = more conservative
```

### Adjust Parallelism

Edit `orchestrator.py`, line 22:

```python
MAX_WORKERS = 6  # Increase/decrease based on your machine
```

---

## Output Files

### Primary Output

- **artifacts/soa/state_of_the_art_final.tex**
  - Your verified, repaired State of the Art
  - Ready to include in your thesis

### Intermediate Artifacts (For Review)

- **artifacts/extracted/PX.json** - Facts from each paper
- **artifacts/critic/PX.json** - Quality assessment
- **artifacts/clusters/clusters.json** - Paper groupings
- **artifacts/synthesis/synthesis.json** - Cross-paper insights

### Reports

- **artifacts/soa/hallucination_report.json** - Verification results
- **artifacts/soa/repair_failure.json** - Issues that couldn't be fixed (if any)

---

## Integration with Thesis

### LaTeX

```latex
\input{artifacts/soa/state_of_the_art_final.tex}
```

### Word

1. Compile LaTeX to PDF
2. Copy text from PDF
3. Or use pandoc: `pandoc state_of_the_art_final.tex -o soa.docx`

---

## Rerunning Pipeline

Safe to rerun - artifacts are overwritten:

```bash
# Clean previous run (optional)
rm -rf artifacts/* vector_db/*

# Run again
python soa_cli.py
```

---

## Paper Naming Convention

Recommended format:

```
papers/
├── P01_AuthorYear_ShortTitle.pdf
├── P02_AuthorYear_ShortTitle.pdf
├── ...
└── P43_AuthorYear_ShortTitle.pdf
```

The system uses file name stem as paper ID (e.g., P01, P02).

---

## Citation in Thesis

Example methodology section:

> "The State of the Art was generated using a multi-agent pipeline with 
> mathematical similarity clustering and iterative hallucination repair. 
> The system processes 43 papers through six specialized agents: Reader, 
> Extractor, Critic, Cluster, Synthesis, and Writer. A four-layer 
> verification system ensures all claims are grounded in extracted facts 
> with automatic repair of unsupported statements."

---

## Performance Tips

### Speed Up Processing

1. **Reduce temperature** (faster, more deterministic):
   ```python
   TEMPERATURE = 0.1
   ```

2. **Increase parallelism** (if you have CPU/GPU):
   ```python
   MAX_WORKERS = 12
   ```

3. **Use smaller model** (less accurate):
   ```python
   MODEL = "qwen2.5-7b"
   ```

### Improve Quality

1. **Increase temperature slightly** (more creative):
   ```python
   TEMPERATURE = 0.3
   ```

2. **Adjust cluster count** (more specific themes):
   ```python
   n_clusters = 8
   ```

3. **Review and edit prompts** in `prompts/` directory

---

## Support

Issues to check first:

1. Run `./check.py` to verify setup
2. Check `artifacts/soa/hallucination_report.json`
3. Review individual paper extractions in `artifacts/extracted/`
4. Ensure Qwen CLI is working: `qwen run --help`

---

## Next Steps After Generation

1. **Read the output** - Don't submit without reading
2. **Verify citations** - Check key papers manually
3. **Add your interpretation** - Add your perspective
4. **Integrate with your work** - Show where you fit in
5. **Get supervisor feedback** - This is still a draft

---

**Remember**: This system generates a **high-quality draft**, not a final submission. Human review and refinement are essential.
