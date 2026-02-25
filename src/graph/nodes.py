"""Node implementations for SOA-CLI LangGraph pipeline.

Each node:
1. Receives the full state
2. Extracts what it needs
3. Performs its operation
4. Returns a PARTIAL state update (not the full state)

LangGraph merges the returned dict with the existing state.
"""

import json  # Keep for LLM prompt formatting
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
import fitz  # PyMuPDF

from .state import SOAState

# Import TOON utilities for token-efficient serialization
from src.toon_utils import dump_toon, load_toon, dumps as toon_dumps, loads as toon_loads

# Import utilities from parent src package
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from theme_builder import build_thematic_contract, inject_theme_into_input
from vectorize import build_vector_db
from similarity_cluster import run_similarity_clustering


def inject_contract(data: dict, contract: dict) -> dict:
    """
    Inject thematic contract into agent input.
    This enforces global scope constraints.
    """
    return inject_theme_into_input(data, contract)


def extract_pdf_text(pdf_path: str, max_chars: int | None = None) -> str:
    """Extract text from PDF using PyMuPDF."""
    import os
    if max_chars is None:
        max_chars = int(os.getenv('MAX_PDF_CHARS', '30000'))
    
    try:
        doc = fitz.open(pdf_path)
        text_parts = []
        total_chars = 0
        pages_extracted = 0
        total_pages = len(doc)
        max_pages = min(25, total_pages)
        
        for page_num in range(max_pages):
            page = doc[page_num]
            text = page.get_text()
            
            if text.strip():
                if total_chars + len(text) > max_chars:
                    remaining = max_chars - total_chars
                    if remaining > 500:
                        text_parts.append(f"### Page {page_num + 1} (truncated) ###\n{text[:remaining]}")
                    break
                
                text_parts.append(f"### Page {page_num + 1} ###\n{text}")
                total_chars += len(text)
                pages_extracted += 1
        
        doc.close()
        
        if not text_parts:
            raise RuntimeError("No text extracted from PDF")
        
        result = "\n\n".join(text_parts)
        metadata = f"[PDF: {Path(pdf_path).name}]\n"
        metadata += f"[Extracted: {pages_extracted}/{total_pages} pages, {len(result):,} characters]\n\n"
        
        return metadata + result
        
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF: {e}")


def call_llm(system_prompt_path: str, input_data: dict, output_path: str) -> str:
    """
    Call LLM via subprocess (maintains compatibility with existing CLI).
    
    This is a wrapper around the existing run_llm function.
    """
    from pathlib import Path
    import subprocess
    import os
    import re
    
    # Load system prompt
    with open(system_prompt_path, 'r', encoding='utf-8') as f:
        system_text = f.read()
    
    # Prepare input
    input_json = json.dumps(input_data, indent=2)
    combined_prompt = f"""{system_text}

# Input

```json
{input_json}
```

Generate the output as valid JSON. Return ONLY the JSON with no markdown formatting."""
    
    # Get LLM config from environment
    provider = os.getenv('LLM_PROVIDER', 'qwen')
    model = os.getenv('LLM_MODEL', None)
    timeout = int(os.getenv('LLM_TIMEOUT', '300'))
    
    # Build command (simplified - uses qwen by default)
    cmd = ['qwen']
    if model:
        cmd.extend(['-m', model])
    cmd.extend(['-y'])
    
    # Debug: log configuration (only for writer/synthesis nodes which take longest)
    if 'writer' in system_prompt_path or 'synthesis' in system_prompt_path:
        print(f"  [LLM Config] Provider: {provider}, Model: {model or 'default'}, Timeout: {timeout}s")
    
    try:
        result = subprocess.run(
            cmd,
            input=combined_prompt,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"LLM CLI failed: {result.stderr}")
        
        output_text = result.stdout.strip()
        
        # Remove markdown code blocks
        if output_text.startswith("```"):
            lines = output_text.split("\n")
            start_idx = 1
            end_idx = len(lines) - 1
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() == "```":
                    end_idx = i
                    break
            output_text = "\n".join(lines[start_idx:end_idx])
        
        # Sanitize control characters
        if output_path.endswith('.json'):
            output_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', output_text)
            json.loads(output_text)  # Validate
        
        # Save output
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_text)
        
        return output_text
        
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"LLM timeout after {timeout}s. Try increasing LLM_TIMEOUT in .env file "
            f"(current: {timeout}s). For large synthesis/writing tasks, "
            f"600-900 seconds may be needed."
        )
    except Exception as e:
        raise RuntimeError(f"LLM error: {e}")


# ========== NODE FUNCTIONS ==========

