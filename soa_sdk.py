#!/usr/bin/env python3
"""
SOA-SDK: State of the Art Generation SDK

Multi-provider LLM support with LangGraph orchestration.
Supports GPT, Claude, Gemini, DeepSeek, Qwen, GLM, Ollama, and more.

Usage as SDK:
    from soa_sdk import SOAEngine
    
    engine = SOAEngine(provider="openai", model="gpt-4")
    result = engine.process_papers(paper_paths, config)

Usage as CLI:
    python soa_sdk.py --papers papers/ --provider openai --model gpt-4
"""

import os
import sys
import json  # Keep for state serialization compatibility
import logging
import time
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize logging
from src.logging_config import setup_logging, log_environment_config, get_logger
logger = setup_logging()
log_environment_config(logger)

from src.graph.builder import compile_graph
from src.graph.state import SOAState
from src.toon_utils import load_toon, dump_toon


class SOAEngine:
    """
    SDK interface for State of the Art generation.
    
    Examples:
        # Basic usage with default provider (Qwen)
        >>> engine = SOAEngine()
        >>> result = engine.process("papers/")
        
        # With specific provider
        >>> engine = SOAEngine(provider="openai", model="gpt-4")
        >>> result = engine.process("papers/", max_repair=5)
        
        # From paper paths
        >>> engine = SOAEngine(provider="claude", model="claude-3-opus-20240229")
        >>> result = engine.process_papers(
        ...     paper_paths=["paper1.pdf", "paper2.pdf"],
        ...     max_repair=3
        ... )
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **config
    ):
        """
        Initialize SOA Engine.
        
        Args:
            provider: LLM provider (openai, claude, gemini, deepseek, qwen, glm, ollama)
            model: Model name (e.g., gpt-4, claude-3-opus, gemini-pro)
            **config: Additional configuration options
        """
        self.provider = provider or os.getenv("LLM_PROVIDER", "qwen")
        self.model = model or os.getenv("LLM_MODEL", "qwen-turbo")
        self.config = config
        
        # Set in environment for downstream components
        os.environ["LLM_PROVIDER"] = self.provider
        os.environ["LLM_MODEL"] = self.model
    
    def process(
        self,
        papers_dir: str,
        max_repair: int = 3,
        thread_id: str = "default",
        resume: bool = False,
        clusters: Optional[int] = None,
        output_format: str = "latex"
    ) -> dict:
        """
        Process papers from directory.
        
        Args:
            papers_dir: Directory containing PDF papers
            max_repair: Maximum repair iterations
            thread_id: Unique ID for checkpointing
            resume: Whether to resume from checkpoint
            clusters: Number of clusters (None = auto-detect)
            output_format: Output format (latex, markdown, docx, or all)
        
        Returns:
            Final state dictionary with results
        """
        return run_pipeline(
            papers_dir=papers_dir,
            max_repair=max_repair,
            thread_id=thread_id,
            resume=resume,
            provider=self.provider,
            model=self.model,
            clusters=clusters,
            output_format=output_format
        )
    
    def process_papers(
        self,
        paper_paths: list[str],
        max_repair: int = 3,
        thread_id: str = "default",
        clusters: Optional[int] = None,
        output_format: str = "latex"
    ) -> dict:
        """
        Process specific paper files.
        
        Args:
            paper_paths: List of PDF file paths
            max_repair: Maximum repair iterations
            thread_id: Unique ID for checkpointing
            clusters: Number of clusters (None = auto-detect)
            output_format: Output format (latex, markdown, docx, or all)
        
        Returns:
            Final state dictionary with results
        """
        # Create temporary directory with symlinks to papers
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Copy/link papers to temp dir
            for paper in paper_paths:
                src = Path(paper)
                dst = Path(tmpdir) / src.name
                shutil.copy2(src, dst)
            
            return self.process(
                papers_dir=tmpdir,
                max_repair=max_repair,
                thread_id=thread_id,
                clusters=clusters,
                output_format=output_format
            )


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
    resume: bool = False,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    clusters: Optional[int] = None,
    output_format: str = "latex"
) -> dict:
    """
    Run the complete SOA pipeline with LangGraph.
    
    Args:
        papers_dir: Directory containing PDF papers
        max_repair: Maximum repair iterations
        thread_id: Unique ID for checkpointing
        resume: Whether to resume from checkpoint
        provider: LLM provider (openai, claude, gemini, deepseek, qwen, glm, ollama)
        model: Model name (e.g., gpt-4, claude-3-opus-20240229, gemini-pro)
        clusters: Number of clusters (None = auto-detect using silhouette score)
        output_format: Output format (latex, markdown, docx, or all)
    
    Returns:
        Final state dictionary
    """
    pipeline_start_time = time.time()
    
    logger.info("\n" + "="*90)
    logger.info("SOA-SDK PIPELINE EXECUTION")
    logger.info("="*90)
    
    # Set LLM provider/model in environment if specified
    if provider:
        os.environ["LLM_PROVIDER"] = provider
        logger.info(f"LLM Provider set to: {provider}")
    if model:
        os.environ["LLM_MODEL"] = model
        logger.info(f"LLM Model set to: {model}")
    if clusters is not None:
        os.environ["CLUSTER_COUNT"] = str(clusters)
        logger.info(f"Cluster count manually set to: {clusters}")
    
    # Get effective provider and model
    effective_provider = os.getenv("LLM_PROVIDER", "qwen")
    effective_model = os.getenv("LLM_MODEL", "qwen-turbo")
    
    print("=" * 60)
    print("SOA-SDK: State of the Art Generation")
    print("=" * 60)
    print(f"LLM Provider: {effective_provider}")
    print(f"Model: {effective_model}")
    
    logger.info(f"Pipeline Configuration:")
    logger.info(f"  Papers Directory: {papers_dir}")
    logger.info(f"  Max Repair Iterations: {max_repair}")
    logger.info(f"  Thread ID: {thread_id}")
    logger.info(f"  Resume Mode: {resume}")
    logger.info(f"  Output Format: {output_format}")
    logger.info(f"  Cluster Count: {'AUTO-DETECT' if clusters is None else clusters}")
    
    print(f"\n[Setup] Loading papers from {papers_dir}...")
    logger.info(f"Loading papers from: {papers_dir}")
    all_paper_paths = load_paper_paths(papers_dir)
    print(f"  Found {len(all_paper_paths)} papers")
    logger.info(f"Found {len(all_paper_paths)} paper(s)")
    
    for i, path in enumerate(all_paper_paths, 1):
        logger.debug(f"  Paper {i}: {Path(path).name}")
    
    # Check for existing artifacts and load them
    print("\n[Setup] Checking for existing artifacts...")
    logger.info("Checking for existing artifacts...")
    existing_reader, existing_extracted, existing_critic, unprocessed_paths = load_existing_artifacts(all_paper_paths)
    
    already_processed = len(existing_reader)
    need_processing = len(unprocessed_paths)
    
    if already_processed > 0:
        print(f"  ✓ Found {already_processed} already processed papers")
        print(f"  → Will process {need_processing} new/incomplete papers")
        logger.info(f"Existing artifacts found: {already_processed} papers")
        logger.info(f"Need to process: {need_processing} papers")
        for paper_id in existing_reader.keys():
            logger.debug(f"  Already processed: {paper_id}")
    else:
        print(f"  → No existing artifacts, will process all {need_processing} papers")
        logger.info(f"No existing artifacts found. Processing all {need_processing} papers")
    
    # Create artifacts directory
    Path("artifacts").mkdir(exist_ok=True)
    
    # Compile graph
    print("\n[Setup] Compiling LangGraph...")
    logger.info("Compiling LangGraph pipeline...")
    app = compile_graph()
    logger.info("LangGraph compiled successfully")
    
    # Create state with pre-loaded data
    config = {"configurable": {"thread_id": thread_id}}
    
    if not resume:
        print("\n[Setup] Creating initial state...")
        logger.info("Creating initial pipeline state...")
        
        # Determine if we can skip to clustering
        skip_to_clustering = (need_processing == 0 and already_processed > 0)
        
        if skip_to_clustering:
            print("\n  ⚡ All papers already processed!")
            print("  → Skipping Reader/Extractor/Critic stages")
            print("  → Starting from Clustering stage")
            logger.info("All papers already processed - skipping to clustering stage")
        
        initial_state = create_initial_state(
            unprocessed_paths,  # Only unprocessed papers
            max_repair,
            existing_reader,    # Pre-loaded data
            existing_extracted,
            existing_critic
        )
        
        logger.debug(f"Initial state created:")
        logger.debug(f"  Paper paths: {len(unprocessed_paths)}")
        logger.debug(f"  Existing reader outputs: {len(existing_reader)}")
        logger.debug(f"  Existing extracted facts: {len(existing_extracted)}")
        logger.debug(f"  Existing critic assessments: {len(existing_critic)}")
        
        # Save initial state
        serializable_initial = {k: v for k, v in initial_state.items() if v is not None and k != 'embeddings'}
        dump_toon(serializable_initial, "artifacts/initial_state.toon")
        logger.info("Initial state saved to artifacts/initial_state.toon")
    else:
        print("\n[Setup] Resuming from checkpoint...")
        logger.info("Resume mode enabled - loading from checkpoint")
        initial_state = None  # Will load from checkpoint
    
    # Run graph
    print("\n" + "=" * 60)
    print("PIPELINE EXECUTION")
    print("=" * 60)
    logger.info("\n" + "="*90)
    logger.info("STARTING PIPELINE EXECUTION")
    logger.info("="*90)
    
    if initial_state:
        logger.info("Invoking LangGraph with initial state...")
        execution_start_time = time.time()
        final_state = app.invoke(initial_state, config)
        execution_duration = time.time() - execution_start_time
        logger.info(f"LangGraph execution completed in {execution_duration:.2f}s")
    else:
        # Resume - need to get state from checkpoint
        # For now, just start fresh
        logger.info("Resuming execution - loading fresh state")
        paper_paths_fresh = load_paper_paths(papers_dir)
        initial_state_fresh = create_initial_state(paper_paths_fresh, max_repair)
        execution_start_time = time.time()
        final_state = app.invoke(initial_state_fresh, config)
        execution_duration = time.time() - execution_start_time
        logger.info(f"LangGraph execution completed in {execution_duration:.2f}s")
    
    # Print summary
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    
    final_stage = final_state.get('pipeline_stage', 'unknown')
    processed = final_state.get('processed_papers', 0)
    total = final_state.get('total_papers', 0)
    errors = final_state.get('errors', [])
    verification_passed = final_state.get('verification_passed', False)
    repair_iteration = final_state.get('repair_iteration', 0)
    max_repairs = final_state.get('max_repair_iterations', 0)
    
    print(f"\nStage: {final_stage}")
    print(f"Papers processed: {processed}/{total}")
    print(f"Errors: {len(errors)}")
    print(f"Verification: {'PASSED' if verification_passed else 'FAILED'}")
    print(f"Repair iterations: {repair_iteration}/{max_repairs}")
    
    logger.info("\n" + "="*90)
    logger.info("PIPELINE EXECUTION COMPLETE")
    logger.info("="*90)
    logger.info(f"Final Stage: {final_stage}")
    logger.info(f"Papers Processed: {processed}/{total}")
    logger.info(f"Errors Encountered: {len(errors)}")
    logger.info(f"Verification Status: {'PASSED' if verification_passed else 'FAILED'}")
    logger.info(f"Repair Iterations: {repair_iteration}/{max_repairs}")
    
    if errors:
        logger.warning(f"Errors during pipeline execution:")
        for i, error in enumerate(errors, 1):
            logger.warning(f"  Error {i}: {error.get('node', 'unknown')} - {error.get('error', 'no details')}")
    
    # Save final state
    output_file = "artifacts/final_state.toon"
    # Only save serializable parts
    serializable_state = {
        k: v for k, v in final_state.items()
        if k not in ['embeddings'] and v is not None
    }
    dump_toon(serializable_state, output_file)
    
    print(f"\n✓ Final state saved to {output_file}")
    logger.info(f"Final state saved to: {output_file}")
    logger.debug(f"Final state size: {len(str(serializable_state)):,} chars")
    
    # Save State of the Art in requested format(s)
    soa_draft = final_state.get('soa_draft')
    if soa_draft:
        logger.info(f"Exporting State of the Art document in '{output_format}' format...")
        from src.exporter import SOAExporter
        
        exporter = SOAExporter()
        output_dir = "artifacts/soa"
        base_name = "state_of_the_art_final"
        
        print(f"\n[Export] Generating output in '{output_format}' format...")
        
        if output_format == "all":
            # Export to all formats
            logger.info("Exporting to all formats (LaTeX, Markdown, Word)")
            latex_path = f"{base_name}.tex"
            md_path = f"{output_dir}/{base_name}.md"
            docx_path = f"{output_dir}/{base_name}.docx"
            
            # LaTeX (root directory for compatibility)
            export_start = time.time()
            with open(latex_path, 'w', encoding='utf-8') as f:
                f.write(soa_draft)
            print(f"  ✓ LaTeX: {latex_path}")
            logger.info(f"  ✓ LaTeX exported: {latex_path} (took {time.time() - export_start:.2f}s)")
            
            # Also save in artifacts
            exporter.to_latex(soa_draft, f"{output_dir}/{base_name}.tex")
            
            export_start = time.time()
            exporter.to_markdown(soa_draft, md_path)
            print(f"  ✓ Markdown: {md_path}")
            logger.info(f"  ✓ Markdown exported: {md_path} (took {time.time() - export_start:.2f}s)")
            
            try:
                export_start = time.time()
                exporter.to_docx(soa_draft, docx_path)
                print(f"  ✓ Word: {docx_path}")
                logger.info(f"  ✓ Word exported: {docx_path} (took {time.time() - export_start:.2f}s)")
            except RuntimeError as e:
                print(f"  ! Skipping .docx: {e}")
                logger.warning(f"Skipping Word export: {e}")
                
        elif output_format == "latex":
            # LaTeX only (root directory for compatibility)
            logger.info("Exporting LaTeX format only")
            export_start = time.time()
            soa_file = "STATE_OF_THE_ART.tex"
            with open(soa_file, 'w', encoding='utf-8') as f:
                f.write(soa_draft)
            print(f"  ✓ LaTeX: {soa_file}")
            logger.info(f"  ✓ LaTeX exported: {soa_file} (took {time.time() - export_start:.2f}s)")
            # Also save in artifacts
            exporter.to_latex(soa_draft, f"{output_dir}/{base_name}.tex")
            
        elif output_format == "markdown":
            logger.info("Exporting Markdown format only")
            export_start = time.time()
            md_path = f"{output_dir}/{base_name}.md"
            exporter.to_markdown(soa_draft, md_path)
            # Also save main output
            with open("STATE_OF_THE_ART.md", 'w', encoding='utf-8') as f:
                # Convert and save
                from src.exporter import SOAExporter
                temp_exporter = SOAExporter()
                md_content = temp_exporter._latex_to_markdown(soa_draft)
                f.write(md_content)
            print(f"  ✓ Markdown: STATE_OF_THE_ART.md")
            logger.info(f"  ✓ Markdown exported: STATE_OF_THE_ART.md (took {time.time() - export_start:.2f}s)")
            
        elif output_format == "docx":
            logger.info("Exporting Word format only")
            export_start = time.time()
            docx_path = f"{output_dir}/{base_name}.docx"
            try:
                exporter.to_docx(soa_draft, docx_path)
                # Copy to root
                import shutil
                shutil.copy(docx_path, "STATE_OF_THE_ART.docx")
                print(f"  ✓ Word: STATE_OF_THE_ART.docx")
                logger.info(f"  ✓ Word exported: STATE_OF_THE_ART.docx (took {time.time() - export_start:.2f}s)")
            except RuntimeError as e:
                print(f"  ✗ Failed to export Word: {e}")
                print(f"    Install python-docx: pip install python-docx")
                logger.error(f"Failed to export Word: {e}")
    else:
        logger.warning("No SOA draft found in final state - cannot export")
    
    # Print errors if any
    errors = final_state.get('errors', [])
    if errors:
        print(f"\n⚠ {len(errors)} errors encountered:")
        for i, err in enumerate(errors[:5], 1):  # Show first 5
            print(f"  {i}. [{err.get('node', 'unknown')}] {err.get('error', 'unknown error')[:80]}...")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")
    
    # Calculate and log total pipeline duration
    total_duration = time.time() - pipeline_start_time
    logger.info(f"\n{'='*90}")
    logger.info(f"PIPELINE SUMMARY")
    logger.info(f"{'='*90}")
    logger.info(f"Total Duration: {total_duration:.2f}s ({total_duration/60:.1f} minutes)")
    logger.info(f"Papers Processed: {processed}/{total}")
    logger.info(f"Final Stage: {final_stage}")
    logger.info(f"Verification: {'✓ PASSED' if verification_passed else '✗ FAILED'}")
    logger.info(f"Errors: {len(errors)}")
    logger.info(f"Output Format: {output_format}")
    logger.info(f"{'='*90}\n")
    
    print(f"\n{'='*60}")
    print(f"Total Duration: {total_duration:.2f}s ({total_duration/60:.1f} minutes)")
    print(f"{'='*60}\n")
    
    logger.info("Pipeline execution finished successfully")
    logger.info(f"Log file: {[h.baseFilename for h in logger.handlers if hasattr(h, 'baseFilename')][0]}")
    
    return final_state


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="SOA-SDK: Automated State of the Art generation with multi-provider LLM support"
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
        "--provider",
        type=str,
        default=None,
        help="LLM provider (openai, claude, gemini, deepseek, qwen, glm, ollama). Defaults to LLM_PROVIDER env var or qwen"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name (e.g., gpt-4, claude-3-opus, gemini-pro). Defaults to LLM_MODEL env var"
    )
    parser.add_argument(
        "--clusters",
        type=int,
        default=None,
        help="Number of clusters for paper grouping. If not specified, automatically determines optimal count using silhouette analysis"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["latex", "markdown", "docx", "all"],
        default="latex",
        help="Output format (latex, markdown, docx, or all). Default: latex"
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
            resume=args.resume,
            provider=args.provider,
            model=args.model,
            clusters=args.clusters,
            output_format=args.format
        )
    except Exception as e:
        print(f"\n✗ Pipeline failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
