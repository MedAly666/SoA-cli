# Vector DB And Clean

## Current Cluster Path

The active cluster node in `src/graph/nodes.py` builds deterministic in-memory clusters from extracted papers (`_cluster_from_extracted`).

## Legacy Vector DB Components

`src/vectorize.py` and related FAISS code remain in repo, but are not the required data handoff path in current DB-first graph execution.

## Clean Command

`python soa_cli.py --clean` clears files under `artifacts/` and preserves folder structure.