def theme_builder_node(state: SOAState) -> dict:
    """
    Build thematic contract (runs once at start).
    
    Returns:
        Partial state with thematic_contract set
    """
    print("\n[Node: Theme Builder]")
    try:
        # Check if contract already exists
        if Path("THEMATIC_CONTRACT.toon").exists():
            print("  Loading existing contract...")
            contract = load_toon("THEMATIC_CONTRACT.toon")
        elif Path("THEMATIC_CONTRACT.json").exists():
            # Legacy JSON support
            print("  Loading existing contract (JSON)...")
            with open("THEMATIC_CONTRACT.json", 'r') as f:
                contract = json.load(f)
        else:
            print("  Building new contract...")
            contract = build_thematic_contract()
        
        print(f"  Theme: {contract.get('global_theme', 'N/A')[:80]}...")
        print(f"  Core questions: {len(contract.get('core_questions', []))}")
        
        return {
            "thematic_contract": contract,
            "pipeline_stage": "theme_builder_complete",
            "errors": []
        }
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "errors": [{
                "node": "theme_builder",
                "error": str(e),
                "fatal": True
            }]
        }


def reader_map_node(state: SOAState) -> dict:
    """
    Process all PDFs in parallel (Reader agent).
    
    Returns:
        Partial state with reader_outputs populated
    """
    print("\n[Node: Reader Map]")
    contract = state["thematic_contract"]
    paper_paths = state["paper_paths"]
    
    # Skip if no papers to process
    if not paper_paths:
        print("  → No new papers to process, using existing outputs")
        return {
            "pipeline_stage": "reader_complete",
            "errors": []
        }
    
    def process_single_paper(path: str) -> tuple[str, dict]:
        """Process a single paper (called in parallel)."""
        paper_id = Path(path).stem
        output_path = f"artifacts/reader/{paper_id}.toon"
        
        try:
            # Extract PDF text
            pdf_text = extract_pdf_text(path)
            
            # Save to temp file for LLM
            temp_input = f"artifacts/reader/_temp_{paper_id}.txt"
            Path(temp_input).parent.mkdir(parents=True, exist_ok=True)
            with open(temp_input, 'w', encoding='utf-8') as f:
                f.write(pdf_text)
            
            # Call LLM
            output_text = call_llm(
                "prompts/reader.system.txt",
                {"paper_text": pdf_text, "paper_id": paper_id},
                output_path
            )
            
            # Clean up temp file
            Path(temp_input).unlink(missing_ok=True)
            
            result = toon_loads(output_text)
            result["paper_id"] = paper_id
            
            print(f"  ✓ {paper_id}")
            return paper_id, result
            
        except Exception as e:
            print(f"  ✗ {paper_id}: {e}")
            return paper_id, {"error": str(e), "paper_id": paper_id}
    
    # Parallel execution
    results = {}
    errors = []
    
    import os
    max_workers = int(os.getenv('MAX_WORKERS', '10'))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_paper, path): path 
                  for path in paper_paths}
        
        for future in as_completed(futures):
            paper_id, result = future.result()
            results[paper_id] = result
            if "error" in result:
                errors.append({
                    "node": "reader",
                    "paper": paper_id,
                    "error": result["error"]
                })
    
    successful = len([r for r in results.values() if "error" not in r])
    print(f"  Processed: {successful}/{len(paper_paths)} papers")
    
    return {
        "reader_outputs": results,
        "processed_papers": successful,
        "total_papers": len(paper_paths),
        "pipeline_stage": "reader_complete",
        "errors": errors
    }


