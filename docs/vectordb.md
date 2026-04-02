# Vector DB Stage

Current vectorize node behavior in `src/graph/nodes.py`:
- reports embedding metadata summary in state
- does not require JSON artifact exchange for downstream stages

Clustering in current runtime is state-driven and uses `_cluster_from_extracted` fallback logic.

Legacy vector-db modules are retained for compatibility and experimentation.
