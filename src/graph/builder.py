"""Build and compile the SOA-CLI LangGraph."""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import SOAState
from .nodes import (
    theme_builder_node,
    reader_map_node,
    extractor_map_node,
    critic_map_node,
    vectorize_node,
    cluster_node,
    interpret_clusters_node,
    synthesis_node,
    writer_node,
    verifier_node,
    repair_node,
)


def route_after_verification(state: SOAState) -> Literal["repair", "end"]:
    """
    Conditional routing after verification.
    
    Decision logic:
    - If verification passed → END
    - If iteration >= max → END (give up)
    - Otherwise → repair
    """
    passed = state.get("verification_passed", False)
    iteration = state.get("repair_iteration", 0)
    max_iterations = state.get("max_repair_iterations", 3)
    
    if passed:
        print(f"\n[Router] ✓ Verification passed → END")
        return "end"
    
    if iteration >= max_iterations:
        print(f"\n[Router] ✗ Max iterations reached ({iteration}/{max_iterations}) → END")
        return "end"
    
    print(f"\n[Router] → Repair (iteration {iteration + 1}/{max_iterations})")
    return "repair"


def build_graph() -> StateGraph:
    """
    Build the complete SOA-CLI pipeline graph.
    
    Graph structure:
        START
          ↓
        theme_builder
          ↓
        reader_map (parallel)
          ↓
        extractor_map (parallel)
          ↓
        critic_map (parallel)
          ↓
        vectorize
          ↓
        cluster
          ↓
        interpret_clusters
          ↓
        synthesis
          ↓
        writer
          ↓
        verifier
          ↓ [conditional]
        repair ←┐ (loop)
          ↓     │
        verifier┘ [conditional]
          ↓
        END
    """
    
    # Create graph
    workflow = StateGraph(SOAState)
    
    # Add all nodes
    workflow.add_node("theme_builder", theme_builder_node)
    workflow.add_node("reader_map", reader_map_node)
    workflow.add_node("extractor_map", extractor_map_node)
    workflow.add_node("critic_map", critic_map_node)
    workflow.add_node("vectorize", vectorize_node)
    workflow.add_node("cluster", cluster_node)
    workflow.add_node("interpret_clusters", interpret_clusters_node)
    workflow.add_node("synthesis", synthesis_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("repair", repair_node)
    
    # Linear edges (deterministic flow)
    workflow.set_entry_point("theme_builder")
    workflow.add_edge("theme_builder", "reader_map")
    workflow.add_edge("reader_map", "extractor_map")
    workflow.add_edge("extractor_map", "critic_map")
    workflow.add_edge("critic_map", "vectorize")
    workflow.add_edge("vectorize", "cluster")
    workflow.add_edge("cluster", "interpret_clusters")
    workflow.add_edge("interpret_clusters", "synthesis")
    workflow.add_edge("synthesis", "writer")
    workflow.add_edge("writer", "verifier")
    
    # Conditional edge after verification
    workflow.add_conditional_edges(
        "verifier",
        route_after_verification,
        {
            "repair": "repair",
            "end": END
        }
    )
    
    # Repair loops back to verifier
    workflow.add_edge("repair", "verifier")
    
    return workflow


def compile_graph(checkpointer=None):
    """
    Compile the graph with optional checkpointing.
    
    Args:
        checkpointer: Optional checkpointer (e.g., MemorySaver())
    
    Returns:
        Compiled LangGraph app
    """
    workflow = build_graph()
    
    if checkpointer is None:
        checkpointer = MemorySaver()
    
    app = workflow.compile(checkpointer=checkpointer)
    
    return app
