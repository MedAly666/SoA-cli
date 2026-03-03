# Configuration Guide

## Overview

SOA-CLI uses environment variables for configuration management. All configuration is stored in the `.env` file, which is gitignored to prevent accidentally committing sensitive settings.

## Setup

1. **Copy the template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your preferences:**
   ```bash
   nano .env  # or use your preferred editor
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration Variables

### LLM Configuration

#### `LLM_PROVIDER`
- **Default:** `qwen`
- **Description:** Choose which CLI agent to use for LLM interactions
- **Supported Providers:**
  - `qwen` - Qwen CLI (default)
  - `claude` - Claude CLI (Anthropic)
  - `gemini` - Gemini CLI (Google)
  - `openai` - OpenAI CLI
  - `kilo` - Kilo CLI
  - `glm` - GLM CLI (Zhipu AI)
- **Setup Requirements:** Install the chosen CLI tool:
  ```bash
  # Example installations
  pip install qwen-cli        # For Qwen
  npm install -g @anthropic/claude-cli  # For Claude
  pip install google-generativeai      # For Gemini
  pip install openai          # For OpenAI
  ```

#### `LLM_MODEL`
- **Default:** Empty (uses provider's default model)
- **Description:** Specify a specific LLM model within the chosen provider
- **Examples by Provider:**
  
  **Qwen:**
  - Leave empty for default
  - `qwen-coder` - Coding-optimized model
  - `qwen-32b` - Larger model
  
  **Claude (Anthropic):**
  - `claude-sonnet-4.5` - Balanced performance
  - `claude-opus-4` - Most capable model
  - `claude-haiku-4` - Fastest model
  
  **Gemini (Google):**
  - `gemini-3-pro` - Advanced reasoning
  - `gemini-2.5-flash` - Fast responses
  - `gemini-ultra-2` - Most capable
  
  **OpenAI:**
  - `gpt-5.2` - Latest GPT model
  - `gpt-4.5-turbo` - Fast GPT-4
  - `o1-mini` - Reasoning model
  
  **GLM (Zhipu AI):**
  - `glm-5` - Latest model
  - `glm-4-plus` - Enhanced model

#### `LLM_TEMPERATURE`
- **Default:** `0.3`
- **Range:** `0.0` - `1.0`
- **Description:** Controls randomness in text generation
  - `0.0` = Deterministic, reproducible output
  - `0.3` = Slightly creative (recommended for academic writing)
  - `0.7` = More creative
  - `1.0` = Maximum creativity
- **Recommended:** `0.2` - `0.5` for academic State of the Art generation

#### `LLM_TIMEOUT`
- **Default:** `120` (2 minutes)
- **Unit:** Seconds
- **Description:** Maximum time to wait for LLM API response per attempt
- **Retry Behavior:** System retries up to 3 times with exponential backoff (2s, 4s, 8s delays)
- **Adjust if:**
  - You experience timeouts → increase (e.g., `300` for 5 minutes, `600` for 10 minutes)
  - Papers are very short → decrease (e.g., `60`)
  - Large synthesis tasks → increase to `300-600`
- **Note:** Total wait time = timeout × 3 attempts (e.g., 120s × 3 = up to 6 minutes)

#### `CITATION_STYLE`
- **Default:** `ieee`
- **Options:** `ieee`, `apa`, `chicago`, `harvard`
- **Description:** Academic citation style for the State of the Art document
- **Style Details:**
  
  **IEEE (Institute of Electrical and Electronics Engineers):**
  - Numeric citations: `[1]`, `[2]`, `[3]`
  - Sequential numbering in order of appearance
  - Format: `[1] A. Smith, "Title," Journal, vol. 1, no. 2, pp. 10-20, 2020.`
  - **Recommended for:** Computer Science, Engineering, Technical papers
  
  **APA (American Psychological Association):**
  - Author-date citations: `(Smith, 2020)`, `(Smith & Jones, 2020)`
  - Ampersand (&) in parentheses, "and" in text
  - Format: `Smith, A., & Jones, B. (2020). Title. Journal, 1(2), 10-20.`
  - **Recommended for:** Psychology, Social Sciences, Education
  
  **Chicago (Author-Date System):**
  - Author-date with full names: `(John Smith and Jane Doe 2020)`
  - Format: `Smith, John, and Jane Doe. 2020. "Title." Journal 1 (2): 10-20.`
  - **Recommended for:** Humanities, History, Arts
  
  **Harvard:**
  - Author-date with surnames: `(Smith and Doe 2020)`
  - "and" connector (no ampersand)
  - Format: `Smith, A. and Doe, J. (2020) 'Title', Journal, 1(2), pp. 10-20.`
  - **Recommended for:** UK universities, Business, Law

- **Example:**
  ```env
  # For Computer Science papers
  CITATION_STYLE=ieee
  
  # For Psychology papers
  CITATION_STYLE=apa
  ```

### Pipeline Configuration

#### `MAX_WORKERS`
- **Default:** `10`
- **Range:** `1` - `20`
- **Description:** Number of parallel workers for concurrent paper processing
- **Guidelines:**
  - Set to number of CPU cores for optimal performance
  - 4-core CPU: `MAX_WORKERS=4`
  - 8-core CPU: `MAX_WORKERS=8`
  - 12+ core CPU: `MAX_WORKERS=10-12`
- **Note:** More workers = faster processing but higher memory usage

#### `MAX_PDF_CHARS`
- **Default:** `30000`
- **Unit:** Characters
- **Description:** Maximum characters to extract from each PDF
- **Equivalent:** ~15-20 pages (includes abstract, intro, methods, results)
- **Smart Truncation:** When PDFs exceed this limit, the system:
  - Scores pages by importance (abstract, intro, methods, results, conclusion = +10)
  - Deprioritizes references, acknowledgements, appendices (-50)
  - Prefers early pages (pages 1-5 = +5 boost)
  - Prints yellow warning with truncation statistics
  - Stores truncation metadata in artifacts
- **Guidelines:**
  - Short papers (10 pages): `20000`
  - Standard papers (20-30 pages): `30000` (default)
  - Long papers (40+ pages): `40000-50000`
- **Trade-off:** 
  - Higher = More complete extraction, longer LLM processing time
  - Lower = Faster processing, may miss important content
- **Warning Display:**
  ```
  ⚠️  [paper.pdf] truncated at 30,000 chars
      Full length: 75,000 chars
      Lost: 45,000 chars (60.0%)
      Appendices/References may be excluded
  ```

#### `CLUSTER_COUNT`
- **Default:** `6` (or `auto` via CLI flag)
- **Range:** `2` - `20`, or `auto`
- **Description:** Number of clusters for similarity-based paper grouping
- **Auto-Detection:** Use `--clusters auto` CLI flag to automatically detect optimal cluster count
  - Uses silhouette analysis to test k from 2 to 10
  - Selects k with highest silhouette score (best cluster separation)
  - Logs all scores and optimal k selection
  - Handles edge cases (< 3 papers)
- **Manual Guidelines:**
  - <20 papers: `3-4` clusters
  - 20-50 papers: `4-6` clusters
  - 50-100 papers: `6-10` clusters
  - 100+ papers: `8-15` clusters
- **Note:** Too few clusters = overly broad categories; too many = fragmented insights
- **Example:**
  ```bash
  # Auto-detect optimal cluster count (recommended)
  python soa_cli.py --clusters auto
  
  # Manual override
  python soa_cli.py --clusters 5
  ```
- **Silhouette Analysis Output:**
  ```
  Testing cluster counts from 2 to 8...
    k=2: silhouette score = 0.45
    k=3: silhouette score = 0.52  ← Optimal
    k=4: silhouette score = 0.48
  Optimal cluster count: 3 (silhouette score: 0.52)
  ```

### CLI Flags

In addition to environment variables, SOA-CLI supports command-line flags for runtime configuration:

#### `--clusters`
- **Options:** `auto` or integer (2-20)
- **Default:** `6`
- **Description:** Override cluster count from command line
- **Examples:**
  ```bash
  # Auto-detect optimal cluster count
  python soa_cli.py --clusters auto
  
  # Manually set to 5 clusters
  python soa_cli.py --clusters 5
  ```

#### `--format`
- **Options:** `latex`, `markdown`, `docx`, `all`
- **Default:** `latex`
- **Description:** Output format for State of the Art document
- **Formats:**
  - `latex`: LaTeX source file (`.tex`) - default
  - `markdown`: Markdown file (`.md`) - converted from LaTeX
  - `docx`: Microsoft Word document (`.docx`) - with styled formatting
  - `all`: Export all three formats simultaneously
- **Examples:**
  ```bash
  # Export as Markdown
  python soa_cli.py --format markdown
  
  # Export as Word document
  python soa_cli.py --format docx
  
  # Export all formats at once
  python soa_cli.py --format all
  ```
- **Output Files:**
  - LaTeX: `state_of_the_art.tex`
  - Markdown: `state_of_the_art.md`
  - Word: `state_of_the_art.docx`
- **Word Formatting:**
  - Section headers: Heading 1 style
  - Subsection headers: Heading 2 style
  - Bold text: **Bold** formatting
  - Italic text: *Italic* formatting
  - Citations: Blue colored text

#### Other Flags
- `--papers`: Specify custom papers directory (default: `papers/`)
- `--max-repair`: Set maximum repair iterations (default: 3)
- `--skip-reader`: Skip PDF extraction stage
- `--skip-download`: Skip paper download stage
- `--resume`: Resume from checkpoint
- `--thread-id`: Specify checkpoint thread ID

#### Combined Usage
```bash
# Complete example: auto-cluster, export all formats, APA citations
CITATION_STYLE=apa python soa_cli.py --clusters auto --format all

