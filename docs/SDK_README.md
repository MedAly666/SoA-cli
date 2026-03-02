# SOA-SDK: State of the Art Generation SDK

Multi-provider LLM SDK for generating academic State of the Art sections from research papers.

## ✨ Features

- **Multi-Provider Support**: GPT, Claude, Gemini, DeepSeek, Qwen, GLM, Ollama
- **Flexible Interface**: Use as Python SDK or CLI
- **LangGraph Orchestration**: Fault-tolerant multi-agent pipeline
- **TOON Format**: 30-60% token reduction for LLM inputs
- **Incremental Processing**: Resume from checkpoints

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd SOA-CLI

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your API keys
```

### Usage as SDK

```python
from soa_sdk import SOAEngine

# Use default provider (Qwen)
engine = SOAEngine()
result = engine.process("papers/")

# Use OpenAI GPT-4
engine = SOAEngine(provider="openai", model="gpt-4")
result = engine.process("papers/", max_repair=3)

# Process specific papers
result = engine.process_papers([
    "paper1.pdf",
    "paper2.pdf"
])

print(f"Processed {result['processed_papers']} papers")
print(f"Generated: {result.get('soa_draft') is not None}")
```

### Usage as CLI

```bash
# Default provider (from .env)
python soa_sdk.py --papers papers/

# Specify provider and model
python soa_sdk.py --papers papers/ --provider openai --model gpt-4

# With options
python soa_sdk.py --papers papers/ --provider claude --model claude-3-opus-20240229 --max-repair 5

# Clean start (remove all artifacts)
python soa_sdk.py --papers papers/ --clean
```

## 🔧 Supported Providers

| Provider | Models | API Key Required |
|----------|--------|------------------|
| **OpenAI** | gpt-4, gpt-4-turbo, gpt-3.5-turbo | `OPENAI_API_KEY` |
| **Anthropic** | claude-3-opus, claude-3-sonnet, claude-3-haiku | `ANTHROPIC_API_KEY` |
| **Google** | gemini-pro, gemini-1.5-pro | `GOOGLE_API_KEY` |
| **DeepSeek** | deepseek-chat, deepseek-coder | `DEEPSEEK_API_KEY` |
| **Qwen** | qwen-turbo, qwen-plus, qwen-max | `QWEN_API_KEY` (or local CLI) |
| **GLM** | glm-4, glm-3-turbo | `GLM_API_KEY` |
| **Ollama** | llama2, mistral, codellama, etc. | Local installation |

## 📝 Configuration

Create a `.env` file:

```bash
# Default provider
LLM_PROVIDER=openai
LLM_MODEL=gpt-4

# API Key (used for the selected provider)
API_KEY=sk-...

# Pipeline settings
LLM_TIMEOUT=600
MAX_WORKERS=10
MAX_PDF_CHARS=100000
```

## 📚 Examples

See [examples.py](examples.py) for comprehensive usage examples:

```bash
python examples.py
```

## 🏗️ Architecture

```
SOA-SDK/
├── soa_sdk.py              # Main SDK + CLI entry point
├── src/
│   ├── llm_provider.py     # Multi-provider LLM abstraction
│   ├── graph/              # LangGraph pipeline
│   │   ├── nodes.py        # Agent nodes
│   │   ├── builder.py      # Graph compiler
│   │   └── state.py        # State definition
│   ├── toon_utils.py       # TOON serialization
│   ├── theme_builder.py    # Thematic contract
│   ├── vectorize.py        # Embeddings
│   └── ...
└── examples.py             # Usage examples
```

## 🔄 Pipeline Stages

1. **Theme Builder**: Define research scope
2. **Reader**: Extract structured data from PDFs
3. **Extractor**: Extract methodological facts
4. **Critic**: Assess relevance and quality
5. **Vectorizer**: Generate embeddings
6. **Clustering**: Group similar papers
7. **Synthesis**: Generate coherent narrative
8. **Writer**: Draft LaTeX document
9. **Verifier**: Check for hallucinations
10. **Repair**: Fix issues (if needed)

## 📖 Output

- `STATE_OF_THE_ART.tex` - Final LaTeX document
- `artifacts/final_state.toon` - Complete pipeline state
- `artifacts/soa/` - Intermediate results

## 🛠️ Development

```bash
# Install development dependencies
pip install -r requirements.txt

# Run with debug
python soa_sdk.py --papers papers/ --provider qwen

# Clean artifacts
python soa_sdk.py --clean

# Resume from checkpoint
python soa_sdk.py --resume --thread-id experiment-1
```

## 🔑 API Key Setup

Set a single `API_KEY` environment variable. The system automatically uses it with the provider specified in `LLM_PROVIDER`.

### Via Environment Variable
```bash
# Set your API key
export API_KEY="sk-..."

# Set your provider
export LLM_PROVIDER="openai"
export LLM_MODEL="gpt-4"
```

### Via .env File
```bash
# .env file
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
API_KEY=sk-...
```

### Switching Providers
```bash
# Switch to Claude
export LLM_PROVIDER="claude"
export LLM_MODEL="claude-3-opus-20240229"
export API_KEY="sk-ant-..."

# Switch to Gemini
export LLM_PROVIDER="gemini"
export LLM_MODEL="gemini-pro"
export API_KEY="AIza..."
```

### Ollama (Local)
```bash
# No API key needed for Ollama
export LLM_PROVIDER="ollama"
export LLM_MODEL="llama2"

# Install Ollama: https://ollama.ai
ollama serve
```

## 📊 Token Savings

Using TOON format instead of JSON:
- **JSON**: 14,240 chars (~3,560 tokens)
- **TOON**: 7,390 chars (~1,847 tokens)
- **Reduction**: 48.1% ✨

For a 42-paper pipeline:
- **~7,200 tokens saved** per run
- **~48% API cost reduction**

## 🚀 SaaS Ready

This SDK is designed for SaaS integration:
- Clean programmatic API
- Async-ready architecture
- Multi-provider support
- Configurable via environment
- Artifact storage system

See [Architecture Guide](docs/ARCHITECTURE.md) for SaaS integration patterns.

## 📄 License

MIT

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md).

## 📧 Support

For issues and questions:
- GitHub Issues: [your-repo/issues](https://github.com/your-repo/issues)
- Email: support@example.com

---

**Built with ❤️ using LangGraph, LangChain, and modern LLMs**
