# Provider Setup

SOA-CLI uses CLI binaries through `src/llm_client.py`.

## Supported Providers

- `claude`
- `gemini`
- `qwen`
- `gpt`
- `glm`

At startup, `soa_cli.py` checks provider availability using `check_cli_available`.

## Example Setup

```bash
export LLM_PROVIDER=qwen
export LLM_MODEL=qwen-oauth
export LLM_TIMEOUT=180
```

If the configured provider binary is missing from `PATH`, startup exits early.

## Reliability Behavior

- Retries: up to 3 attempts in `LLMClient.call`.
- Backoff: 2s, 4s, 8s.
- On repeated failure, nodes receive a `__LLM_FAILURE__` error string and handle it as node error state.
