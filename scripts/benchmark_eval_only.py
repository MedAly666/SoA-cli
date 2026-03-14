#!/usr/bin/env python3
"""Evaluate benchmark metrics from existing artifacts without re-running pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark import run_benchmark  # noqa: E402


if __name__ == "__main__":
    run_benchmark(run_pipeline=False, pipeline_cmd=None)