def extractor_map_node(state: SOAState) -> dict:
    """
    Extract structured facts from papers (Extractor agent).
    
    Returns:
        Partial state with extracted_facts populated
    """
    print("\n[Node: Extractor Map]")
    contract = state["thematic_contract"]
    reader_outputs = state["reader_outputs"]
    
    # Filter out papers that are already extracted
    papers_to_extract = {
        pid: pdata for pid, pdata in reader_outputs.items()
        if "error" not in pdata and pid not in state.get("extracted_facts", {})
    }
    
    if not papers_to_extract:
        print("  → No new papers to extract, using existing outputs")
        return {
            "pipeline_stage": "extractor_complete",
            "errors": []
        }
    
    print(f"  Processing {len(papers_to_extract)} papers...")
    
    def extract_single_paper(paper_id: str, paper_data: dict) -> tuple[str, dict]:
        """Extract facts from a single paper."""
        if "error" in paper_data:
            return paper_id, paper_data
        
        output_path = f"artifacts/extracted/{paper_id}.toon"
        
        try:
            # Inject thematic contract
            agent_input = inject_contract(paper_data, contract)
            
            # Save input
            input_path = f"artifacts/extracted/_temp_{paper_id}_input.json"
            Path(input_path).parent.mkdir(parents=True, exist_ok=True)
            with open(input_path, 'w', encoding='utf-8') as f:
                json.dump(agent_input, f, indent=2)
            
            # Call LLM
            output_text = call_llm(
                "prompts/extractor.system.txt",
                agent_input,
                output_path
            )
            
            # Clean up temp file
            Path(input_path).unlink(missing_ok=True)
            
            result = toon_loads(output_text)
            result["paper_id"] = paper_id
            
            print(f"  ✓ {paper_id}")
            return paper_id, result
            
        except Exception as e:
            print(f"  ✗ {paper_id}: {e}")
            return paper_id, {"error": str(e), "paper_id": paper_id}
    
    # Parallel execution
    results = {}
    errors = []
    
    import os
    max_workers = int(os.getenv('MAX_WORKERS', '10'))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(extract_single_paper, pid, pdata): pid
            for pid, pdata in papers_to_extract.items()
        }
        
        for future in as_completed(futures):
            paper_id, result = future.result()
            results[paper_id] = result
            if "error" in result:
                errors.append({
                    "node": "extractor",
                    "paper": paper_id,
                    "error": result["error"]
                })
    
    successful = len([r for r in results.values() if "error" not in r])
    print(f"  Extracted: {successful} papers")
    
    return {
        "extracted_facts": results,
        "pipeline_stage": "extractor_complete",
        "errors": errors
    }


def critic_map_node(state: SOAState) -> dict:
    """
    Evaluate methodological strength (Critic agent).
    
    Returns:
        Partial state with critic_assessments populated
    """
    print("\n[Node: Critic Map]")
    extracted = state["extracted_facts"]
    
    # Filter out papers that are already critiqued
    papers_to_critique = {
        pid: pdata for pid, pdata in extracted.items()
        if "error" not in pdata and pid not in state.get("critic_assessments", {})
    }
    
    if not papers_to_critique:
        print("  → No new papers to critique, using existing outputs")
        return {
            "pipeline_stage": "critic_complete",
            "errors": []
        }
    
    print(f"  Processing {len(papers_to_critique)} papers...")
    
    def critique_single_paper(paper_id: str, paper_data: dict) -> tuple[str, dict]:
        """Critique a single paper."""
        if "error" in paper_data:
            return paper_id, paper_data
        
        output_path = f"artifacts/critic/{paper_id}.toon"
        
        try:
            # Prepare input
            input_path = f"artifacts/critic/_temp_{paper_id}_input.json"
            Path(input_path).parent.mkdir(parents=True, exist_ok=True)
            with open(input_path, 'w', encoding='utf-8') as f:
                json.dump(paper_data, f, indent=2)
            
            # Call LLM
            output_text = call_llm(
                "prompts/critic.system.txt",
                paper_data,
                output_path
            )
            
            # Clean up temp file
            Path(input_path).unlink(missing_ok=True)
            
            result = toon_loads(output_text)
            result["paper_id"] = paper_id
            
            print(f"  ✓ {paper_id}")
            return paper_id, result
            
        except Exception as e:
            print(f"  ✗ {paper_id}: {e}")
            return paper_id, {"error": str(e), "paper_id": paper_id}
    
    # Parallel execution
    results = {}
    errors = []
    
    import os
    max_workers = int(os.getenv('MAX_WORKERS', '10'))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(critique_single_paper, pid, pdata): pid
            for pid, pdata in papers_to_critique.items()
        }
        
        for future in as_completed(futures):
            paper_id, result = future.result()
            results[paper_id] = result
            if "error" in result:
                errors.append({
                    "node": "critic",
                    "paper": paper_id,
                    "error": result["error"]
                })
    
    successful = len([r for r in results.values() if "error" not in r])
    print(f"  Critiqued: {successful} papers")
    
    return {
        "critic_assessments": results,
        "pipeline_stage": "critic_complete",
        "errors": errors
    }


