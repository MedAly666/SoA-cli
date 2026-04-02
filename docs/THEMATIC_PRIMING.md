# Thematic Priming

Theme contract behavior is implemented in `theme_builder_node`.

## Contract Source Priority

1. If `state.thematic_contract` already contains `global_theme`, it is used directly.
2. Else if `THEMATIC_CONTRACT.json` exists, it is loaded.
3. Else build from `theme_input.json` using `build_thematic_contract` (unless strict mode blocks).

## Strict Mode

Set `SOA_REQUIRE_THEMATIC_CONTRACT=true` to require pre-existing `THEMATIC_CONTRACT.json`.