# Fast processing with custom papers directory
python soa_cli.py --papers /path/to/pdfs --clusters 4 --format markdown
```

## Examples

### Using Different LLM Providers

#### Qwen (Default)
```env
LLM_PROVIDER=qwen
LLM_MODEL=
LLM_TEMPERATURE=0.3
LLM_TIMEOUT=120
CITATION_STYLE=ieee
MAX_WORKERS=10
MAX_PDF_CHARS=30000
CLUSTER_COUNT=6
```

#### Claude (Anthropic)
```env
LLM_PROVIDER=claude
LLM_MODEL=claude-sonnet-4.5
LLM_TEMPERATURE=0.3
LLM_TIMEOUT=120
CITATION_STYLE=ieee
MAX_WORKERS=10
MAX_PDF_CHARS=30000
CLUSTER_COUNT=6
```

#### Gemini (Google)
```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3-pro
LLM_TEMPERATURE=0.3
LLM_TIMEOUT=120
CITATION_STYLE=ieee
MAX_WORKERS=10
MAX_PDF_CHARS=30000
CLUSTER_COUNT=6
```

#### OpenAI (GPT)
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.2
LLM_TEMPERATURE=0.3
LLM_TIMEOUT=120
CITATION_STYLE=ieee
MAX_WORKERS=10
MAX_PDF_CHARS=30000
CLUSTER_COUNT=6
```

