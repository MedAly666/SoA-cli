"""State schema for SOA-CLI LangGraph pipeline."""

from typing import TypedDict, Annotated, Optional
import operator


class SOAState(TypedDict):
    """
    Shared state for the entire SOA pipeline.
    
    LangGraph updates this state as it flows through nodes.
    Fields with Annotated[..., operator] are aggregated across updates.
    Plain fields use last-write-wins semantics.
    """
    
    # ===== IMMUTABLE INPUTS (set once) =====
    thematic_contract: dict  # Set by theme_builder, read by all agents
    paper_paths: list[str]   # Input PDF paths
    max_repair_iterations: int  # Maximum repair attempts
    
    # ===== AGGREGATING COLLECTIONS (use operator.or_ for dict merge) =====
    # These accumulate results across parallel operations
    reader_outputs: Annotated[dict[str, dict], operator.or_]
    extracted_facts: Annotated[dict[str, dict], operator.or_]
    critic_assessments: Annotated[dict[str, dict], operator.or_]
    
    # Error tracking (accumulates across all nodes)
    errors: Annotated[list[dict], operator.add]
    
    # ===== SINGLE-VALUE FIELDS (last write wins) =====
    # These get replaced wholesale by nodes
    embeddings: Optional[dict]  # Paper embeddings for clustering
    raw_clusters: Optional[dict]  # Precomputed similarity clusters
    clusters: Optional[dict]  # LLM-interpreted clusters
    synthesis: Optional[dict]  # Cross-paper synthesis
    synthesis_paper_coverage: float  # Fraction of extracted papers referenced in synthesis text (default 0.0)
    soa_draft: Optional[str]  # Current version of LaTeX SoA
    prisma_metadata: Optional[dict]  # PRISMA search methodology metadata (if papers auto-fetched)
    citation_graph: Optional[dict]  # Directed graph of citation + thematic links

    # ===== QUALITY SIGNALS =====
    rubric_scores: dict[str, float]  # Multi-dimensional quality scores
    rubric_failing: list[str]  # Dimensions scoring below threshold

    reflector_feedback: dict  # Multi-level reflector diagnostics
    reflector_passed_level: int  # 0..3, highest passed reflector level
    reflector_rewrite_attempts: int  # Number of writer rewrites triggered by reflector
    
    # ===== VERIFICATION & REPAIR =====
    verification_results: Optional[list[dict]]  # Hallucination violations
    verification_passed: bool  # True if no violations found
    hallucination_report: dict  # Verifier report payload (default {})
    repair_iteration: int  # Current repair attempt (0-indexed)

    # ===== TIMING =====
    pipeline_start_time: float  # Epoch seconds at pipeline start (default 0.0)
    stage_start_times: dict[str, float]  # Start timestamp per stage (default {})
    stage_durations: dict[str, float]  # Elapsed seconds per stage (default {})
    total_wall_clock_seconds: float  # End-to-end wall clock time (default 0.0)
    
    # ===== METADATA =====
    pipeline_stage: str  # Current stage name for logging
    total_papers: int  # Number of papers being processed
    processed_papers: int  # Number successfully processed
