#!/usr/bin/env python3
"""
SOA-CLI: Production-Grade Multi-Agent State of the Art Generator

MAIN ENTRY POINT for the SOA-CLI system.

This orchestrator:
- Runs a deterministic pipeline (no agent improvisation)
- Enforces thematic constraints across all agents
- Parallelizes where safe (Extractor + Critic)
- Saves all artifacts to disk
- Includes retry and validation
- Is LLM-agnostic (works with Qwen or any other)

Usage:
    python soa_cli.py

Documentation: See docs/ folder
"""

import subprocess
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import fitz  # PyMuPDF for PDF text extraction
from dotenv import load_dotenv

# Import core modules
from src.vectorize import build_vector_db
from src.similarity_cluster import run_similarity_clustering
from src.repair_loop import repair_pipeline
from src.theme_builder import (
    build_thematic_contract,
    load_thematic_contract,
    inject_theme_into_input,
    print_theme_summary,
    thematic_filter_paper,
    detect_theme_violation
)

# Load environment variables from .env file
load_dotenv()


# ========== CONFIGURATION ==========

# LLM Configuration
MODEL = os.getenv('LLM_MODEL', None)  # Use default Qwen model if not specified
TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.3'))
LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '300'))  # Timeout in seconds

# Pipeline Configuration
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '10'))  # For parallel execution
MAX_PDF_CHARS = int(os.getenv('MAX_PDF_CHARS', '30000'))  # Limit PDF text to ~15-20 pages
CLUSTER_COUNT = int(os.getenv('CLUSTER_COUNT', '6'))  # Number of clusters for similarity clustering


# ========== QWEN INVOCATION ==========

def extract_text_from_pdf(pdf_path, max_chars=MAX_PDF_CHARS):
    """
    Extract text from PDF using PyMuPDF.
    
    Prioritizes first ~15-20 pages which typically contain:
    - Abstract, Introduction, Methodology, Results (core content)
    - Avoids lengthy appendices, references, supplementary material
    
    Args:
        pdf_path: Path to PDF file
        max_chars: Maximum characters to extract (to prevent timeout)
        
    Returns:
        Extracted text as string (truncated if needed)
        
    Raises:
        RuntimeError: If PDF extraction fails
    """
    try:
        doc = fitz.open(pdf_path)
        text_parts = []
        total_chars = 0
        pages_extracted = 0
        total_pages = len(doc)
        
        # Extract up to max_chars or 25 pages, whichever comes first
        max_pages = min(25, total_pages)
        
        for page_num in range(max_pages):
            page = doc[page_num]
            text = page.get_text()
            
            if text.strip():
                # Check if adding this page would exceed limit
                if total_chars + len(text) > max_chars:
                    # Add truncated page and stop
                    remaining = max_chars - total_chars
                    if remaining > 500:  # Only add if significant space left
                        text_parts.append(f"### Page {page_num + 1} (truncated) ###\n{text[:remaining]}")
                    break
                
                text_parts.append(f"### Page {page_num + 1} ###\n{text}")
                total_chars += len(text)
                pages_extracted += 1
        
        doc.close()
        
        if not text_parts:
            raise RuntimeError("No text extracted from PDF")
        
        result = "\n\n".join(text_parts)
        
        # Add metadata header
        metadata = f"[PDF: {Path(pdf_path).name}]\n"
        metadata += f"[Extracted: {pages_extracted}/{total_pages} pages, {len(result):,} characters]\n"
        if pages_extracted < total_pages:
            metadata += f"[Note: Focused on first {pages_extracted} pages - typically contains core methodology and results]\n"
        metadata += "\n" + "="*60 + "\n\n"
        
        result = metadata + result
        
        return result
        
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF: {e}")


