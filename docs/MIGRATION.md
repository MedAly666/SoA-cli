# Migration Guide: CLI → SDK

This guide explains the changes from SOA-CLI to SOA-SDK and how to migrate.

## 🎯 What Changed?

### 1. File Rename
- **Old**: `soa_cli.py`
- **New**: `soa_sdk.py`

### 2. New SDK Interface

**Before** (CLI only):
```bash
python soa_cli.py --papers papers/
```

**After** (SDK + CLI):
```python
# As library
from soa_sdk import SOAEngine
engine = SOAEngine()
result = engine.process("papers/")

# As CLI (still works)
python soa_sdk.py --papers papers/
```

### 3. Multi-Provider LLM Support

**Before**: Single provider (hardcoded or environment)

**After**: Choose any provider:

```python
# In code
engine = SOAEngine(provider="openai", model="gpt-4")

# Via CLI
python soa_sdk.py --provider claude --model claude-3-opus

# Via environment
LLM_PROVIDER=gemini
LLM_MODEL=gemini-pro
```

## 🔧 Configuration Changes

### Old `.env` format
```bash
OPENAI_API_KEY=sk-...
# That's it
```

### New `.env` format
```bash
# Default provider
LLM_PROVIDER=openai
LLM_MODEL=gpt-4

# Single API key (used with selected provider)
API_KEY=sk-...

# Pipeline settings
LLM_TIMEOUT=600
MAX_WORKERS=10
MAX_PDF_CHARS=100000
```

**✅ Backward Compatible**: Old `.env` files still work!

## 📦 New Dependencies

### Required
```bash
pip install openai>=1.0.0 requests>=2.31.0 simple-toon>=0.2.0
```

### Optional (install based on provider)
```bash
# For Anthropic/Claude
pip install anthropic>=0.18.0

# For Google/Gemini
pip install google-generativeai>=0.3.0
```

## 🚀 Migration Steps

### Step 1: Update Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Update Configuration
```bash
cp .env.example .env
# Edit .env and add your API keys
```

### Step 3: Update Scripts

**If you used CLI directly** (no changes needed):
```bash
# Old
python soa_cli.py --papers papers/

# New (same command, different file)
python soa_sdk.py --papers papers/
```

**If you imported as module**:
```python
# Old
from soa_cli import run_pipeline
result = run_pipeline("papers/", ...)

# New
from soa_sdk import SOAEngine
engine = SOAEngine()
result = engine.process("papers/")
```

### Step 4: Choose Your Provider

**Option A**: Use environment variables (`.env`)
```bash
LLM_PROVIDER=qwen
LLM_MODEL=qwen-turbo
API_KEY=...
```

**Option B**: Specify in code
```python
engine = SOAEngine(provider="openai", model="gpt-4")
```

**Option C**: Pass via CLI
```bash
python soa_sdk.py --provider claude --model claude-3-opus
```

## 📊 Feature Comparison

| Feature | CLI Mode | SDK Mode |
|---------|----------|----------|
| Process papers | ✅ | ✅ |
| Choose provider | ✅ (flag) | ✅ (param) |
| Resume from checkpoint | ✅ | ✅ |
| Clean artifacts | ✅ | ❌ (manual) |
| Custom thread ID | ✅ | ✅ |
| Progress tracking | ✅ (stdout) | ✅ (return dict) |
| Error handling | ✅ (exit code) | ✅ (exceptions) |

## 🎓 Usage Examples

### Example 1: Basic Migration

**Old CLI**:
```bash
python soa_cli.py --papers papers/
```

**New CLI** (same functionality):
```bash
python soa_sdk.py --papers papers/
```

**New SDK** (programmatic):
```python
from soa_sdk import SOAEngine

engine = SOAEngine()
result = engine.process("papers/")

if result.get("soa_draft"):
    print("Success!")
```

### Example 2: Provider Selection

**Old** (hardcoded in code):
```python
# Had to modify source code to change provider
```

**New** (configurable):
```python
# Try different providers easily
providers = ["openai", "claude", "gemini"]

for provider in providers:
    engine = SOAEngine(provider=provider)
    result = engine.process("papers/")
    print(f"{provider}: {result['processed_papers']} papers")
```

### Example 3: Batch Processing

**Old** (run CLI multiple times):
```bash
for dir in exp1 exp2 exp3; do
    python soa_cli.py --papers $dir/
done
```

**New** (single Python script):
```python
from soa_sdk import SOAEngine

engine = SOAEngine(provider="qwen")

for directory in ["exp1", "exp2", "exp3"]:
    result = engine.process(f"{directory}/")
    print(f"{directory}: {result['status']}")
```

### Example 4: Error Handling

**Old**:
```bash
# Check exit code
python soa_cli.py --papers papers/
if [ $? -eq 0 ]; then
    echo "Success"
fi
```

**New**:
```python
from soa_sdk import SOAEngine

engine = SOAEngine()

try:
    result = engine.process("papers/")
    print(f"Processed {result['processed_papers']} papers")
except Exception as e:
    print(f"Error: {e}")
```

## 🔍 Breaking Changes

### ⚠️ None!

This is a **non-breaking** update:
- Old CLI commands still work (just use `soa_sdk.py` instead of `soa_cli.py`)
- Old `.env` files still work
- All functionality preserved

### ✨ New Features

1. **SDK Interface**: Import and use as library
2. **Multi-Provider**: 7 LLM providers supported
3. **Provider Aliases**: Use "gpt" instead of "openai", "claude" instead of "anthropic"
4. **Better Configuration**: Centralized `.env` management
5. **TOON Format**: 48-50% token savings (automatic)

## 🐛 Troubleshooting

### Issue: Import Error

**Problem**:
```python
ModuleNotFoundError: No module named 'openai'
```

**Solution**:
```bash
pip install -r requirements.txt
```

### Issue: Provider Not Found

**Problem**:
```
ValueError: Provider 'gpt5' not found
```

**Solution**:
Check available providers:
```python
from src.llm_provider import PROVIDERS
print(PROVIDERS.keys())
# Output: ['openai', 'gpt', 'claude', 'anthropic', ...]
```

### Issue: API Key Missing

**Problem**:
```
ValueError: Provider is not configured
```

**Solution**:
1. Create `.env` file:
   ```bash
   cp .env.example .env
   ```
2. Add your API key:
   ```bash
   LLM_PROVIDER=openai
   API_KEY=sk-...
   ```
3. Or export it:
   ```bash
   export API_KEY=sk-...
   export LLM_PROVIDER=openai
   ```

### Issue: TOON Format Error

**Problem**:
```
ModuleNotFoundError: No module named 'toon_parser'
```

**Solution**:
```bash
pip install simple-toon>=0.2.0
```

## 📚 Further Reading

- [SDK_README.md](SDK_README.md) - Complete SDK documentation
- [examples.py](examples.py) - Usage examples
- [.env.example](.env.example) - Configuration template

## 🎉 Benefits of Migration

1. **Flexibility**: Use as library or CLI
2. **Provider Choice**: 7 LLM options (more coming)
3. **Cost Optimization**: Switch to cheaper providers
4. **SaaS Ready**: Programmatic API for web backends
5. **Token Savings**: 48% reduction with TOON format
6. **Better Testing**: Unit test with different providers

## 🚀 Next Steps

1. Update your scripts to use `soa_sdk.py`
2. Configure providers in `.env`
3. Try different LLM providers
4. Explore SDK interface for automation
5. Build web applications with the SDK

---

**Questions?** Open an issue on GitHub!
