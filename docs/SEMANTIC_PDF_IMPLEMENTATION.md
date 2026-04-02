# Semantic PDF Implementation

Semantic parsing integration exists and is active when configured:

- module: `src/pdf_parser.py`
- router: `extract_pdf_content()` in `src/graph/nodes.py`

## Behavior

- If `USE_SEMANTIC_PDF=true` and parser import succeeds, semantic extraction is used.
- On parser failure, extraction falls back to text-only mode.

## Controls

- `USE_SEMANTIC_PDF`
- `INCLUDE_FIGURES_IN_TEXT`
- `INCLUDE_TABLES_IN_TEXT`
- `EXTRACT_PDF_IMAGES`
- `MAX_PDF_CHARS`
