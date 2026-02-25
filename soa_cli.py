#!/usr/bin/env python3
"""
SOA-CLI: Multi-Agent State of the Art Generator

Production-grade pipeline using LangGraph for fault-tolerant orchestration.
Automatically generates academically rigorous State of the Art sections from research papers.
"""

import os
import sys
import json  # Keep for state serialization compatibility
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.graph.builder import compile_graph
from src.graph.state import SOAState
from src.toon_utils import load_toon, dump_toon


def load_paper_paths(papers_dir: str = "papers") -> list[str]:
    """Load all PDF paths from papers directory."""
    papers_path = Path(papers_dir)
    if not papers_path.exists():
        raise FileNotFoundError(f"Papers directory not found: {papers_dir}")
    
    pdf_files = list(papers_path.glob("*.pdf"))
    
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {papers_dir}")
    
    return [str(p.absolute()) for p in sorted(pdf_files)]


def clear_artifacts():
    """Remove all artifacts to force a fresh run."""
    import shutil
    
    artifacts_dir = Path("artifacts")
    if artifacts_dir.exists():
        print("\n[Clean] Removing existing artifacts...")
        try:
            shutil.rmtree(artifacts_dir)
            print("  ✓ All artifacts cleared")
        except Exception as e:
            print(f"  ✗ Failed to clear artifacts: {e}")
            raise
    else:
        print("\n[Clean] No artifacts to clear")


def load_existing_artifacts(paper_paths: list[str]) -> tuple[dict, dict, dict, list[str]]:
    """
    Load existing artifacts and identify unprocessed papers.
    
    Args:
        paper_paths: List of all PDF paths
    
    Returns:
        Tuple of (reader_outputs, extracted_facts, critic_assessments, unprocessed_paper_paths)
    """
    reader_outputs = {}
    extracted_facts = {}
    critic_assessments = {}
    unprocessed_paths = []
    
    for path in paper_paths:
        paper_id = Path(path).stem
        
        # Check for existing artifacts (prefer .toon, fallback to .json)
        reader_file = Path(f"artifacts/reader/{paper_id}.toon")
        if not reader_file.exists():
            reader_file = Path(f"artifacts/reader/{paper_id}.json")
            
        extracted_file = Path(f"artifacts/extracted/{paper_id}.toon")
        if not extracted_file.exists():
            extracted_file = Path(f"artifacts/extracted/{paper_id}.json")
            
        critic_file = Path(f"artifacts/critic/{paper_id}.toon")
        if not critic_file.exists():
            critic_file = Path(f"artifacts/critic/{paper_id}.json")
        
        # Load reader output if exists
        if reader_file.exists():
            try:
                if reader_file.suffix == '.toon':
                    reader_outputs[paper_id] = load_toon(reader_file)
                else:
                    with open(reader_file, 'r', encoding='utf-8') as f:
                        reader_outputs[paper_id] = json.load(f)
            except (json.JSONDecodeError, IOError, Exception) as e:
                print(f"  ⚠ Corrupted reader output for {paper_id}, will reprocess")
                unprocessed_paths.append(path)
                continue
        else:
            unprocessed_paths.append(path)
            continue
        
        # Load extracted facts if exists
        if extracted_file.exists():
            try:
                if extracted_file.suffix == '.toon':
                    extracted_facts[paper_id] = load_toon(extracted_file)
                else:
                    with open(extracted_file, 'r', encoding='utf-8') as f:
                        extracted_facts[paper_id] = json.load(f)
            except (json.JSONDecodeError, IOError, Exception) as e:
                print(f"  ⚠ Corrupted extracted output for {paper_id}, will reprocess")
                if path not in unprocessed_paths:
                    unprocessed_paths.append(path)
                continue
        else:
            if path not in unprocessed_paths:
                unprocessed_paths.append(path)
            continue
        
        # Load critic assessment if exists
        if critic_file.exists():
            try:
                if critic_file.suffix == '.toon':
                    critic_assessments[paper_id] = load_toon(critic_file)
                else:
                    with open(critic_file, 'r', encoding='utf-8') as f:
                        critic_assessments[paper_id] = json.load(f)
            except (json.JSONDecodeError, IOError, Exception) as e:
                print(f"  ⚠ Corrupted critic output for {paper_id}, will reprocess")
                if path not in unprocessed_paths:
                    unprocessed_paths.append(path)
    
    return reader_outputs, extracted_facts, critic_assessments, unprocessed_paths


def create_initial_state(
    paper_paths: list[str], 
    max_repair: int = 3,
    existing_reader: dict = None,
    existing_extracted: dict = None,
    existing_critic: dict = None
) -> SOAState:
    """
    Create initial state for the graph.
    
    Args:
        paper_paths: List of PDF file paths (only unprocessed papers)
        max_repair: Maximum repair iterations
        existing_reader: Pre-loaded reader outputs
        existing_extracted: Pre-loaded extracted facts
        existing_critic: Pre-loaded critic assessments
    
    Returns:
        Initial state dictionary
    """
    return {
        # Inputs
        "thematic_contract": {},  # Will be populated by theme_builder
        "paper_paths": paper_paths,
        "max_repair_iterations": max_repair,
        
        # Collections (may have pre-loaded data)
        "reader_outputs": existing_reader or {},
        "extracted_facts": existing_extracted or {},
        "critic_assessments": existing_critic or {},
        "errors": [],
        
        # Single values
        "embeddings": None,
        "raw_clusters": None,
        "clusters": None,
        "synthesis": None,
        "soa_draft": None,
        
        # Verification
        "verification_results": None,
        "verification_passed": False,
        "repair_iteration": 0,
        
        # Metadata
        "pipeline_stage": "initialized",
        "total_papers": len(paper_paths) + len(existing_reader or {}),
        "processed_papers": len(existing_reader or {}),
    }


