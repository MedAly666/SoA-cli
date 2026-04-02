# Artifacts Guide

In current DB-first mode, pipeline correctness does not depend on JSON artifact files between nodes.

## Still Produced

- `db_outputs/soa/state_of_the_art.md`
- `STATE_OF_THE_ART.md`
- optional logs/legacy files depending on helper scripts

## Legacy Artifact Folder

`artifacts/` may still be used by helper code and logs.

`python soa_cli.py --clean` removes files under `artifacts/` while preserving folder structure and `.gitkeep` files.
