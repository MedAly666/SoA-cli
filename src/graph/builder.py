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
    build_graph_node,
    cluster_node,
    interpret_clusters_node,
    synthesis_node,
    writer_node,
    reflector_node,
    rubric_evaluator_node,
    verifier_node,
    repair_node,
    final_output_node,
    figures_generator_node,
)


def route_after_verification(state: SOAState) -> Literal["repair", "final_output"]:
    """
    Conditional routing after verification.
    
    Decision logic:
    - If verification passed → final_output
    - If iteration >= max → final_output (give up)
    - Otherwise → repair
    """
    passed = state.get("verification_passed", False)
    iteration = state.get("repair_iteration", 0)
    max_iterations = state.get("max_repair_iterations", 3)
    
    if passed:
      print(f"\n[Router] ✓ Verification passed → Final Output")
      return "final_output"
    
    if iteration >= max_iterations:
      print(f"\n[Router] ✗ Max iterations reached ({iteration}/{max_iterations}) → Final Output")
      return "final_output"
    
    print(f"\n[Router] → Repair (iteration {iteration + 1}/{max_iterations})")
    return "repair"


def route_after_reflector(state: SOAState) -> Literal["writer", "rubric_evaluator"]:
    """
    Conditional routing after hierarchical reflector.

    Decision logic:
    - If reflector passes all 3 levels -> rubric_evaluator
    - If reflector fails and rewrite attempts < 2 -> writer
    - If rewrite attempts >= 2 -> rubric_evaluator (force forward)
    """
    passed_level = int(state.get("reflector_passed_level", 0))
    attempts = int(state.get("reflector_rewrite_attempts", 0))

    if passed_level >= 3:
        print("\n[Router] ✓ Reflector passed all levels -> Rubric Evaluator")
        return "rubric_evaluator"

    if attempts >= 2:
        print("\n[Router] ⚠ Reflector rewrite limit reached (2) -> Rubric Evaluator")
        return "rubric_evaluator"

    print(f"\n[Router] → Writer rewrite requested (attempt {attempts}/2)")
    return "writer"


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
        build_graph
          ↓
        cluster
          ↓
        interpret_clusters
          ↓
        synthesis
          ↓
        writer
          ↓
        reflector
          ↓ [conditional]
        writer (rewrite loop, max 2) OR rubric_evaluator
          ↓
        verifier
          ↓
        repair
          ↓
        verifier [conditional]
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
    workflow.add_node("build_graph", build_graph_node)
    workflow.add_node("cluster", cluster_node)
    workflow.add_node("interpret_clusters", interpret_clusters_node)
    workflow.add_node("synthesis", synthesis_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("reflector", reflector_node)
    workflow.add_node("rubric_evaluator", rubric_evaluator_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("repair", repair_node)
    workflow.add_node("final_output", final_output_node)
    workflow.add_node("figures_generator", figures_generator_node)
    
    # Linear edges (deterministic flow)
    workflow.set_entry_point("theme_builder")
    workflow.add_edge("theme_builder", "reader_map")
    workflow.add_edge("reader_map", "extractor_map")
    workflow.add_edge("extractor_map", "critic_map")
    workflow.add_edge("critic_map", "vectorize")
    workflow.add_edge("vectorize", "build_graph")
    workflow.add_edge("build_graph", "cluster")
    workflow.add_edge("cluster", "interpret_clusters")
    workflow.add_edge("interpret_clusters", "synthesis")
    workflow.add_edge("synthesis", "writer")
    workflow.add_edge("writer", "reflector")

    workflow.add_conditional_edges(
      "reflector",
      route_after_reflector,
      {
        "writer": "writer",
        "rubric_evaluator": "rubric_evaluator",
      }
    )

    workflow.add_edge("rubric_evaluator", "verifier")
    
    # Conditional edge after verification
    workflow.add_conditional_edges(
        "verifier",
        route_after_verification,
        {
            "repair": "repair",
        "final_output": "final_output"
        }
    )
    
    # Repair loops back to verifier
    workflow.add_edge("repair", "verifier")
    workflow.add_edge("final_output", "figures_generator")
    workflow.add_edge("figures_generator", END)
    
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