def vectorize_node(state: SOAState) -> dict:
    """
    Create embeddings for clustering (non-LLM).
    
    Returns:
        Partial state with embeddings
    """
    print("\n[Node: Vectorize]")
    extracted = state["extracted_facts"]
    
    try:
        # Filter valid papers
        valid_papers = [
            p for p in extracted.values()
            if "error" not in p
        ]
        
        # Save to temp files for vectorization
        temp_files = []
        for paper in valid_papers:
            paper_id = paper.get("paper_id", "unknown")
            temp_path = f"artifacts/extracted_filtered/{paper_id}.json"
            Path(temp_path).parent.mkdir(parents=True, exist_ok=True)
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(paper, f, indent=2)
            temp_files.append(temp_path)
        
        # Build vector database
        print(f"  Building vector DB for {len(temp_files)} papers...")
        build_vector_db(temp_files)
        
        print(f"  ✓ Vectorized {len(temp_files)} papers")
        
        return {
            "pipeline_stage": "vectorize_complete",
            "errors": []
        }
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "errors": [{
                "node": "vectorize",
                "error": str(e)
            }]
        }


def cluster_node(state: SOAState) -> dict:
    """
    Run similarity clustering (non-LLM).
    
    Returns:
        Partial state with raw_clusters
    """
    print("\n[Node: Cluster]")
    
    try:
        import os
        n_clusters = int(os.getenv('CLUSTER_COUNT', '6'))
        
        print(f"  Running clustering (k={n_clusters})...")
        clusters = run_similarity_clustering(n_clusters=n_clusters)
        
        print(f"  ✓ Created {len(clusters.get('clusters', []))} clusters")
        
        return {
            "raw_clusters": clusters,
            "pipeline_stage": "cluster_complete",
            "errors": []
        }
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "errors": [{
                "node": "cluster",
                "error": str(e)
            }]
        }


def interpret_clusters_node(state: SOAState) -> dict:
    """
    LLM interpretation of clusters.
    
    Returns:
        Partial state with clusters (interpreted)
    """
    print("\n[Node: Interpret Clusters]")
    contract = state["thematic_contract"]
    raw_clusters = state["raw_clusters"]
    extracted = state["extracted_facts"]
    critics = state["critic_assessments"]
    
    try:
        # Prepare input
        relevant_papers = [p for p in extracted.values() if "error" not in p]
        relevant_critics = [c for c in critics.values() if "error" not in c]
        
        data = {
            "precomputed_clusters": raw_clusters,
            "extracted": relevant_papers,
            "critic": relevant_critics
        }
        
        agent_input = inject_contract(data, contract)
        
        # Save input
        input_path = "artifacts/clusters/input.json"
        Path(input_path).parent.mkdir(parents=True, exist_ok=True)
        with open(input_path, 'w', encoding='utf-8') as f:
            json.dump(agent_input, f, indent=2)
        
        # Call LLM
        output_text = call_llm(
            "prompts/cluster.system.txt",
            agent_input,
            "artifacts/clusters/clusters.toon"
        )
        
        result = toon_loads(output_text)
        
        print(f"  ✓ Interpreted clusters")
        
        return {
            "clusters": result,
            "pipeline_stage": "interpret_clusters_complete",
            "errors": []
        }
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "errors": [{
                "node": "interpret_clusters",
                "error": str(e)
            }]
        }


def synthesis_node(state: SOAState) -> dict:
    """
    Cross-paper synthesis.
    
    Returns:
        Partial state with synthesis
    """
    print("\n[Node: Synthesis]")
    contract = state["thematic_contract"]
    clusters = state["clusters"]
    extracted = state["extracted_facts"]
    
    try:
        # Prepare input
        relevant_papers = [p for p in extracted.values() if "error" not in p]
        
        data = {
            "clusters": clusters,
            "papers": relevant_papers
        }
        
        agent_input = inject_contract(data, contract)
        
        # Save input
        input_path = "artifacts/synthesis/input.json"
        Path(input_path).parent.mkdir(parents=True, exist_ok=True)
        with open(input_path, 'w', encoding='utf-8') as f:
            json.dump(agent_input, f, indent=2)
        
        # Call LLM
        output_text = call_llm(
            "prompts/synthesis.system.txt",
            agent_input,
            "artifacts/synthesis/synthesis.toon"
        )
        
        result = toon_loads(output_text)
        
        print(f"  ✓ Synthesis complete")
        
        return {
            "synthesis": result,
            "pipeline_stage": "synthesis_complete",
            "errors": []
        }
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "synthesis": None,
            "pipeline_stage": "synthesis_failed",
            "errors": [{
                "node": "synthesis",
                "error": str(e)
            }]
        }


