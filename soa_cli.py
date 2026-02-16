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


# ========== CONFIGURATION ==========

MODEL = "qwen3.5-32b"
TEMPERATURE = 0.2
MAX_WORKERS = 6  # For parallel execution


# ========== QWEN INVOCATION ==========

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
        cmd = ["qwen", "-m", model, "-y"]
        
        result = subprocess.run(
            cmd,
            input=combined_prompt,
            capture_output=True,
            text=True,
            timeout=300
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
    
    Note: This is a placeholder. In production, you'd use a proper PDF parser
    like PyMuPDF, pdfplumber, or similar before calling the LLM.
    """
    paper_id = pdf_path.stem
    output = f"artifacts/reader/{paper_id}.json"
    
    print(f"  [Reader] Processing {paper_id}")
    
    try:
        # In production: extract text from PDF first
        # For now, assuming PDF text is already available or handling is external
        
        run_qwen(
            system_prompt="prompts/reader.system.txt",
            input_file=str(pdf_path),
            output_file=output
        )
        
        print(f"    ✓ {paper_id}")
        return output
        
    except Exception as e:
        print(f"    ✗ {paper_id}: {e}")
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

def run_clustering(extracted_files, critic_files, contract, n_clusters=6):
    """
    Run similarity-based clustering followed by LLM interpretation.
    Applies thematic filtering before embedding.
    """
    print("\n[Stage 3] Clustering Papers")
    print("="*60)
    
    # Load extracted papers and apply thematic filter
    print("[+] Applying thematic filter to papers")
    extracted_data = [load_json(f) for f in extracted_files]
    
    relevant_papers = []
    filtered_out = []
    
    for paper_data in extracted_data:
        if thematic_filter_paper(paper_data, contract):
            relevant_papers.append(paper_data)
        else:
            filtered_out.append(paper_data['paper_id'])
    
    print(f"[+] Thematic filter: {len(relevant_papers)}/{len(extracted_data)} papers relevant")
    if filtered_out:
        print(f"    Filtered out: {', '.join(filtered_out[:5])}" + 
              (f" and {len(filtered_out)-5} more" if len(filtered_out) > 5 else ""))
    
    # Save relevant papers temporarily for vectorization
    relevant_files = []
    for paper in relevant_papers:
        temp_file = f"artifacts/extracted_filtered/{paper['paper_id']}.json"
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
    
    critic_data = [load_json(f) for f in critic_files 
                   if Path(f).stem in [p['paper_id'] for p in relevant_papers]]
    
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
        extracted_db[data["paper_id"]] = data
    
    critic_db = {}
    for f in critic_files:
        data = load_json(f)
        critic_db[data["paper_id"]] = data
    
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
    
    # Check for papers
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
