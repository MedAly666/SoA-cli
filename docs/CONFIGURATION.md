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
- **Default:** `300` (5 minutes)
- **Unit:** Seconds
- **Description:** Maximum time to wait for LLM API response
- **Adjust if:**
  - You experience timeouts → increase (e.g., `600`)
  - Papers are very short → decrease (e.g., `180`)

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
- **Guidelines:**
  - Short papers (10 pages): `20000`
  - Standard papers (20-30 pages): `30000`
  - Long papers (40+ pages): `40000-50000`
- **Trade-off:** 
  - Higher = More complete extraction, longer LLM processing time
  - Lower = Faster processing, may miss important content

#### `CLUSTER_COUNT`
- **Default:** `6`
- **Range:** `2` - `20`
- **Description:** Number of clusters for similarity-based paper grouping
- **Guidelines:**
  - <20 papers: `3-4` clusters
  - 20-50 papers: `4-6` clusters
  - 50-100 papers: `6-10` clusters
  - 100+ papers: `8-15` clusters
- **Note:** Too few clusters = overly broad categories; too many = fragmented insights

## Examples

### Using Different LLM Providers

#### Qwen (Default)
```env
LLM_PROVIDER=qwen
LLM_MODEL=
LLM_TEMPERATURE=0.3
LLM_TIMEOUT=300
MAX_WORKERS=10
MAX_PDF_CHARS=30000
CLUSTER_COUNT=6
```

#### Claude (Anthropic)
```env
LLM_PROVIDER=claude
LLM_MODEL=claude-sonnet-4.5
LLM_TEMPERATURE=0.3
LLM_TIMEOUT=300
MAX_WORKERS=10
MAX_PDF_CHARS=30000
CLUSTER_COUNT=6
```

#### Gemini (Google)
```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3-pro
LLM_TEMPERATURE=0.3
LLM_TIMEOUT=300
MAX_WORKERS=10
MAX_PDF_CHARS=30000
CLUSTER_COUNT=6
```

#### OpenAI (GPT)
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.2
LLM_TEMPERATURE=0.3
LLM_TIMEOUT=300
MAX_WORKERS=10
MAX_PDF_CHARS=30000
CLUSTER_COUNT=6
```

#### GLM (Zhipu AI)
```env
LLM_PROVIDER=glm
LLM_MODEL=glm-5
LLM_TEMPERATURE=0.2
LLM_TIMEOUT=300
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
LLM_TIMEOUT=180
MAX_WORKERS=4
MAX_PDF_CHARS=20000
CLUSTER_COUNT=4
```

### Balanced (Default)
```env
LLM_PROVIDER=qwen
LLM_MODEL=
LLM_TEMPERATURE=0.3
LLM_TIMEOUT=300
MAX_WORKERS=10
MAX_PDF_CHARS=30000
CLUSTER_COUNT=6
```

### Thorough Analysis (Large Dataset)
```env
LLM_PROVIDER=qwen
LLM_MODEL=
LLM_TEMPERATURE=0.2
LLM_TIMEOUT=600
MAX_WORKERS=12
MAX_PDF_CHARS=40000
CLUSTER_COUNT=10
```

### High Creativity (Exploratory)
```env
LLM_PROVIDER=claude
LLM_MODEL=claude-opus-4
LLM_TEMPERATURE=0.7
LLM_TIMEOUT=300
MAX_WORKERS=8
MAX_PDF_CHARS=30000
CLUSTER_COUNT=6
```

## Troubleshooting

### Timeout Errors
**Problem:** LLM calls timeout frequently

**Solutions:**
1. Increase `LLM_TIMEOUT` to `600` or higher
2. Decrease `MAX_PDF_CHARS` to `20000`
3. Reduce `MAX_WORKERS` to `4-6`

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
