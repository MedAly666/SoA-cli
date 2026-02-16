"""
SOA-CLI Core Modules

Production-grade multi-agent system for State of the Art generation.
"""

__version__ = "1.0.0"

from .theme_builder import (
    build_thematic_contract,
    load_thematic_contract,
    inject_theme_into_input,
    print_theme_summary,
    thematic_filter_paper,
    detect_theme_violation
)

from .vectorize import build_vector_db, get_embedder, load_vector_db
from .similarity_cluster import run_similarity_clustering
from .hallucination_detector import run_hallucination_checks
from .repair_loop import repair_pipeline

__all__ = [
    'build_thematic_contract',
    'load_thematic_contract',
    'inject_theme_into_input',
    'print_theme_summary',
    'thematic_filter_paper',
    'detect_theme_violation',
    'build_vector_db',
    'get_embedder',
    'load_vector_db',
    'run_similarity_clustering',
    'run_hallucination_checks',
    'repair_pipeline',
]
