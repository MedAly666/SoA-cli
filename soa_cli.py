#!/usr/bin/env python3
"""
SOA-CLI: Multi-Agent State of the Art Generator

Production-grade pipeline using LangGraph for fault-tolerant orchestration.
Automatically generates academically rigorous State of the Art sections from research papers.
"""

import os
import sys
import json  # Keep for state serialization compatibility
import time
import shutil
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.graph.builder import compile_graph
from src.graph.state import SOAState


def load_paper_paths(papers_dir: str = "papers", allow_empty: bool = False) -> list[str]:
    """Load all PDF paths from papers directory."""
    papers_path = Path(papers_dir)
    if not papers_path.exists():
        if allow_empty:
            # Create directory if it doesn't exist
            papers_path.mkdir(parents=True, exist_ok=True)
            return []
        raise FileNotFoundError(f"Papers directory not found: {papers_dir}")
    
    pdf_files = list(papers_path.glob("*.pdf"))
    
    if not pdf_files:
        if allow_empty:
            return []
        raise FileNotFoundError(f"No PDF files found in {papers_dir}")
    
    return [str(p.absolute()) for p in sorted(pdf_files)]


def clear_artifacts():
    """
    Clear all artifacts while preserving directory structure and .gitkeep files.
    Removes all files from artifacts/ subdirectories but keeps the folders themselves.
    """
    import shutil
    
    artifacts_dir = Path("artifacts")
    if not artifacts_dir.exists():
        print("\n[Clean] No artifacts to clear")
        return
    
    print("\n[Clean] Clearing artifact files (preserving folders and .gitkeep)...")
    
    # Directories to clean
    subdirs_to_clean = [
        "states",
        "prisma",
        "reader",
        "extracted",
        "extracted_facts",
        "extracted_filtered",
        "extractions",
        "critic",
        "clusters",
        "synthesis",
        "soa",
        "vector_db"
    ]
    
    files_deleted = 0
    
    # Clean each subdirectory
    for subdir in subdirs_to_clean:
        subdir_path = artifacts_dir / subdir
        if subdir_path.exists():
            # Delete all files except .gitkeep
            for item in subdir_path.iterdir():
                if item.is_file() and item.name != ".gitkeep":
                    try:
                        item.unlink()
                        files_deleted += 1
                    except Exception as e:
                        print(f"  ✗ Failed to delete {item}: {e}")
                elif item.is_dir():
                    # Recursively delete subdirectories (e.g., temp files)
                    try:
                        shutil.rmtree(item)
                        files_deleted += 1
                    except Exception as e:
                        print(f"  ✗ Failed to delete {item}: {e}")
    
    # Also clean root-level files in artifacts/ (except .gitkeep)
    for item in artifacts_dir.iterdir():
        if item.is_file() and item.name != ".gitkeep":
            try:
                item.unlink()
                files_deleted += 1
            except Exception as e:
                print(f"  ✗ Failed to delete {item}: {e}")
    
    print(f"  ✓ Cleared {files_deleted} artifact files")
    print(f"  ✓ Preserved folder structure and .gitkeep files")


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
        
        # Check for existing artifacts (JSON only)
        reader_file = Path(f"artifacts/reader/{paper_id}.json")
        extracted_file = Path(f"artifacts/extracted/{paper_id}.json")
        critic_file = Path(f"artifacts/critic/{paper_id}.json")
        
        # Load reader output if exists
        if reader_file.exists():
            try:
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
    existing_reader: Optional[dict] = None,
    existing_extracted: Optional[dict] = None,
    existing_critic: Optional[dict] = None,
    prisma_metadata: Optional[dict] = None
) -> SOAState:
    """
    Create initial state for the graph.
    
    Args:
        paper_paths: List of PDF file paths (only unprocessed papers)
        max_repair: Maximum repair iterations
        existing_reader: Pre-loaded reader outputs
        existing_extracted: Pre-loaded extracted facts
        existing_critic: Pre-loaded critic assessments
        prisma_metadata: PRISMA search methodology metadata (if papers auto-fetched)
    
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
        "synthesis_paper_coverage": 0.0,
        "soa_draft": None,
        "citation_map": {},
        "db_run_id": "",
        "prisma_metadata": prisma_metadata,
        "citation_graph": None,

        # Quality signals
        "rubric_scores": {},
        "rubric_failing": [],
        "reflector_feedback": {},
        "reflector_passed_level": 0,
        "reflector_rewrite_attempts": 0,
        
        # Verification
        "verification_results": None,
        "verification_passed": False,
        "hallucination_report": {},
        "repair_iteration": 0,

        # Timing
        "pipeline_start_time": 0.0,
        "stage_start_times": {},
        "stage_durations": {},
        "total_wall_clock_seconds": 0.0,
        
        # Metadata
        "pipeline_stage": "initialized",
        "total_papers": len(paper_paths) + len(existing_reader or {}),
        "processed_papers": len(existing_reader or {}),
    }


def run_pipeline(
    papers_dir: str = "papers",
    max_repair: int = 3,
    thread_id: str = "default",
    resume: bool = False,
    output_format: str = "markdown"
) -> dict:
    """
    Run the complete SOA pipeline with LangGraph.
    
    Args:
        papers_dir: Directory containing PDF papers
        max_repair: Maximum repair iterations
        thread_id: Unique ID for checkpointing
        resume: Whether to resume from checkpoint
        output_format: Output format (latex, markdown, docx, or all)
    
    Returns:
        Final state dictionary
    """
    
    print("=" * 60)
    print("SOA-CLI with LangGraph")
    print("=" * 60)
    
    print(f"\n[Setup] Loading papers from {papers_dir}...")
    all_paper_paths = load_paper_paths(papers_dir, allow_empty=True)
    
    prisma_metadata = None
    
    # If no papers found, trigger automatic paper search
    if not all_paper_paths:
        print(f"  ⚠️  No papers found in {papers_dir}")
        print("\n" + "="*60)
        print("AUTOMATIC PAPER SEARCH")
        print("="*60)
        print("\nNo papers detected. Initiating PRISMA paper search...")
        
        try:
            # Run paper search
            search_papers_command(auto_download=False)
            
            print("\n" + "="*60)
            print("PAPER SEARCH COMPLETE - ACTION REQUIRED")
            print("="*60)
            print("\n📋 Next steps:")
            print("  1. Review candidates: paper_candidates.json")
            print("  2. Edit 'status' field: 'approved' or 'rejected'")
            print("  3. Download papers: python soa_cli.py --download-papers")
            print("  4. Run pipeline again: python soa_cli.py")
            print("\nExiting. Please review candidates and download papers.\n")
            sys.exit(0)
        
        except Exception as e:
            print(f"\n✗ Paper search failed: {e}")
            print("\nAlternatives:")
            print(f"  1. Manually add PDFs to {papers_dir}/")
            print(f"  2. Run: python soa_cli.py --search-papers")
            print(f"  3. Fix the error and try again\n")
            sys.exit(1)
    
    print(f"  Found {len(all_paper_paths)} papers")
    
    # DB mode processes from current paper set and keeps state in DB + in-memory graph state.
    unprocessed_paths = all_paper_paths
    existing_reader = {}
    existing_extracted = {}
    existing_critic = {}
    
    # Compile graph
    print("\n[Setup] Compiling LangGraph...")
    app = compile_graph()
    
    # Create state with pre-loaded data
    config = {"configurable": {"thread_id": thread_id}}
    
    if not resume:
        print("\n[Setup] Creating initial state...")
        
        initial_state = create_initial_state(
            unprocessed_paths,  # Only unprocessed papers
            max_repair,
            existing_reader,    # Pre-loaded data
            existing_extracted,
            existing_critic,
            prisma_metadata     # PRISMA metadata if available
        )

        # Runtime timing initialization before graph invocation.
        initial_state["pipeline_start_time"] = time.time()
        initial_state["stage_start_times"] = {}
        initial_state["stage_durations"] = {}
        initial_state["total_wall_clock_seconds"] = 0.0
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
        initial_state_fresh["pipeline_start_time"] = time.time()
        initial_state_fresh["stage_start_times"] = {}
        initial_state_fresh["stage_durations"] = {}
        initial_state_fresh["total_wall_clock_seconds"] = 0.0
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
    
    # Export final markdown only.
    soa_draft = final_state.get('soa_draft')
    if soa_draft:
        print("\n[Export] Generating markdown output...")
        output_dir = "db_outputs/soa"
        fallback_output_dir = "db_outputs/soa"
        markdown_path = Path(output_dir) / "state_of_the_art.md"

        if not markdown_path.exists():
            alt = Path(fallback_output_dir) / "state_of_the_art.md"
            if alt.exists():
                markdown_path = alt

        if markdown_path.exists():
            shutil.copy2(markdown_path, "STATE_OF_THE_ART.md")
        else:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            with open(Path(output_dir) / "state_of_the_art.md", 'w', encoding='utf-8') as f:
                f.write(str(soa_draft))
            with open("STATE_OF_THE_ART.md", 'w', encoding='utf-8') as f:
                f.write(str(soa_draft))
        print("✓ Markdown: STATE_OF_THE_ART.md")
    
    # Print errors if any
    errors = final_state.get('errors', [])
    if errors:
        print(f"\n⚠ {len(errors)} errors encountered:")
        for i, err in enumerate(errors[:5], 1):  # Show first 5
            print(f"  {i}. [{err.get('node', 'unknown')}] {err.get('error', 'unknown error')[:80]}...")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")
    
    return final_state


def search_papers_command(auto_download: bool = False):
    """Execute paper search with PRISMA methodology."""
    from src.paper_fetcher import PRISMAPaperFetcher
    from src.theme_builder import ensure_theme_input, build_thematic_contract
    
    print("\n" + "="*80)
    print("PRISMA PAPER SEARCH")
    print("="*80)
    
    # Ensure theme_input.json exists
    print("\n[Setup] Loading thematic contract...")
    user_input_file = "theme_input.json"
    
    try:
        # Use None to let functions create their own LLMClient with proper settings
        user_input = ensure_theme_input(user_input_file, model=None)
        
        # Build thematic contract (pass filename, not dict)
        contract = build_thematic_contract(user_input_file, model=None)
        print(f"  ✓ Theme: {contract.get('global_theme', 'N/A')}")
    
    except Exception as e:
        print(f"\n✗ Failed to load thematic contract: {e}")
        sys.exit(1)
    
    # Load paper fetcher configuration from environment
    config = {
        'sources': os.getenv('PAPER_SOURCES', 'semantic_scholar,arxiv').split(','),
        'max_papers': int(os.getenv('PAPER_MAX_RESULTS', '50')),
        'min_year': int(os.getenv('PAPER_MIN_YEAR', '2015')),
        'min_citations': int(os.getenv('PAPER_MIN_CITATIONS', '10')),
        'require_venue_whitelist': os.getenv('PAPER_REQUIRE_WHITELIST', 'true').lower() == 'true'
    }
    
    print("\n[Config]:")
    print(f"  Sources: {', '.join(config['sources'])}")
    print(f"  Max papers: {config['max_papers']}")
    print(f"  Min year: {config['min_year']}")
    print(f"  Min citations: {config['min_citations']}")
    print(f"  Venue whitelist: {'Required' if config['require_venue_whitelist'] else 'Optional'}")
    
    # Run PRISMA search
    fetcher = PRISMAPaperFetcher(contract, config)
    report = fetcher.run_systematic_search(auto_download=auto_download)
    
    print("\n" + "="*80)
    print("✓ PAPER SEARCH COMPLETE")
    print("="*80)
    
    return report


def download_papers_command():
    """Download approved papers from candidates file."""
    from src.paper_fetcher import PRISMAPaperFetcher, PaperCandidate
    
    print("\n" + "="*80)
    print("DOWNLOAD APPROVED PAPERS")
    print("="*80)
    
    candidates_file = "paper_candidates.json"
    
    if not Path(candidates_file).exists():
        print(f"\n✗ Candidates file not found: {candidates_file}")
        print("  Run --search-papers first to generate candidates")
        sys.exit(1)
    
    # Load candidates
    with open(candidates_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    candidates = data.get('candidates', [])
    
    # Filter approved papers
    approved = [c for c in candidates if c.get('status') == 'approved']
    
    if not approved:
        print(f"\n⚠ No approved papers found in {candidates_file}")
        print("  Edit the 'status' field to 'approved' for papers you want to download")
        sys.exit(0)
    
    print(f"\n[Download] Found {len(approved)} approved papers")
    
    # Convert to PaperCandidate objects
    from dataclasses import fields
    paper_objects = []
    
    for c in approved:
        # Only pass fields that exist in PaperCandidate
        valid_fields = {f.name for f in fields(PaperCandidate)}
        filtered_data = {k: v for k, v in c.items() if k in valid_fields}
        
        try:
            paper = PaperCandidate(**filtered_data)
            paper_objects.append(paper)
        except Exception as e:
            print(f"  ⚠ Error loading paper '{c.get('title', 'Unknown')}': {e}")
    
    # Download papers
    dummy_config = {'sources': [], 'max_papers': 0}
    fetcher = PRISMAPaperFetcher({}, dummy_config)
    
    included = fetcher.inclusion_stage(paper_objects)
    
    print(f"\n✓ Successfully downloaded {len(included)} papers to papers/")
    
    # Update candidates file with download status
    for candidate in candidates:
        for paper in included:
            if candidate.get('title') == paper.title:
                candidate['status'] = 'included'
                candidate['pdf_path'] = paper.pdf_path
    
    with open(candidates_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Candidates file updated: {candidates_file}")


def prisma_report_command():
    """Generate PRISMA report from candidates file."""
    print("\n" + "="*80)
    print("GENERATE PRISMA REPORT")
    print("="*80)
    
    candidates_file = "paper_candidates.json"
    
    if not Path(candidates_file).exists():
        print(f"\n✗ Candidates file not found: {candidates_file}")
        print("  Run --search-papers first to generate candidates")
        sys.exit(1)
    
    # Load candidates
    with open(candidates_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metadata = data.get('search_metadata', {})
    
    # Reconstruct report from metadata
    report = {
        "identification": {
            "total_records": metadata.get('total_identified', 0),
            "by_source": {},
            "search_date": metadata.get('search_date', ''),
            "queries": metadata.get('queries_used', [])
        },
        "screening": {
            "duplicates_removed": metadata.get('duplicates_removed', 0),
            "records_screened": metadata.get('screened', 0),
            "excluded_abstract": 0
        },
        "eligibility": {
            "full_text_assessed": metadata.get('screened', 0),
            "excluded_full_text": 0
        },
        "included": {
            "total_included": metadata.get('eligible', 0)
        }
    }
    
    # Count exclusions
    candidates = data.get('candidates', [])
    for c in candidates:
        if c.get('status') == 'excluded':
            if c.get('exclusion_stage') == 'screening':
                report['screening']['excluded_abstract'] += 1
            else:
                report['eligibility']['excluded_full_text'] += 1
    
    # Save report
    Path("artifacts").mkdir(exist_ok=True)
    with open("artifacts/prisma_report.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✓ PRISMA report saved: artifacts/prisma_report.json")
    
    # Generate flow diagram (simplified version without full fetcher)
    from src.paper_fetcher import PRISMAPaperFetcher
    fetcher = PRISMAPaperFetcher({}, {})
    fetcher.generate_prisma_flow_diagram(report)
    
    print("\n✓ PRISMA REPORT COMPLETE")


def main():
    """Main entry point."""
    import argparse
    from src.llm_client import verify_provider_or_exit
    
    # Verify LLM provider CLI is available
    provider = os.getenv('LLM_PROVIDER', 'qwen')
    verify_provider_or_exit(provider)
    
    parser = argparse.ArgumentParser(
        description="SOA-CLI: Automated State of the Art generation with LangGraph"
    )
    
    # Main pipeline arguments
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
    parser.add_argument(
        "--clusters",
        type=str,
        default="auto",
        help="Number of clusters (default: auto-detect using silhouette analysis, or specify integer)"
    )
    parser.add_argument(
        "--format",
        type=str,
        default="markdown",
        choices=["markdown"],
        help="Output format (markdown only in DB-first mode)."
    )
    
    args = parser.parse_args()
    
    # Parse clusters argument for main pipeline
    if args.clusters.lower() == 'auto':
        clusters = None  # Auto-detect
    else:
        try:
            clusters = int(args.clusters)
        except ValueError:
            print(f"Error: --clusters must be 'auto' or an integer, got '{args.clusters}'")
            sys.exit(1)
    
    # Set CLUSTER_COUNT environment variable for pipeline
    if clusters is not None:
        os.environ['CLUSTER_COUNT'] = str(clusters)
    else:
        os.environ['CLUSTER_COUNT'] = 'auto'  # Signal auto-detection
    
    # Clear artifacts if requested
    if args.clean:
        clear_artifacts()
    
    try:
        run_pipeline(
            papers_dir=args.papers,
            max_repair=args.max_repair,
            thread_id=args.thread_id,
            resume=args.resume,
            output_format=args.format
        )
    except Exception as e:
        print(f"\n✗ Pipeline failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