def run_qwen(system_prompt, input_file, output_file, model=MODEL, temperature=TEMPERATURE):
    """
    Invoke Qwen CLI with specified parameters.
    
    Args:
        system_prompt: Path to system prompt file
        input_file: Path to input file
        output_file: Path to output file
        model: Model name
        temperature: Temperature setting (note: Qwen CLI may not support this directly)
        
    Raises:
        RuntimeError: If Qwen execution fails
    """
    # Load system prompt
    with open(system_prompt, 'r', encoding='utf-8') as f:
        system_text = f.read()
    
    # Load input data
    with open(input_file, 'r', encoding='utf-8') as f:
        input_data = f.read()
    
    # Construct combined prompt
    combined_prompt = f"""{system_text}

# Input

```json
{input_data}
```

Generate the output as valid JSON. Return ONLY the JSON with no markdown formatting."""
    
    try:
        # Invoke Qwen with stdin/stdout
        if model:
            cmd = ["qwen", "-m", model, "-y"]
        else:
            cmd = ["qwen", "-y"]  # Use default model
        
        result = subprocess.run(
            cmd,
            input=combined_prompt,
            capture_output=True,
            text=True,
            timeout=LLM_TIMEOUT
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Qwen failed: {result.stderr}")
        
        # Parse and clean output
        output_text = result.stdout.strip()
        
        # Remove markdown code blocks if present
        if output_text.startswith("```"):
            lines = output_text.split("\n")
            start_idx = 1
            if lines[0].startswith("```json"):
                start_idx = 1
            end_idx = len(lines) - 1
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() == "```":
                    end_idx = i
                    break
            output_text = "\n".join(lines[start_idx:end_idx])
        
        # Save output
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_text)
        
        return output_file
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Qwen timeout for {input_file}")
    except Exception as e:
        raise RuntimeError(f"Qwen error: {e}")


def load_json(path):
    """Load and validate JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load JSON from {path}: {e}")


def save_json(data, path):
    """Save data as JSON file."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def prepare_agent_input(data, contract, temp_file):
    """
    Prepare agent input by injecting thematic contract.
    
    Args:
        data: Agent input data
        contract: Thematic contract dictionary
        temp_file: Path to save combined input
        
    Returns:
        Path to prepared input file
    """
    combined = inject_theme_into_input(data, contract)
    save_json(combined, temp_file)
    return temp_file


# ========== STAGE 0: THEMATIC CONTRACT ==========

def run_stage_0():
    """
    Stage 0: Build or load thematic contract.
    
    This defines the global research scope that all agents must follow.
    
    Returns:
        Thematic contract dictionary
    """
    print("\n" + "="*60)
    print("STAGE 0: THEMATIC CONTRACT")
    print("="*60)
    
    # Check if contract already exists
    if Path("THEMATIC_CONTRACT.json").exists():
        print("[+] Loading existing thematic contract")
        contract = load_thematic_contract()
    else:
        print("[+] Building new thematic contract")
        contract = build_thematic_contract()
    
    print_theme_summary(contract)
    
    return contract


# ========== STAGE 1: READER AGENT ==========

def run_reader(pdf_path):
    """
    Convert PDF to structured JSON.
    
    Extracts text from PDF using PyMuPDF, then passes to LLM for structuring.
    """
    paper_id = pdf_path.stem
    output = f"artifacts/reader/{paper_id}.json"
    temp_text_file = f"artifacts/reader/_temp_{paper_id}.txt"
    
    print(f"  [Reader] Processing {paper_id}")
    
    try:
        # Extract text from PDF
        pdf_text = extract_text_from_pdf(str(pdf_path))
        
        # Save extracted text to temporary file
        Path(temp_text_file).parent.mkdir(parents=True, exist_ok=True)
        with open(temp_text_file, 'w', encoding='utf-8') as f:
            f.write(pdf_text)
        
        # Process with LLM
        run_qwen(
            system_prompt="prompts/reader.system.txt",
            input_file=temp_text_file,
            output_file=output
        )
        
        # Clean up temp file
        Path(temp_text_file).unlink(missing_ok=True)
        
        print(f"    ✓ {paper_id}")
        return output
        
    except Exception as e:
        print(f"    ✗ {paper_id}: {e}")
        # Clean up temp file on error
        Path(temp_text_file).unlink(missing_ok=True)
        return None


