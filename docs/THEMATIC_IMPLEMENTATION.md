# Thematic Implementation

Core implementation files:
- `src/theme_builder.py`
- `src/graph/nodes.py` (`theme_builder_node`)

The thematic contract is injected into downstream agent inputs via `inject_contract` / `inject_theme_into_input`.

Required contract fields are validated at runtime:
- `global_theme`
- `core_questions`
- `in_scope`
- `out_of_scope`
