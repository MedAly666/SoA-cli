## Datetime JSON Serialization Fix - Summary

**Error Fixed:**
```
✗ Paper search failed: Object of type datetime is not JSON serializable
```

**Root Cause:**
A `datetime` object was being passed to the PRISMA log and later serialized to JSON, which fails because datetime objects aren't JSON-serializable.

**Changes Made:**

### File: `src/paper_fetcher.py` (line 250)

**Before (BROKEN):**
```python
self.prisma_log.log_search_strategy(
    queries=queries,
    databases=self.sources,
    date=datetime.now(),  # ❌ datetime object - not JSON serializable
    inclusion_criteria=self.contract.get('in_scope', []),
    exclusion_criteria=self.contract.get('out_of_scope', [])
)
```

**After (FIXED):**
```python
self.prisma_log.log_search_strategy(
    queries=queries,
    databases=self.sources,
    date=datetime.now().isoformat(),  # ✅ ISO string - JSON serializable
    inclusion_criteria=self.contract.get('in_scope', []),
    exclusion_criteria=self.contract.get('out_of_scope', [])
)
```

**Why This Works:**

1. `datetime.now()` returns a datetime object like: `datetime(2026, 3, 5, 11, 0, 44)`
2. This cannot be serialized to JSON directly
3. `.isoformat()` converts it to an ISO 8601 string like: `"2026-03-05T11:00:44.760590"`
4. Strings are JSON-serializable ✅

**Data Flow:**
```
datetime.now().isoformat() 
  → log_search_strategy(date=...)
  → self.search_date = date
  → save_candidates() → json.dump()
  → ✅ Success!
```

**Verification:**

Run `test_datetime_fix.py` shows:
```
❌ OLD WAY: Object of type datetime is not JSON serializable
✅ NEW WAY: Successfully serialized to JSON: 2026-03-05T11:00:44.760590
```

**Impact:**
- ✅ Fixes paper search JSON serialization error
- ✅ PRISMA metadata now saves correctly
- ✅ No breaking changes to data format (ISO 8601 is standard)
- ✅ All other datetime usages already correct

**Test It:**
```bash
python soa_cli.py --search-papers
```

The error "Object of type datetime is not JSON serializable" should be gone! 🎉