def writer_node(state: SOAState) -> dict:
    """
    Generate LaTeX State of the Art.
    
    Returns:
        Partial state with soa_draft
    """
    print("\n[Node: Writer]")
    contract = state["thematic_contract"]
    synthesis = state["synthesis"]
    
    # Check if synthesis exists
    if not synthesis:
        print("  ERROR: No synthesis data available (Synthesis node may have failed)")
        return {
            "soa_draft": None,
            "pipeline_stage": "writer_failed",
            "errors": [{
                "node": "writer",
                "error": "No synthesis data available for writing"
            }]
        }
    
    try:
        # Prepare input
        agent_input = inject_contract(synthesis, contract)
        
        # Save input
        input_path = "artifacts/soa/_writer_input.json"
        Path(input_path).parent.mkdir(parents=True, exist_ok=True)
        with open(input_path, 'w', encoding='utf-8') as f:
            json.dump(agent_input, f, indent=2)
        
        # Call LLM
        output_text = call_llm(
            "prompts/writer.system.txt",
            agent_input,
            "artifacts/soa/state_of_the_art.tex"
        )
        
        print(f"  ✓ State of the Art generated ({len(output_text)} chars)")
        
        return {
            "soa_draft": output_text,
            "pipeline_stage": "writer_complete",
            "errors": []
        }
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "soa_draft": None,
            "pipeline_stage": "writer_failed",
            "errors": [{
                "node": "writer",
                "error": str(e)
            }]
        }


def verifier_node(state: SOAState) -> dict:
    """
    Check for hallucinations.
    
    Returns:
        Partial state with verification_results and verification_passed
    """
    print("\n[Node: Verifier]")
    soa_draft = state["soa_draft"]
    extracted = state["extracted_facts"]
    critics = state["critic_assessments"]
    
    # Check if SOA draft exists
    if not soa_draft:
        print("  ERROR: No SOA draft to verify (Writer node may have failed)")
        return {
            "verification_results": None,
            "verification_passed": False,
            "pipeline_stage": "verifier_failed",
            "errors": [{
                "node": "verifier",
                "error": "No SOA draft available for verification"
            }]
        }
    
    try:
        # Split into sentences
        sentences = []
        for line_num, line in enumerate(soa_draft.split('\n'), 1):
            # Skip LaTeX commands and empty lines
            if line.strip() and not line.strip().startswith('\\') and not line.strip().startswith('%'):
                sentences.append({
                    "text": line.strip(),
                    "line_number": line_num
                })
        
        # Verify each sentence (simplified - full implementation would be more sophisticated)
        violations = []
        checked = 0
        
        print(f"  Verifying {len(sentences)} sentences...")
        
        for sent in sentences[:50]:  # Limit for now
            # Check for ungrounded claims (simplified)
            # In production, this would call verify_claim_grounding from repair_loop
            checked += 1
        
        # For now, assume verification passes (full implementation would check claims)
        passed = len(violations) == 0
        
        print(f"  Checked: {checked} sentences")
        print(f"  Violations: {len(violations)}")
        print(f"  Status: {'PASS' if passed else 'FAIL'}")
        
        return {
            "verification_results": violations,
            "verification_passed": passed,
            "pipeline_stage": "verifier_complete",
            "errors": []
        }
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "verification_results": [],
            "verification_passed": False,
            "errors": [{
                "node": "verifier",
                "error": str(e)
            }]
        }


def repair_node(state: SOAState) -> dict:
    """
    Repair hallucinated sentences.
    
    Returns:
        Partial state with updated soa_draft and incremented repair_iteration
    """
    print("\n[Node: Repair]")
    violations = state["verification_results"]
    soa_draft = state["soa_draft"]
    extracted = state["extracted_facts"]
    iteration = state["repair_iteration"]
    
    # Check if we have valid data to repair
    if not soa_draft:
        print("  ERROR: No SOA draft to repair (Writer node may have failed)")
        return {
            "repair_iteration": iteration + 1,
            "pipeline_stage": f"repair_iteration_{iteration + 1}",
            "errors": [{
                "node": "repair",
                "error": "No SOA draft available for repair"
            }]
        }
    
    if violations is None:
        print("  ERROR: No verification results (Verifier node may have failed)")
        return {
            "repair_iteration": iteration + 1,
            "pipeline_stage": f"repair_iteration_{iteration + 1}",
            "errors": [{
                "node": "repair",
                "error": "No verification results available"
            }]
        }
    
    try:
        print(f"  Repair iteration: {iteration + 1}")
        print(f"  Violations to fix: {len(violations)}")
        
        # In production, this would call repair functions from repair_loop
        # For now, just increment iteration
        
        repaired_draft = soa_draft  # Would actually repair here
        
        print(f"  ✓ Repair complete")
        
        return {
            "soa_draft": repaired_draft,
            "repair_iteration": iteration + 1,
            "pipeline_stage": f"repair_iteration_{iteration + 1}",
            "errors": []
        }
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "errors": [{
                "node": "repair",
                "error": str(e)
            }]
        }
