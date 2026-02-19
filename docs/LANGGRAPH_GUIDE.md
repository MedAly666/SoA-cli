# SOA-CLI Architecture Guide

## Overview

This document describes the **LangGraph-based architecture** for SOA-CLI, a production-grade multi-agent system for generating State of the Art sections.

## Architecture Highlights

### Key Benefits
- ✅ **Fault Tolerance**: Automatic checkpointing allows resuming from any node
- ✅ **Explicit Control Flow**: Clear verification gates and repair loops
- ✅ **Type-Safe State**: TypedDict ensures data consistency
- ✅ **Better Error Handling**: Errors don't crash the pipeline
- ✅ **Professional Architecture**: Separation of concerns, testable nodes

### Graph Structure

```
START
  ↓
theme_builder (LLM) → Creates thematic contract
  ↓
reader_map (LLM, parallel) → Extracts text from all PDFs
  ↓
extractor_map (LLM, parallel) → Extracts structured facts
  ↓
critic_map (LLM, parallel) → Evaluates methodology
  ↓
vectorize (non-LLM) → Creates embeddings
  ↓
cluster (non-LLM) → Similarity clustering
  ↓
interpret_clusters (LLM) → Interprets clusters
  ↓
synthesis (LLM) → Cross-paper synthesis
  ↓
writer (LLM) → Generates LaTeX draft
  ↓
verifier (mixed) → Checks for hallucinations
  ↓ [CONDITIONAL]
  ├─→ PASS → END
  ├─→ MAX ITERATIONS → END
  └─→ FAIL → repair (LLM)
              ↓
         [LOOP BACK TO verifier]
```

## File Structure

```
SOA-CLI/
├── soa_cli.py                 # Main entry point (LangGraph pipeline)
├── test_langgraph.py          # Validation tests
├── visualize_graph.py         # Graph visualization
├── src/
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py           # SOAState TypedDict
│   │   ├── nodes.py           # All 11 node functions
│   │   └── builder.py         # Graph construction & routing
│   ├── theme_builder.py       # Thematic contract utilities
│   ├── vectorize.py
│   ├── similarity_cluster.py
│   ├── repair_loop.py
│   └── hallucination_detector.py
├── prompts/                   # Enhanced with technical depth
│   ├── theme_builder.system.txt
│   ├── reader.system.txt
│   ├── extractor.system.txt
│   ├── critic.system.txt
│   ├── cluster.system.txt
│   ├── synthesis.system.txt
│   ├── writer.system.txt
│   ├── verifier.system.txt
│   └── repair.system.txt
└── papers/                    # Input PDFs
```

## Usage

### Basic Usage

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the pipeline
python3 soa_cli.py
```

### Advanced Options

```bash
# Custom papers directory
python3 soa_cli.py --papers /path/to/pdfs

# Adjust max repair iterations (default: 3)
python3 soa_cli.py --max-repair 5

# Resume from checkpoint
python3 soa_cli.py --resume --thread-id my-session

# Custom thread ID for concurrent runs
python3 soa_cli.py --thread-id experiment-1
```

# Adjust max repair iterations (default: 3)
python3 soa_cli.py --max-repair 5

# Resume from checkpoint
python3 soa_cli.py --resume --thread-id my-session

# Custom thread ID for concurrent runs
python3 soa_cli.py --thread-id experiment-1
```

### Advanced Options

```bash
# Custom papers directory
python3 soa_langgraph.py --papers /path/to/papers

# Adjust max repair iterations (default: 3)
python3 soa_langgraph.py --max-repair 5

# Resume from checkpoint
python3 soa_langgraph.py --resume --thread-id my-session

# Custom thread ID for concurrent runs
python3 soa_langgraph.py --thread-id experiment-1
```

### Environment Variables

```bash
# LLM provider (default: qwen)
export LLM_PROVIDER=gemini
export LLM_MODEL=gemini-2.0-flash-exp

# Clustering
export CLUSTER_COUNT=6

# Parallelism (for ThreadPoolExecutor in nodes)
export MAX_WORKERS=10
```

## State Schema

The pipeline state is a typed dictionary (`SOAState`) with:

### Immutable Inputs
- `thematic_contract`: Global scope (set once by theme_builder)
- `paper_paths`: List of PDF paths
- `max_repair_iterations`: Maximum repair attempts (default: 3)

### Aggregating Collections
These use `Annotated[dict, operator.or_]` to merge results:
- `reader_outputs`: {paper_id: {metadata, text}}
- `extracted_facts`: {paper_id: {facts, equations, algorithms}}
- `critic_assessments`: {paper_id: {strength_scores, gaps}}
- `errors`: List of error dictionaries

### Single-Value Fields
Last write wins:
- `embeddings`: Vector representations (used internally)
- `raw_clusters`: Precomputed similarity clusters
- `clusters`: LLM-interpreted clusters
- `synthesis`: Cross-paper synthesis
- `soa_draft`: Current LaTeX draft

### Verification & Repair
- `verification_results`: List of hallucination violations
- `verification_passed`: Boolean (True = no violations)
- `repair_iteration`: Current repair attempt (0-indexed)

### Metadata
- `pipeline_stage`: Current stage name
- `total_papers`: Number of papers
- `processed_papers`: Successfully processed papers

## Node Implementation Pattern

All nodes follow this pattern:

```python
def my_node(state: SOAState) -> dict:
    """
    Node description.
    
    Returns:
        Partial state update (NOT full state)
    """
    print("\n[Node: My Node]")
    
    # Extract what we need
    contract = state["thematic_contract"]
    papers = state["paper_paths"]
    
    try:
        # Do work
        result = do_something(contract, papers)
        
        # Return PARTIAL update
        return {
            "my_output": result,
            "pipeline_stage": "my_node_complete",
            "errors": []
        }
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "errors": [{
                "node": "my_node",
                "error": str(e)
            }]
        }
```

