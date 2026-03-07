## Theme Builder Fix - Summary

**Error Fixed:**
```
Error: expected str, bytes or os.PathLike object, not LLMClient
```

**Root Cause:**
In `soa_cli.py`, an `LLMClient` instance was being passed to functions that expect a model name string (or None).

**Changes Made:**

### File: `soa_cli.py` (lines 423-442)

**Before (WRONG):**
```python
def search_papers_command(auto_download: bool = False):
    from src.paper_fetcher import PRISMAPaperFetcher
    from src.theme_builder import ensure_theme_input, build_thematic_contract
    from src.llm_client import LLMClient  # ← Unnecessary import
    
    try:
        model = LLMClient(timeout=120)  # ← Creating instance
        user_input = ensure_theme_input(user_input_file, model=model)  # ← Passing instance
        contract = build_thematic_contract(user_input_file, model)     # ← Passing instance
```

**After (CORRECT):**
```python
def search_papers_command(auto_download: bool = False):
    from src.paper_fetcher import PRISMAPaperFetcher
    from src.theme_builder import ensure_theme_input, build_thematic_contract
    # Removed: from src.llm_client import LLMClient
    
    try:
        # Use None to let functions create their own LLMClient with proper settings
        user_input = ensure_theme_input(user_input_file, model=None)  # ← Passing None
        contract = build_thematic_contract(user_input_file, model=None)  # ← Passing None
```

**Why This Works:**

Both `ensure_theme_input()` and `build_thematic_contract()` have this signature:
```python
def function_name(user_input_file: str, model=None):
```

The `model` parameter expects:
- `None` (default) - Functions will create their own LLMClient internally
- `str` - A model name like "qwen-32b", "claude-opus-4", etc.

**NOT:** An LLMClient instance

The functions internally create their own LLMClient:
```python
client = LLMClient(model=model, timeout=120)
```

When you pass an LLMClient instance as `model`, it tries to use that instance as a model name string, causing the error.

**Testing:**

Run the command that was failing:
```bash
python soa_cli.py --search-papers
```

This should now work without the "expected str, bytes or os.PathLike object" error.

**Impact:**
- ✅ Fixes paper search functionality
- ✅ Fixes thematic contract generation
- ✅ No breaking changes to other parts of the system
- ✅ Cleaner code (removed unnecessary import)
