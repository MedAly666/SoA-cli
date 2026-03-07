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
    soa_draft: Optional[str]  # Current version of LaTeX SoA
    prisma_metadata: Optional[dict]  # PRISMA search methodology metadata (if papers auto-fetched)
    
    # ===== VERIFICATION & REPAIR =====
    verification_results: Optional[list[dict]]  # Hallucination violations
    verification_passed: bool  # True if no violations found
    repair_iteration: int  # Current repair attempt (0-indexed)
    
    # ===== METADATA =====
    pipeline_stage: str  # Current stage name for logging
    total_papers: int  # Number of papers being processed
    processed_papers: int  # Number successfully processed
