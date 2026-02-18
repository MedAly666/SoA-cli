# LLM Provider Setup Guide

SOA-CLI supports multiple LLM providers through a unified interface. This guide explains how to set up and use different providers.

## Quick Start

1. **Choose your provider** and install the CLI
2. **Configure authentication** (API keys, etc.)
3. **Update `.env`** with provider and model settings
4. **Run SOA-CLI** - it works the same regardless of provider

---

## Supported Providers

### 1. Qwen (Default)

**Provider:** Alibaba Cloud Qwen models

#### Installation
```bash
# Install Qwen CLI
pip install qwen-cli
```

#### Configuration
```env
LLM_PROVIDER=qwen
LLM_MODEL=              # Leave empty for default, or specify: qwen-coder, qwen-32b
LLM_TEMPERATURE=0.3
```

#### Authentication
```bash
# Set up Qwen API key
export QWEN_API_KEY=your_api_key_here
```

#### Available Models
- Default (when `LLM_MODEL` is empty)
- `qwen-coder` - Optimized for coding tasks
- `qwen-32b` - Larger model with enhanced capabilities
- `qwen-72b` - Most capable model

---

### 2. Claude (Anthropic)

**Provider:** Anthropic Claude models

#### Installation
```bash
# Install Claude CLI
npm install -g @anthropic/claude-cli

# Or using pip (if available)
pip install anthropic-cli
```

#### Configuration
```env
LLM_PROVIDER=claude
LLM_MODEL=claude-sonnet-4.5   # Recommended for balanced performance
LLM_TEMPERATURE=0.3
```

#### Authentication
```bash
# Set up Anthropic API key
export ANTHROPIC_API_KEY=your_api_key_here

# Or configure via CLI
claude configure
```

#### Available Models
- `claude-sonnet-4.5` - Balanced performance and speed (recommended)
- `claude-opus-4` - Most capable, best for complex tasks
- `claude-haiku-4` - Fastest, good for simple tasks
- `claude-3.5-sonnet` - Previous generation, still very capable

#### Best For
- Academic writing (excellent at following complex instructions)
- Long-context understanding (200K+ token context)
- Structured output (great JSON compliance)

---

### 3. Gemini (Google)

**Provider:** Google Gemini models

#### Installation
```bash
# Install Google Generative AI SDK
pip install google-generativeai

# Or use gcloud CLI
gcloud components install gemini-cli
```

#### Configuration
```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3-pro       # Latest Pro model
LLM_TEMPERATURE=0.3
```

#### Authentication
```bash
# Set up Google API key
export GOOGLE_API_KEY=your_api_key_here

# Or use gcloud authentication
gcloud auth application-default login
```

#### Available Models
- `gemini-3-pro` - Latest, most capable (if available)
- `gemini-2.5-flash` - Fast inference, good quality
- `gemini-ultra-2` - Most capable for complex reasoning
- `gemini-1.5-pro` - Previous generation, very capable
- `gemini-1.5-flash` - Fast and efficient

#### Best For
- Multimodal tasks (can handle images in PDFs)
- Fast inference with Flash models
- Cost-effective with generous free tier

---

### 4. OpenAI (GPT)

**Provider:** OpenAI GPT models

#### Installation
```bash
# Install OpenAI CLI
pip install openai

# Or use official CLI
brew install openai  # macOS
```

#### Configuration
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.2           # Latest GPT model
LLM_TEMPERATURE=0.3
```

#### Authentication
```bash
# Set up OpenAI API key
export OPENAI_API_KEY=your_api_key_here

# Or configure via CLI
openai configure
```

#### Available Models
- `gpt-5.2` - Latest GPT model (if available)
- `gpt-4.5-turbo` - Fast GPT-4 with optimizations
- `gpt-4-turbo` - Previous generation, very capable
- `o1-mini` - Reasoning-optimized model
- `o1-preview` - Advanced reasoning (slower, more capable)

#### Best For
- Cutting-edge performance
- Function calling and structured output
- Broad knowledge base

---

### 5. Kilo CLI

**Provider:** Kilo AI models

#### Installation
```bash
# Install Kilo CLI (check official documentation)
pip install kilo-cli

