# Enhanced Logging System Documentation

## Overview

The SOA-CLI system now includes a comprehensive logging system that provides detailed visibility into every operation. All logs are written to both console and file, with different verbosity levels available.

## Features

### 1. **Dual Output Logging**
- **Console**: INFO level by default (user-friendly progress updates)
- **File**: DEBUG level (detailed technical information)
- **Location**: `logs/soa_pipeline_YYYYMMDD_HHMMSS.log`

### 2. **Comprehensive Operation Tracking**

#### Environment Configuration
- All environment variables logged at startup
- API key status (SET/NOT_SET, no actual keys logged)
- LLM provider and model configuration
- Pipeline configuration (workers, PDF limits, clustering, citation style)
- Directory structure
- Python environment details

#### LLM Calls
```
LLM Call: writer.system.txt
  Provider: qwen
  Model: qwen-turbo
  System prompt: 12,345 chars
  User prompt: 3,456 chars
  Temperature: 0.1
  Max tokens: 4096
  Duration: 23.45s
  Retries: 0
```

#### PDF Extraction
```
PDF extraction: paper.pdf
  Total pages: 25, extracting up to: 25
  Extracted 25 pages, 45,230 chars
  PDF truncated: paper.pdf
    Original: 45,230 chars → Truncated: 30,000 chars
    Lost: 15,230 chars (33.6%)
```

#### Node Operations
```
==========================================
NODE: Theme Builder
==========================================
Loading existing thematic contract (TOON format)
Thematic Contract Summary:
  Global Theme: Machine learning for healthcare...
  Core Questions: 5
  In Scope Items: 12
  Out of Scope Items: 8
  Q1: What are the main ML approaches?
  Q2: What datasets are used?
  ...
Theme Builder completed successfully
```

#### Clustering Analysis
```
Clustering Analysis (silhouette):
  Optimal k: 4
  Scores: {2: 0.543, 3: 0.612, 4: 0.678, 5: 0.589}
  → k=4: score=0.678
    k=3: score=0.612
    k=2: score=0.543
```

#### Export Operations
```
Exporting to all formats (LaTeX, Markdown, Word)
  ✓ LaTeX exported: STATE_OF_THE_ART.tex (took 0.12s)
  ✓ Markdown exported: STATE_OF_THE_ART.md (took 1.45s)
  ✓ Word exported: STATE_OF_THE_ART.docx (took 3.21s)
```

#### Pipeline Summary
```
==========================================================================================
PIPELINE SUMMARY
==========================================================================================
Total Duration: 145.67s (2.4 minutes)
Papers Processed: 10/10
Final Stage: writer_complete
Verification: ✓ PASSED
Errors: 0
Output Format: all
==========================================================================================
```

### 3. **Performance Tracking**

Every major operation includes timing:
- Individual LLM calls (with retry attempts)
- PDF extraction per paper
- Node execution duration
- Export operation timing
- Total pipeline duration

### 4. **Error Tracking**

Detailed error logging with:
- Error type and message
- Context (which node/operation failed)
- Stack traces (in DEBUG mode)
- Retry attempts for transient failures

Example:
```
ERROR in Theme Builder: FileNotFoundError: THEMATIC_CONTRACT.toon
Stack trace:
  File "./soa_sdk.py", line 123, in theme_builder_node
    contract = load_toon("THEMATIC_CONTRACT.toon")
  ...
```

### 5. **State Transitions**

LangGraph state transitions logged:
```
State Transition: reader_map → extractor_map
  Papers Processed: 10
```

## Configuration

### Log Levels

Set via `LOG_LEVEL` environment variable:

```bash
# In .env
LOG_LEVEL=INFO     # Default - user-friendly progress
LOG_LEVEL=DEBUG    # Detailed technical information
LOG_LEVEL=WARNING  # Only warnings and errors
LOG_LEVEL=ERROR    # Only errors
```

### Console vs File Output

- **Console**: Respects `LOG_LEVEL` setting
- **File**: Always DEBUG level (captures everything)

### Log File Location

Logs are stored in `logs/` directory with timestamps:
```
logs/
├── soa_pipeline_20260302_143022.log
├── soa_pipeline_20260302_151534.log
└── soa_pipeline_20260302_163845.log
```

## Usage Examples

### Normal Operation (INFO level)
```bash
python soa_sdk.py papers/
# Console: High-level progress
# File: Detailed debug information
```

### Debug Mode (DEBUG level)
```bash
LOG_LEVEL=DEBUG python soa_sdk.py papers/
# Console: Detailed debug information
# File: Same detailed debug information
```

### Quiet Mode (WARNING level)
```bash
LOG_LEVEL=WARNING python soa_sdk.py papers/
# Console: Only warnings and errors
# File: Still captures DEBUG information
```