# ========== STAGE 2: EXTRACTOR AGENT ==========

def run_extractor(reader_json):
    """
    Extract structured scientific knowledge from paper.
    """
    paper_id = Path(reader_json).stem
    output = f"artifacts/extracted/{paper_id}.json"
    
    print(f"  [Extractor] Processing {paper_id}")
    
    try:
        run_qwen(
            system_prompt="prompts/extractor.system.txt",
            input_file=reader_json,
            output_file=output
        )
        
        print(f"    ✓ {paper_id}")
        return output
        
    except Exception as e:
        print(f"    ✗ {paper_id}: {e}")
        return None


# ========== STAGE 3: CRITIC AGENT ==========

def run_critic(extracted_json):
    """
    Evaluate methodological strength of paper.
    """
    paper_id = Path(extracted_json).stem
    output = f"artifacts/critic/{paper_id}.json"
    
    print(f"  [Critic] Processing {paper_id}")
    
    try:
        run_qwen(
            system_prompt="prompts/critic.system.txt",
            input_file=extracted_json,
            output_file=output
        )
        
        print(f"    ✓ {paper_id}")
        return output
        
    except Exception as e:
        print(f"    ✗ {paper_id}: {e}")
        return None


# ========== PARALLEL EXECUTION ==========

def run_extraction_and_critique(reader_outputs):
    """
    Run Extractor and Critic agents in parallel.
    """
    print("\n[Stage 2] Running Extractor + Critic (parallel)")
    print("="*60)
    
    extracted = []
    critics = []
    
    # First run extractors
    print("[Extractors]")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(run_extractor, r): r for r in reader_outputs if r}
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                extracted.append(result)
    
    # Then run critics on extracted data
    print("\n[Critics]")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(run_critic, e): e for e in extracted}
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                critics.append(result)
    
    print(f"\n[✓] Extraction complete: {len(extracted)} papers")
    print(f"[✓] Critique complete: {len(critics)} papers")
    
    return extracted, critics


# ========== STAGE 4: CLUSTERING ==========

def run_clustering(extracted_files, critic_files, contract, n_clusters=None):
    """
    Run similarity-based clustering followed by LLM interpretation.
    Applies thematic filtering before embedding.
    """
    # Use configured cluster count if not specified
    if n_clusters is None:
        n_clusters = CLUSTER_COUNT
    
    print("\n[Stage 3] Clustering Papers")
    print("="*60)
    
    # Load extracted papers and apply thematic filter
    print("[+] Applying thematic filter to papers")
    extracted_data = [load_json(f) for f in extracted_files]
    
    relevant_papers = []
    filtered_out = []
    
    for i, paper_data in enumerate(extracted_data):
        # Get paper identifier (use paper_id if available, otherwise use filename)
        paper_id = paper_data.get('paper_id', Path(extracted_files[i]).stem)
        
        # Ensure paper has paper_id field
        if 'paper_id' not in paper_data:
            paper_data['paper_id'] = paper_id
        
        if thematic_filter_paper(paper_data, contract):
            relevant_papers.append(paper_data)
        else:
            filtered_out.append(paper_id)
    
    print(f"[+] Thematic filter: {len(relevant_papers)}/{len(extracted_data)} papers relevant")
    if filtered_out:
        print(f"    Filtered out: {', '.join(filtered_out[:5])}" + 
              (f" and {len(filtered_out)-5} more" if len(filtered_out) > 5 else ""))
    
    # Save relevant papers temporarily for vectorization
    relevant_files = []
    for i, paper in enumerate(relevant_papers):
        # paper_id should now be guaranteed to exist
        paper_id = paper['paper_id']
        # Sanitize paper_id for filename (replace invalid chars)
        safe_id = paper_id.replace('/', '_').replace('\\', '_')[:100]
        temp_file = f"artifacts/extracted_filtered/{safe_id}.json"
        save_json(paper, temp_file)
        relevant_files.append(temp_file)
    
    # Build vector database (only on relevant papers)
    print("[+] Building vector database")
    build_vector_db(relevant_files)
    
    # Run mathematical clustering
    print("[+] Running similarity-based clustering")
    raw_clusters = run_similarity_clustering(n_clusters=n_clusters)
    
    # Prepare input for cluster agent (with theme contract)
    merged_input_base = "artifacts/clusters/input_base.json"
    
    # Match critics to relevant papers by filename (not by paper_id which might be DOI)
    relevant_filenames = set(Path(f).stem for f in extracted_files 
                           if any(Path(f).stem == Path(critic).stem for critic in critic_files))
    critic_data = []
    for critic_file in critic_files:
        critic_stem = Path(critic_file).stem
        # Check if this critic corresponds to a relevant paper
        for i, extracted_file in enumerate(extracted_files):
            if Path(extracted_file).stem == critic_stem:
                if extracted_data[i] in relevant_papers:
                    critic_data.append(load_json(critic_file))
                break
    
    data = {
        "precomputed_clusters": raw_clusters,
        "extracted": relevant_papers,
        "critic": critic_data
    }
    
    merged_input = prepare_agent_input(data, contract, "artifacts/clusters/input.json")
    
    # Run cluster interpretation agent
    print("[+] Running cluster interpretation agent")
    output = "artifacts/clusters/clusters.json"
    
    run_qwen(
        system_prompt="prompts/cluster.system.txt",
        input_file=merged_input,
        output_file=output
    )
    
    print(f"[✓] Clusters saved to {output}")
    
    return output


