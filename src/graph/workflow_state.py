from __future__ import annotations

from typing import TypedDict, Any


class SoAState(TypedDict, total=False):
    topic: str
    max_subtopics: int
    max_papers: int
    threshold: float
    chunk_size: int
    refinement_round: int
    max_refinement_rounds: int

    subtopics: list[str]
    subtopic_confidence_scores: list[float]
    venue_mapping: dict[str, list[str]]

    citations: list[dict[str, Any]]
    validated_citations: list[dict[str, Any]]
    citation_validation_errors: list[str]

    documents: list[dict[str, Any]]
    retrieval_failures: list[str]
    summaries: list[dict[str, Any]]

    ckm_memory: dict[str, dict[str, Any]]
    ckm_context: str
    query_citation_keys: list[str]

    partial_outlines: list[dict[str, Any]]
    merged_outline: dict[str, Any]
    outline_valid: bool
    outline_missing_citations: list[str]
    outline_validation_feedback: str

    draft: str
    citations_used: list[str]
    edited_content: str
    editor_changes: list[str]

    bibtex_entries: str
    completed_citations: list[dict[str, Any]]

    rubric_dimensions: dict[str, float]
    review_scores: list[float]
    review_feedback: list[dict[str, Any]]
    avg_score: float

    revision_plan: str
