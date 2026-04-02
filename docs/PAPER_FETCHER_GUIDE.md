# Paper Fetcher Guide

Paper fetcher logic exists in `src/paper_fetcher.py` and helper functions in `soa_cli.py`.

## Current CLI Status

The current `argparse` in `soa_cli.py` does not expose `--search-papers`, `--download-papers`, or `--prisma-report` flags.

## What Exists In Code

- `search_papers_command(...)`
- `download_papers_command()`
- `prisma_report_command()`

These can be re-exposed by adding CLI arguments in `main()` if needed.

## Practical Recommendation

For the current production path, place PDFs directly in `papers/` and run the main pipeline.