# ========== STAGE 5: SYNTHESIS ==========

def run_synthesis(cluster_file, extracted_files, contract):
    """
    Cross-paper reasoning and gap identification.
    Synthesis directly addresses thematic core questions.
    """
    print("\n[Stage 4] Synthesis")
    print("="*60)
    
    data = {
        "clusters": load_json(cluster_file),
        "papers": [load_json(f) for f in extracted_files]
    }
    
    synthesis_input = prepare_agent_input(data, contract, "artifacts/synthesis/input.json")
    
    output = "artifacts/synthesis/synthesis.json"
    
    print("[+] Running synthesis agent")
    run_qwen(
        system_prompt="prompts/synthesis.system.txt",
        input_file=synthesis_input,
        output_file=output
    )
    
    print(f"[✓] Synthesis saved to {output}")
    
    return output


# ========== STAGE 6: WRITER ==========

def run_writer(synthesis_file, contract):
    """
    Generate final State of the Art LaTeX.
    Writer enforces clear exclusion boundaries based on contract.
    """
    print("\n[Stage 5] Writing State of the Art")
    print("="*60)
    
    # Load synthesis and inject theme
    synthesis_data = load_json(synthesis_file)
    writer_input = prepare_agent_input(synthesis_data, contract, "artifacts/soa/_writer_input.json")
    
    output = "artifacts/soa/state_of_the_art.tex"
    
    print("[+] Running writer agent")
    run_qwen(
        system_prompt="prompts/writer.system.txt",
        input_file=writer_input,
        output_file=output
    )
    
    print(f"[✓] State of the Art saved to {output}")
    
    # Check for theme violations
    with open(output, 'r', encoding='utf-8') as f:
        soa_text = f.read()
    
    violations = detect_theme_violation(soa_text, contract)
    if violations:
        print(f"[!] Warning: {len(violations)} theme violations detected")
        for v in violations[:3]:
            print(f"    - Out-of-scope term: {v['term']}")
    
    return output


# ========== STAGE 7: HALLUCINATION DETECTION & REPAIR ==========

