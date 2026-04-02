from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.agents import (
    TopicExpansionAgent,
    DomainScopingAgent,
    CitationRetrievalAgent,
    CitationValidationAgent,
    RetrievalAgent,
    SummarizationAgent,
    CKMManagerAgent,
    OutlineDrafterAgent,
    OutlineMergerAgent,
    OutlineValidatorAgent,
    SectionWriterAgent,
    EditorAgent,
    CitationCompletionAgent,
    ReviewerPoolAgent,
    RefinementAgent,
)

from .workflow_state import SoAState


def create_soa_cli_graph():
    graph = StateGraph(SoAState)

    graph.add_node("topic_expansion", TopicExpansionAgent())
    graph.add_node("domain_scoping", DomainScopingAgent())
    graph.add_node("citation_retrieval", CitationRetrievalAgent())
    graph.add_node("citation_validation", CitationValidationAgent())

    graph.add_node("retrieval", RetrievalAgent())
    graph.add_node("summarization", SummarizationAgent())
    graph.add_node("ckm_manager", CKMManagerAgent())

    graph.add_node("outline_drafter", OutlineDrafterAgent())
    graph.add_node("outline_merger", OutlineMergerAgent())
    graph.add_node("outline_validator", OutlineValidatorAgent())

    graph.add_node("section_writer", SectionWriterAgent())
    graph.add_node("editor", EditorAgent())
    graph.add_node("citation_completion", CitationCompletionAgent())

    graph.add_node("reviewer_pool", ReviewerPoolAgent())
    graph.add_node("refinement", RefinementAgent())

    graph.set_entry_point("topic_expansion")

    graph.add_edge("topic_expansion", "domain_scoping")
    graph.add_edge("domain_scoping", "citation_retrieval")
    graph.add_edge("citation_retrieval", "citation_validation")
    graph.add_edge("citation_validation", "retrieval")
    graph.add_edge("retrieval", "summarization")
    graph.add_edge("summarization", "ckm_manager")
    graph.add_edge("ckm_manager", "outline_drafter")
    graph.add_edge("outline_drafter", "outline_merger")
    graph.add_edge("outline_merger", "outline_validator")
    graph.add_edge("outline_validator", "section_writer")
    graph.add_edge("section_writer", "editor")
    graph.add_edge("editor", "citation_completion")
    graph.add_edge("citation_completion", "reviewer_pool")

    graph.add_conditional_edges(
        "reviewer_pool",
        lambda state: "refinement"
        if (
            float(state.get("avg_score", 0.0)) < float(state.get("threshold", 4.0))
            and int(state.get("refinement_round", 0)) < int(state.get("max_refinement_rounds", 2))
        )
        else "END",
        {"refinement": "refinement", "END": END},
    )
    graph.add_edge("refinement", "reviewer_pool")

    return graph.compile()