#### GLM (Zhipu AI)
```env
LLM_PROVIDER=glm
LLM_MODEL=glm-5
LLM_TEMPERATURE=0.2
LLM_TIMEOUT=120
CITATION_STYLE=ieee
MAX_WORKERS=10
MAX_PDF_CHARS=30000
CLUSTER_COUNT=6
```

### Performance-Optimized Configurations

### Fast Processing (Small Dataset)
```env
LLM_PROVIDER=qwen
LLM_MODEL=
LLM_TEMPERATURE=0.3
LLM_TIMEOUT=60
CITATION_STYLE=ieee
MAX_WORKERS=4
MAX_PDF_CHARS=20000
CLUSTER_COUNT=4
```

### Balanced (Default)
```env
LLM_PROVIDER=qwen
LLM_MODEL=
LLM_TEMPERATURE=0.3
LLM_TIMEOUT=120
CITATION_STYLE=ieee
MAX_WORKERS=10
MAX_PDF_CHARS=30000
CLUSTER_COUNT=6
```

### Thorough Analysis (Large Dataset)
```env
LLM_PROVIDER=qwen
LLM_MODEL=
LLM_TEMPERATURE=0.2
LLM_TIMEOUT=300
CITATION_STYLE=ieee
MAX_WORKERS=12
MAX_PDF_CHARS=40000
CLUSTER_COUNT=10
```

### High Creativity (Exploratory)
```env
LLM_PROVIDER=claude
LLM_MODEL=claude-opus-4
LLM_TEMPERATURE=0.7
LLM_TIMEOUT=120
CITATION_STYLE=apa
MAX_WORKERS=8
MAX_PDF_CHARS=30000
CLUSTER_COUNT=6
```