# Or via npm
npm install -g kilo-cli
```

#### Configuration
```env
LLM_PROVIDER=kilo
LLM_MODEL=              # Check Kilo documentation for available models
LLM_TEMPERATURE=0.3
```

#### Authentication
```bash
# Set up Kilo API key
export KILO_API_KEY=your_api_key_here
```

#### Notes
- Check [Kilo documentation](https://kilo.ai/docs) for specific model names
- May require specific CLI version for compatibility

---

### 6. GLM (Zhipu AI)

**Provider:** Zhipu AI GLM models

#### Installation
```bash
# Install Zhipu AI SDK
pip install zhipuai
```

#### Configuration
```env
LLM_PROVIDER=glm
LLM_MODEL=glm-5             # Latest GLM model
LLM_TEMPERATURE=0.2
```

#### Authentication
```bash
# Set up Zhipu API key
export ZHIPUAI_API_KEY=your_api_key_here
```

#### Available Models
- `glm-5` - Latest generation
- `glm-4-plus` - Enhanced GLM-4
- `glm-4` - Previous generation
- `glm-4-air` - Lightweight version

#### Best For
- Chinese language tasks (excellent Chinese support)
- Cost-effective alternative to Western providers
- Strong reasoning capabilities

---

## Provider Comparison

| Provider | Speed | Quality | Cost | Context | Temperature Support |
|----------|-------|---------|------|---------|---------------------|
| Qwen     | Fast  | Good    | Low  | 32K     | ❌ (CLI limitation) |
| Claude   | Medium| Excellent| High| 200K+   | ✅ |
| Gemini   | Fast  | Excellent| Low | 1M+     | ❌ (CLI limitation) |
| OpenAI   | Medium| Excellent| High| 128K    | ✅ |
| Kilo     | Varies| Good    | Varies| Varies | ❌ (CLI limitation) |
| GLM      | Fast  | Good    | Low  | 128K    | ✅ |

---

## Recommendations

### For Academic State of the Art Generation

**Best Overall:** Claude Sonnet 4.5
```env
LLM_PROVIDER=claude
LLM_MODEL=claude-sonnet-4.5
LLM_TEMPERATURE=0.3
```
- Excellent instruction following
- Strong academic writing capabilities
- Large context for long papers

**Best Value:** Gemini 2.5 Flash
```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
LLM_TEMPERATURE=0.3
```
- Fast and inexpensive
- Good quality output
- Massive context window

**Most Capable:** Claude Opus 4
```env
LLM_PROVIDER=claude
LLM_MODEL=claude-opus-4
LLM_TEMPERATURE=0.2
```
- Best for complex reasoning
- Highest quality output
- Most expensive

**Budget Option:** Qwen
```env
LLM_PROVIDER=qwen
LLM_MODEL=
LLM_TEMPERATURE=0.3
```
- Free or very low cost
- Good baseline performance
- Fast inference

---

## Troubleshooting

### Provider Not Available

**Error:** `'qwen' is not recognized as a command`

**Solution:**
```bash
# Check if CLI is installed
which qwen    # or claude, gemini, etc.

# Install if missing
pip install qwen-cli  # or appropriate installation
```

### Authentication Failed

**Error:** `API key not found` or `Unauthorized`

**Solution:**
```bash
# Set environment variable
export PROVIDER_API_KEY=your_key

# Or add to ~/.bashrc or ~/.zshrc for persistence
echo 'export ANTHROPIC_API_KEY=your_key' >> ~/.bashrc
source ~/.bashrc

# Verify
echo $ANTHROPIC_API_KEY
```

### Model Not Found

**Error:** `Model 'xyz' not found`

**Solution:**
1. Verify model name in provider documentation
2. Check your API tier has access to the model
3. Try leaving `LLM_MODEL` empty to use default:
   ```env
   LLM_MODEL=
   ```

### Temperature Not Working

**Note:** Some providers (Qwen, Gemini, Kilo) don't support temperature control through their CLI

**Solution:**
- Switch to a provider that supports it (Claude, OpenAI, GLM)
- Or accept the default behavior

### Rate Limiting

**Error:** `Rate limit exceeded`

**Solution:**
1. Reduce `MAX_WORKERS` in `.env`:
   ```env
   MAX_WORKERS=4  # Reduce concurrent requests
   ```
2. Add delays between requests (modify `soa_cli.py`)
3. Upgrade your API plan

---

## Advanced: Custom Provider

To add a new provider not listed here:

1. **Add provider configuration** in [soa_cli.py](../soa_cli.py):

```python
LLM_PROVIDERS = {
    # ... existing providers ...
    'my_provider': {
        'command': 'my-cli',           # CLI command name
        'model_flag': '-m',             # Flag for model selection
        'auto_yes': [],                 # Auto-confirmation flags
        'supports_temperature': True,   # Temperature support
        'temperature_flag': '--temp',   # Temperature flag
        'supports_system_prompt': True, # System prompt support
        'input_method': 'stdin',        # Input method
        'output_method': 'stdout'       # Output method
    }
}
```

2. **Update `.env`:**
```env
LLM_PROVIDER=my_provider
LLM_MODEL=my-model-name
```

3. **Test:**
```bash
python soa_cli.py
```

---

## Environment Variables Summary

All providers respect these configuration variables:

```env
# Choose provider
LLM_PROVIDER=claude  # Required: qwen, claude, gemini, openai, kilo, glm

# Specify model (optional, uses default if empty)
LLM_MODEL=claude-sonnet-4.5

# Control randomness (0.0 = deterministic, 1.0 = creative)
LLM_TEMPERATURE=0.3

# Request timeout (seconds)
LLM_TIMEOUT=300

# Processing settings (same for all providers)
MAX_WORKERS=10
MAX_PDF_CHARS=30000
CLUSTER_COUNT=6
```

---

## Getting Help

1. Check provider documentation:
   - [Qwen](https://qwen.ai/docs)
   - [Claude](https://docs.anthropic.com)
   - [Gemini](https://ai.google.dev/docs)
   - [OpenAI](https://platform.openai.com/docs)
   
2. Test CLI directly:
   ```bash
   echo "Hello" | claude -m claude-sonnet-4.5
   ```

3. Check API key:
   ```bash
   env | grep -i api_key
   ```

4. See [CONFIGURATION.md](CONFIGURATION.md) for more details
