# Multimodal PDF Notes

Current runtime supports semantic extraction of figures/tables metadata through `src/pdf_parser.py`.

What it does not currently do in the core pipeline:
- No separate multimodal vision reasoning stage is enforced in graph nodes.
- No mandatory image-to-text model pass beyond what parser and prompts provide.

This page remains as a compatibility note; the authoritative behavior is in `src/graph/nodes.py`.