## Troubleshooting

### Timeout Errors
**Problem:** LLM calls timeout frequently

**Understanding Retry Behavior:**
- System automatically retries failed LLM calls up to 3 times
- Exponential backoff delays: 2s, 4s, 8s between attempts
- Total possible wait time = `LLM_TIMEOUT × 3` (e.g., 120s × 3 = 6 minutes)
- Failed calls return `__LLM_FAILURE__` instead of crashing the pipeline

**Solutions:**
1. Increase `LLM_TIMEOUT` to `300` (5 minutes) or `600` (10 minutes)
2. Decrease `MAX_PDF_CHARS` to `20000` (reduces input size)
3. Reduce `MAX_WORKERS` to `4-6` (less concurrent load)
4. Check provider CLI is working: `echo "test" | qwen -y` (or your provider)
5. Verify API keys are set correctly (if required by provider)

### Memory Issues
**Problem:** System runs out of memory

**Solutions:**
1. Reduce `MAX_WORKERS` to `4` or lower
2. Reduce `MAX_PDF_CHARS` to `20000`
3. Process papers in batches

### Poor Clustering
**Problem:** Papers grouped incorrectly

**Solutions:**
1. Adjust `CLUSTER_COUNT`:
   - Increase if papers are too mixed
   - Decrease if clusters are too granular
2. Check thematic contract alignment

### Inconsistent Output
**Problem:** Results vary between runs

**Solutions:**
1. Lower `LLM_TEMPERATURE` to `0.1` or `0.2`
2. Fix random seeds in code (advanced)

### Provider Not Found
**Problem:** Error: "Unsupported LLM provider"

**Solutions:**
1. Check `LLM_PROVIDER` is set correctly in `.env`
2. Verify supported providers: `qwen`, `claude`, `gemini`, `openai`, `kilo`, `glm`
3. Ensure provider CLI is installed:
   ```bash
   # Check if CLI is available
   which qwen      # or claude, gemini, etc.
   
   # Install if missing
   pip install qwen-cli  # or appropriate installation method
   ```

### Provider Command Fails
**Problem:** Model errors or authentication failures

**Solutions:**
1. **Authentication:** Ensure API keys are configured
   ```bash
   # Claude
   export ANTHROPIC_API_KEY=your_key
   
   # OpenAI
   export OPENAI_API_KEY=your_key
   
   # Gemini
   export GOOGLE_API_KEY=your_key
   ```

2. **Model Availability:** Verify model name is correct for provider
   - Check provider documentation for available models
   - Leave `LLM_MODEL` empty to use default

3. **CLI Installation:** Verify CLI tool is properly installed
   ```bash
   # Test CLI directly
   echo "Hello" | qwen -y
   ```

### Temperature Not Working
**Problem:** Temperature setting has no effect

**Solutions:**
- **Note:** Qwen, Gemini, and Kilo don't support temperature in their CLI
- Switch to a provider that supports it (`claude`, `openai`, `glm`)
- Or modify the code to use provider's API directly

## Advanced Configuration

### Adding Custom Providers

To add support for a new LLM provider:

1. **Add provider configuration in `soa_cli.py`:**
   ```python
   LLM_PROVIDERS = {
       # ... existing providers ...
       'your_provider': {
           'command': 'your-cli-command',
           'model_flag': '-m',  # or appropriate flag
           'auto_yes': [],  # flags for auto-confirmation
           'supports_temperature': True,
           'temperature_flag': '--temperature',
           'supports_system_prompt': True,
           'input_method': 'stdin',
           'output_method': 'stdout'
       }
   }
   ```

2. **Update `.env.example`** with documentation for the new provider

3. **Test:** Set `LLM_PROVIDER=your_provider` in `.env` and run

### Adding Custom Configuration Variables

To add custom configuration variables:

1. **Add to `.env`:**
   ```env
   MY_CUSTOM_SETTING=value
   ```

2. **Load in `soa_cli.py`:**
   ```python
   MY_CUSTOM_SETTING = os.getenv('MY_CUSTOM_SETTING', 'default_value')
   ```

3. **Update `.env.example`** with documentation

## Security Notes

- **Never commit `.env`** to version control (already in `.gitignore`)
- Store sensitive API keys or credentials in `.env`
- Share `.env.example` as template for team members
- Use different `.env` files for development/production environments