## Log Analysis Tips

### Find All Errors
```bash
grep "ERROR" logs/soa_pipeline_*.log
```

### Find LLM Call Durations
```bash
grep "Duration:" logs/soa_pipeline_*.log
```

### Find Truncated PDFs
```bash
grep "PDF truncated" logs/soa_pipeline_*.log
```

### Find Clustering Decisions
```bash
grep "optimal k" logs/soa_pipeline_*.log
```

### Find Total Pipeline Duration
```bash
grep "Total Duration" logs/soa_pipeline_*.log
```

## What Gets Logged

### ✅ Logged
- Environment configuration (at startup)
- API key status (SET/NOT_SET, not actual value)
- All LLM calls (provider, model, prompt sizes, duration, retries)
- PDF extraction (pages, characters, truncation details)
- Node operations (start, completion, duration)
- Clustering analysis (scores, optimal k selection)
- Export operations (format, duration, success/failure)
- State transitions
- Errors with stack traces
- Performance metrics (timing for every major operation)
- Pipeline summary (duration, papers processed, verification status)

### ❌ Not Logged (Security)
- Actual API keys (only status: SET/NOT_SET)
- Paper content (only metadata: file names, page counts, character counts)
- Personal information

## Log Levels in Detail

### DEBUG
- LLM prompt content sizes
- PDF extraction page-by-page details
- Citation style injection
- File I/O operations (reads, writes)
- State structure details
- Stack traces for errors

### INFO
- Pipeline stages starting/completing
- High-level operation summaries
- Paper count and processing status
- Export format confirmations
- Verification results
- Final summaries

### WARNING
- PDF truncation warnings
- Missing optional dependencies
- Retryable LLM call failures
- Non-critical issues

### ERROR
- LLM call failures (after all retries)
- PDF extraction failures
- Node execution failures
- Export failures
- Fatal errors with context

## Log File Format

```
2026-03-02 14:30:22 | INFO     | SOA-CLI | SOA-CLI Pipeline Logging Initialized
2026-03-02 14:30:22 | INFO     | SOA-CLI | Log Level: INFO (console), DEBUG (file)
2026-03-02 14:30:22 | INFO     | SOA-CLI | Log File: logs/soa_pipeline_20260302_143022.log
2026-03-02 14:30:23 | INFO     | SOA-CLI | LLM Configuration:
2026-03-02 14:30:23 | INFO     | SOA-CLI |   Provider: qwen
2026-03-02 14:30:23 | DEBUG    | SOA-CLI.LLMClient | LLMClient initialized: provider=qwen, model=qwen-turbo
...
```

Format: `Timestamp | Level | Logger | Message`

## Performance Impact

- **Memory**: Minimal (< 1MB for typical pipelines)
- **CPU**: Negligible (< 0.1% overhead)
- **Disk**: ~100-500KB per pipeline run (depends on paper count and verbosity)

## Troubleshooting

### Issue: Log file not created
**Solution**: Ensure `logs/` directory exists (created automatically by logging_config.py)

### Issue: Too much console output
**Solution**: Set `LOG_LEVEL=WARNING` or `LOG_LEVEL=ERROR`

### Issue: Missing detailed information
**Solution**: Check the log file in `logs/` directory (always DEBUG level)

### Issue: Log file too large
**Solution**: Old log files are not automatically deleted. Manually clean up:
```bash
# Keep only last 5 log files
ls -t logs/soa_pipeline_*.log | tail -n +6 | xargs rm
```

## Integration with Existing Code

### How It Works

1. **Initialization** (soa_sdk.py):
   ```python
   from src.logging_config import setup_logging, log_environment_config
   logger = setup_logging()
   log_environment_config(logger)
   ```

2. **Module-Level Loggers** (nodes.py, llm_client.py, etc.):
   ```python
   import logging
   logger = logging.getLogger('SOA-CLI.ModuleName')
   ```

3. **Logging Operations**:
   ```python
   logger.info("Operation started")
   logger.debug(f"Details: {details}")
   logger.warning("Non-critical issue")
   logger.error(f"Error: {e}")
   ```

## Benefits

1. **Complete Visibility**: Know exactly what's happening at every step
2. **Performance Monitoring**: Track timing for every operation
3. **Debugging**: Stack traces and detailed context for errors
4. **Audit Trail**: Complete record of all operations
5. **Production Ready**: Separate console (user) and file (technical) output
6. **Configurable**: Adjust verbosity without code changes
7. **Persistent**: All runs logged with timestamps

## Future Enhancements

Potential additions:
- Log rotation (automatic cleanup of old logs)
- Structured logging (JSON format for parsing)
- Remote logging (send logs to central server)
- Real-time log streaming (websocket for live updates)
- Log compression (gzip old logs)
- Performance profiling integration