def run_verification_and_repair(soa_file, extracted_files, critic_files):
    """
    Detect hallucinations and repair if necessary.
    """
    print("\n[Stage 6] Verification & Repair")
    print("="*60)
    
    # Load extracted and critic databases
    extracted_db = {}
    for f in extracted_files:
        data = load_json(f)
        # Use paper_id if available, otherwise use filename
        paper_id = data.get("paper_id", Path(f).stem)
        if "paper_id" not in data:
            data["paper_id"] = paper_id
        extracted_db[paper_id] = data
    
    critic_db = {}
    for f in critic_files:
        data = load_json(f)
        # Use paper_id if available, otherwise use filename
        paper_id = data.get("paper_id", Path(f).stem)
        if "paper_id" not in data:
            data["paper_id"] = paper_id
        critic_db[paper_id] = data
    
    # Run repair pipeline
    success = repair_pipeline(soa_file, extracted_db, critic_db)
    
    if success:
        print("[✓] SoA verified and repaired successfully")
        return "artifacts/soa/state_of_the_art_final.tex"
    else:
        print("[!] SoA has unrepairable issues - see repair_failure.json")
        return "artifacts/soa/state_of_the_art_repaired_partial.tex"


# ========== MAIN PIPELINE ==========

def main():
    """
    Main orchestrator pipeline with thematic priming.
    """
    print("\n" + "="*60)
    print("STATE OF THE ART GENERATION PIPELINE")
    print("="*60)
    
    # Stage 0: Thematic Contract (NEW - runs first)
    try:
        contract = run_stage_0()
    except RuntimeError as e:
        print(f"\n[!] {e}")
        print("[!] Pipeline requires thematic contract to proceed")
        sys.exit(1)
    
    # Check for existing extracted papers
    extracted_dir = Path("artifacts/extracted")
    critic_dir = Path("artifacts/critic")
    existing_extracted = list(extracted_dir.glob("*.json")) if extracted_dir.exists() else []
    existing_critics = list(critic_dir.glob("*.json")) if critic_dir.exists() else []
    
    # If we have extracted papers, skip stages 1-3
    if existing_extracted:
        print(f"\n[+] Found {len(existing_extracted)} existing extracted papers")
        print("[+] Skipping stages 1-3 (already completed)")
        extracted = existing_extracted
        critics = existing_critics
    else:
        # Check for raw papers
        papers_dir = Path("papers")
        pdfs = list(papers_dir.glob("*.pdf"))
        
        if not pdfs:
            print("[!] No PDF files found in papers/ directory")
            print("[!] Please add your 43 papers to the papers/ folder")
            sys.exit(1)
        
        print(f"\n[+] Found {len(pdfs)} papers")
        
        # Stage 1: Reader Agent
        print("\n[Stage 1] Reading Papers")
        print("="*60)
        reader_outputs = []
        for pdf in pdfs:
            result = run_reader(pdf)
            if result:
                reader_outputs.append(result)
        
        if not reader_outputs:
            print("[!] No papers were successfully read")
            sys.exit(1)
        
        print(f"\n[✓] Successfully read {len(reader_outputs)} papers")
        
        # Stage 2+3: Extraction and Critique (parallel)
        extracted, critics = run_extraction_and_critique(reader_outputs)
        
        if not extracted:
            print("[!] No papers were successfully extracted")
            sys.exit(1)
    
    # Stage 4: Clustering (with thematic filtering)
    cluster_file = run_clustering(extracted, critics, contract)
    
    # Stage 5: Synthesis (with thematic contract)
    synthesis_file = run_synthesis(cluster_file, extracted, contract)
    
    # Stage 6: Writing (with thematic contract)
    soa_file = run_writer(synthesis_file, contract)
    
    # Stage 7: Verification and Repair
    final_file = run_verification_and_repair(soa_file, extracted, critics)
    
    # Final report
    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)
    print(f"[✓] Final State of the Art: {final_file}")
    print(f"[✓] Total papers processed: {len(extracted)}")
    print(f"[✓] Thematic contract: THEMATIC_CONTRACT.json")
    print(f"[✓] Artifacts saved in: artifacts/")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