def run_pipeline(
    papers_dir: str = "papers",
    max_repair: int = 3,
    thread_id: str = "default",
    resume: bool = False
) -> dict:
    """
    Run the complete SOA pipeline with LangGraph.
    
    Args:
        papers_dir: Directory containing PDF papers
        max_repair: Maximum repair iterations
        thread_id: Unique ID for checkpointing
        resume: Whether to resume from checkpoint
    
    Returns:
        Final state dictionary
    """
    
    print("=" * 60)
    print("SOA-CLI with LangGraph")
    print("=" * 60)
    
    print(f"\n[Setup] Loading papers from {papers_dir}...")
    all_paper_paths = load_paper_paths(papers_dir)
    print(f"  Found {len(all_paper_paths)} papers")
    
    # Check for existing artifacts and load them
    print("\n[Setup] Checking for existing artifacts...")
    existing_reader, existing_extracted, existing_critic, unprocessed_paths = load_existing_artifacts(all_paper_paths)
    
    already_processed = len(existing_reader)
    need_processing = len(unprocessed_paths)
    
    if already_processed > 0:
        print(f"  ✓ Found {already_processed} already processed papers")
        print(f"  → Will process {need_processing} new/incomplete papers")
    else:
        print(f"  → No existing artifacts, will process all {need_processing} papers")
    
    # Create artifacts directory
    Path("artifacts").mkdir(exist_ok=True)
    
    # Compile graph
    print("\n[Setup] Compiling LangGraph...")
    app = compile_graph()
    
    # Create state with pre-loaded data
    config = {"configurable": {"thread_id": thread_id}}
    
    if not resume:
        print("\n[Setup] Creating initial state...")
        
        # Determine if we can skip to clustering
        skip_to_clustering = (need_processing == 0 and already_processed > 0)
        
        if skip_to_clustering:
            print("\n  ⚡ All papers already processed!")
            print("  → Skipping Reader/Extractor/Critic stages")
            print("  → Starting from Clustering stage")
        
        initial_state = create_initial_state(
            unprocessed_paths,  # Only unprocessed papers
            max_repair,
            existing_reader,    # Pre-loaded data
            existing_extracted,
            existing_critic
        )
        
        # Save initial state
        serializable_initial = {k: v for k, v in initial_state.items() if v is not None and k != 'embeddings'}
        dump_toon(serializable_initial, "artifacts/initial_state.toon")
    else:
        print("\n[Setup] Resuming from checkpoint...")
        initial_state = None  # Will load from checkpoint
    
    # Run graph
    print("\n" + "=" * 60)
    print("PIPELINE EXECUTION")
    print("=" * 60)
    
    if initial_state:
        final_state = app.invoke(initial_state, config)
    else:
        # Resume - need to get state from checkpoint
        # For now, just start fresh
        paper_paths_fresh = load_paper_paths(papers_dir)
        initial_state_fresh = create_initial_state(paper_paths_fresh, max_repair)
        final_state = app.invoke(initial_state_fresh, config)
    
    # Print summary
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    
    print(f"\nStage: {final_state.get('pipeline_stage', 'unknown')}")
    print(f"Papers processed: {final_state.get('processed_papers', 0)}/{final_state.get('total_papers', 0)}")
    print(f"Errors: {len(final_state.get('errors', []))}")
    print(f"Verification: {'PASSED' if final_state.get('verification_passed') else 'FAILED'}")
    print(f"Repair iterations: {final_state.get('repair_iteration', 0)}/{final_state.get('max_repair_iterations', 0)}")
    
    # Save final state
    output_file = "artifacts/final_state.toon"
    # Only save serializable parts
    serializable_state = {
        k: v for k, v in final_state.items()
        if k not in ['embeddings'] and v is not None
    }
    dump_toon(serializable_state, output_file)
    
    print(f"\n✓ Final state saved to {output_file}")
    
    # Save State of the Art
    soa_draft = final_state.get('soa_draft')
    if soa_draft:
        soa_file = "STATE_OF_THE_ART.tex"
        with open(soa_file, 'w', encoding='utf-8') as f:
            f.write(soa_draft)
        print(f"✓ State of the Art saved to {soa_file}")
    
    # Print errors if any
    errors = final_state.get('errors', [])
    if errors:
        print(f"\n⚠ {len(errors)} errors encountered:")
        for i, err in enumerate(errors[:5], 1):  # Show first 5
            print(f"  {i}. [{err.get('node', 'unknown')}] {err.get('error', 'unknown error')[:80]}...")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")
    
    return final_state


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="SOA-CLI: Automated State of the Art generation with LangGraph"
    )
    parser.add_argument(
        "--papers",
        type=str,
        default="papers",
        help="Directory containing PDF papers (default: papers)"
    )
    parser.add_argument(
        "--max-repair",
        type=int,
        default=3,
        help="Maximum repair iterations (default: 3)"
    )
    parser.add_argument(
        "--thread-id",
        type=str,
        default="default",
        help="Thread ID for checkpointing (default: default)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clear all artifacts before running (forces fresh run)"
    )
    
    args = parser.parse_args()
    
    # Clear artifacts if requested
    if args.clean:
        clear_artifacts()
    
    try:
        run_pipeline(
            papers_dir=args.papers,
            max_repair=args.max_repair,
            thread_id=args.thread_id,
            resume=args.resume
        )
    except Exception as e:
        print(f"\n✗ Pipeline failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