## Conditional Routing

The `route_after_verification` function implements the decision logic:

```python
def route_after_verification(state: SOAState) -> Literal["repair", "end"]:
    passed = state["verification_passed"]
    iteration = state["repair_iteration"]
    max_iterations = state["max_repair_iterations"]
    
    if passed:
        return "end"  # Success!
    
    if iteration >= max_iterations:
        return "end"  # Give up
    
    return "repair"  # Try to fix
```

## Checkpointing

LangGraph automatically saves state after each node:

```python
from langgraph.checkpoint.memory import MemorySaver

app = compile_graph(checkpointer=MemorySaver())
```

To resume from a checkpoint:

```bash
python3 soa_langgraph.py --resume --thread-id my-session-id
```

**Note**: Current implementation uses in-memory checkpointing. For production, use SQLite:

```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
app = compile_graph(checkpointer=checkpointer)
```

## Error Handling

Errors are accumulated in the `errors` field:

```python
{
    "node": "extractor",
    "paper": "paper_123",
    "error": "JSON parsing failed",
    "fatal": False  # Optional
}
```

**Non-fatal errors** don't stop the pipeline. The graph continues and final errors are reported at the end.

## Output Files

After running:

```
artifacts/
├── initial_state.json         # Input state (for debugging)
├── final_state.json           # Complete final state
├── reader/
│   ├── paper1.json
│   └── paper2.json
├── extracted/
│   ├── paper1.json
│   └── paper2.json
├── critic/
│   ├── paper1.json
│   └── paper2.json
├── clusters/
│   ├── preclusters.json       # Raw clusters
│   └── clusters.json          # Interpreted clusters
├── synthesis/
│   └── synthesis.json
└── soa/
    └── state_of_the_art.tex   # Draft LaTeX

STATE_OF_THE_ART.tex             # Final output (copied to root)
THEMATIC_CONTRACT.json           # Global theme
```

## Architecture Evolution

SOA-CLI now uses LangGraph for production-grade orchestration:

| Feature | Previous Sequential | Current LangGraph |
|---------|-------------------|-------------------|
| Thematic contract | ✅ | ✅ |
| Parallel processing | ✅ ThreadPoolExecutor | ✅ ThreadPoolExecutor (in nodes) |
| Repair loop | ⚠️ Manual | ✅ Explicit graph loop |
| Error handling | ⚠️ Crashes | ✅ Accumulates, continues |
| Checkpointing | ❌ | ✅ Automatic |
| State management | ⚠️ Files | ✅ Typed in-memory |
| Verification gates | ⚠️ Implicit | ✅ Explicit routing |

## Debugging

### View graph structure

```python
from src.graph.builder import build_graph

workflow = build_graph()
print(workflow.get_graph().draw_mermaid())
```

### Inspect state at any point

```python
from src.graph.builder import compile_graph

app = compile_graph()
config = {"configurable": {"thread_id": "debug"}}

for chunk in app.stream(initial_state, config):
    print(chunk)
```

### Check errors

```python
import json

with open("artifacts/final_state.json") as f:
    state = json.load(f)

for err in state.get("errors", []):
    print(f"[{err['node']}] {err['error']}")
```

## Common Issues

### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'langgraph'`

**Solution**:
```bash
source .venv/bin/activate
pip install langgraph langchain-core
```

### 2. Missing Papers

**Problem**: `FileNotFoundError: No PDF files found in papers`

**Solution**:
```bash
# Ensure papers/ directory exists and contains PDFs
ls papers/*.pdf

# Or specify custom directory
python3 soa_langgraph.py --papers /path/to/pdfs
```

### 3. LLM Timeout

**Problem**: Node hangs or times out

**Solution**:
```bash
export LLM_TIMEOUT=600  # 10 minutes
python3 soa_langgraph.py
```

### 4. Verification Always Fails

**Problem**: Repair loop exhausts iterations

**Solution**:
- Check `artifacts/soa/state_of_the_art.tex` for hallucinations
- Increase max iterations: `--max-repair 5`
- Review `verification_results` in final_state.json

## Performance

On a typical setup (10 papers, Gemini 2.0 Flash):
- **Theme Builder**: ~30s
- **Reader Map**: ~2 min (parallel)
- **Extractor Map**: ~3 min (parallel)
- **Critic Map**: ~2 min (parallel)
- **Vectorize**: ~5s
- **Cluster**: ~2s
- **Interpret Clusters**: ~30s
- **Synthesis**: ~45s
- **Writer**: ~1 min
- **Verifier**: ~30s
- **Repair** (if needed): ~1 min per iteration

**Total**: ~10-15 minutes for 10 papers (without repairs)

## Future Enhancements

### 1. Persistent Checkpointing
```python
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
```

### 2. Distributed Execution
Use LangGraph Cloud for distributed node execution

### 3. Human-in-the-Loop
Add `interrupt_before=["writer"]` to review synthesis before writing

### 4. Advanced Parallelism
Replace ThreadPoolExecutor with LangGraph's `Send` API for native parallel mapping

### 5. Streaming Output
```python
for event in app.stream_events(initial_state, config):
    print(event)
```

## Support

For issues or questions:
1. Check error logs in `artifacts/final_state.json`
2. Review individual stage outputs in `artifacts/*/`
3. Compare with sequential script output for validation

## License

[Your license here]
