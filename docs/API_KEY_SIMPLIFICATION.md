# API Key Simplification

## 🎯 Overview

The SDK now uses a **single `API_KEY` environment variable** instead of multiple provider-specific keys. The system automatically determines which provider to use based on `LLM_PROVIDER`.

## ✨ What Changed

### Before (Multiple Keys)
```bash
# .env file
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
DEEPSEEK_API_KEY=sk-...
QWEN_API_KEY=...
GLM_API_KEY=...
```

### After (Single Key)
```bash
# .env file
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
API_KEY=sk-...
```

## 📝 Configuration Examples

### Example 1: Using OpenAI
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
API_KEY=sk-proj-...
```

### Example 2: Using Claude
```bash
LLM_PROVIDER=claude
LLM_MODEL=claude-3-opus-20240229
API_KEY=sk-ant-...
```

### Example 3: Using Gemini
```bash
LLM_PROVIDER=gemini
LLM_MODEL=gemini-pro
API_KEY=AIza...
```

### Example 4: Using DeepSeek
```bash
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
API_KEY=sk-...
```

### Example 5: Using Qwen (API Mode)
```bash
LLM_PROVIDER=qwen
LLM_MODEL=qwen-turbo
API_KEY=sk-...
```

### Example 6: Using Qwen (CLI Mode)
```bash
LLM_PROVIDER=qwen
LLM_MODEL=qwen-turbo
API_KEY=  # Leave empty to use local Qwen CLI
```

### Example 7: Using Ollama (Local)
```bash
LLM_PROVIDER=ollama
LLM_MODEL=llama2
# No API_KEY needed - runs locally
```

## 🔄 Switching Providers

Switching providers is now as simple as changing two variables:

```bash
# Start with OpenAI
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4
export API_KEY=sk-proj-...
python soa_sdk.py --papers papers/

# Switch to Claude (just change the key and provider)
export LLM_PROVIDER=claude
export LLM_MODEL=claude-3-opus-20240229
export API_KEY=sk-ant-...
python soa_sdk.py --papers papers/

# Switch to DeepSeek (cheaper!)
export LLM_PROVIDER=deepseek
export LLM_MODEL=deepseek-chat
export API_KEY=sk-...
python soa_sdk.py --papers papers/
```

## 💡 Benefits

1. **Simpler Configuration**: One key instead of seven
2. **Easier Provider Switching**: Just change `LLM_PROVIDER` and `API_KEY`
3. **Less Clutter**: Cleaner `.env` file
4. **Secure**: Only the active provider's key needs to be set
5. **Flexible**: Easy to switch providers without maintaining multiple keys

## 🚀 Usage in Code

### CLI Usage
```bash
# Configure via .env
python soa_sdk.py --papers papers/

# Or pass via environment
export API_KEY=sk-...
export LLM_PROVIDER=openai
python soa_sdk.py --papers papers/

# Or pass via CLI flags
python soa_sdk.py --papers papers/ --provider claude --model claude-3-opus
```

### SDK Usage
```python
import os
from soa_sdk import SOAEngine

# Set environment
os.environ['API_KEY'] = 'sk-...'
os.environ['LLM_PROVIDER'] = 'openai'

# Create engine
engine = SOAEngine()
result = engine.process("papers/")

# Or specify directly
engine = SOAEngine(provider="openai", model="gpt-4")
result = engine.process("papers/")
```

## 🔧 Migration Guide

### For Existing Users

**Old `.env` file**:
```bash
OPENAI_API_KEY=sk-proj-abc123
ANTHROPIC_API_KEY=sk-ant-xyz789
GOOGLE_API_KEY=AIza...
```

**New `.env` file** (pick one provider):
```bash
# If you primarily use OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
API_KEY=sk-proj-abc123

# Or if you primarily use Claude
LLM_PROVIDER=claude
LLM_MODEL=claude-3-opus-20240229
API_KEY=sk-ant-xyz789

# Or if you primarily use Gemini
LLM_PROVIDER=gemini
LLM_MODEL=gemini-pro
API_KEY=AIza...
```

### Multiple Providers

If you need to switch between providers frequently, you can create multiple `.env` files:

```bash
# .env.openai
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
API_KEY=sk-proj-...

# .env.claude
LLM_PROVIDER=claude
LLM_MODEL=claude-3-opus-20240229
API_KEY=sk-ant-...

# .env.deepseek
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
API_KEY=sk-...
```

Then load the one you need:
```bash
# Use OpenAI
cp .env.openai .env
python soa_sdk.py --papers papers/

# Switch to Claude
cp .env.claude .env
python soa_sdk.py --papers papers/
```

## 📊 Provider-Specific Notes

### OpenAI
- API Key format: `sk-proj-...` or `sk-...`
- Get key: https://platform.openai.com/api-keys

### Anthropic (Claude)
- API Key format: `sk-ant-...`
- Get key: https://console.anthropic.com/settings/keys

### Google (Gemini)
- API Key format: `AIza...`
- Get key: https://makersuite.google.com/app/apikey

### DeepSeek
- API Key format: `sk-...`
- Get key: https://platform.deepseek.com/api_keys

### Qwen
- API Key format: `sk-...`
- Get key: https://dashscope.console.aliyun.com/apiKey
- **OR** use local CLI (no key needed)

### GLM (ChatGLM)
- API Key format: varies
- Get key: https://open.bigmodel.cn/

### Ollama
- No API key needed
- Runs locally
- Install: https://ollama.ai

## ❓ FAQ

### Q: What if I have multiple API keys?
**A**: Set `API_KEY` to the one matching your `LLM_PROVIDER`. Switch as needed.

### Q: Can I still use provider-specific keys?
**A**: No, the system now only looks for `API_KEY`. This simplification improves maintainability.

### Q: What about security?
**A**: This is actually **more secure** - you only need to expose the key for the provider you're actively using, not all keys at once.

### Q: How do I test multiple providers?
**A**: Change `API_KEY` and `LLM_PROVIDER` between tests:

```python
import os
from soa_sdk import SOAEngine

# Test OpenAI
os.environ['LLM_PROVIDER'] = 'openai'
os.environ['API_KEY'] = 'sk-openai-key'
engine = SOAEngine()
result1 = engine.process("papers/")

# Test Claude
os.environ['LLM_PROVIDER'] = 'claude'
os.environ['API_KEY'] = 'sk-ant-claude-key'
engine = SOAEngine()
result2 = engine.process("papers/")
```

### Q: Does this break backward compatibility?
**A**: If you have old `.env` files with multiple provider-specific keys, you'll need to:
1. Choose your primary provider
2. Copy its key to `API_KEY`
3. Set `LLM_PROVIDER` to match

The migration takes 30 seconds.

## 🎉 Summary

The single `API_KEY` approach is:
- ✅ **Simpler** - One variable instead of seven
- ✅ **Cleaner** - Less clutter in `.env` files
- ✅ **Secure** - Only active provider key exposed
- ✅ **Flexible** - Easy to switch providers
- ✅ **Maintainable** - Less code complexity

---

**Updated**: March 2, 2026
