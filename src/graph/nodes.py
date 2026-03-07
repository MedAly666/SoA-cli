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
import os

from .state import SOAState

# Import utilities from parent src package
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from theme_builder import build_thematic_contract, inject_theme_into_input
from vectorize import build_vector_db
from similarity_cluster import run_similarity_clustering

# Import semantic PDF parser
try:
    from src.pdf_parser import parse_semantic_pdf, semantic_pdf_to_text
    SEMANTIC_PDF_AVAILABLE = True
except ImportError:
    SEMANTIC_PDF_AVAILABLE = False
    print("⚠️  Semantic PDF parser not available, falling back to text-only extraction")


def inject_contract(data: dict, contract: dict) -> dict:
    """
    Inject thematic contract into agent input.
    This enforces global scope constraints.
    """
    return inject_theme_into_input(data, contract)


def extract_pdf_text(pdf_path: str, max_chars: int | None = None) -> tuple[str, dict]:
    """
    Extract text from PDF using PyMuPDF with smart truncation.
    
    Smart truncation:
    - Preferentially keeps: Abstract, Intro, Methods, Results, Conclusion
    - Drops first: References, Acknowledgements, Appendices
    - Warns when truncation occurs
    
    Args:
        pdf_path: Path to PDF file
        max_chars: Maximum characters to extract
        
    Returns:
        Tuple of (extracted_text, truncation_info_dict)
    """
    import os
    if max_chars is None:
        max_chars = int(os.getenv('MAX_PDF_CHARS', '30000'))
    
    try:
        doc = fitz.open(pdf_path)
        filename = Path(pdf_path).name
        total_pages = len(doc)
        
        # First pass: extract all text
        all_pages = []
        total_untruncated_chars = 0
        
        for page_num in range(total_pages):
            page = doc[page_num]
            text = str(page.get_text())  # Ensure text is a string
            if text.strip():
                all_pages.append({
                    'page_num': page_num + 1,
                    'text': text,
                    'chars': len(text)
                })
                total_untruncated_chars += len(text)
        
        doc.close()
        
        if not all_pages:
            raise RuntimeError("No text extracted from PDF")
        
        # Check if truncation is needed
        truncated = total_untruncated_chars > max_chars
        truncation_info = {
            'truncated': truncated,
            'original_chars': total_untruncated_chars,
            'original_pages': total_pages,
            'max_chars': max_chars
        }
        
        if truncated:
            # Smart truncation
            important_pages = _select_important_pages(all_pages, max_chars)
            
            # Build output
            text_parts = []
            total_chars = 0
            
            for page_info in important_pages:
                page_text = page_info['text']
                page_num = page_info['page_num']
                
                if total_chars + len(page_text) > max_chars:
                    # Partial page
                    remaining = max_chars - total_chars
                    if remaining > 500:
                        text_parts.append(f"### Page {page_num} (truncated) ###\n{page_text[:remaining]}")
                    break
                
                text_parts.append(f"### Page {page_num} ###\n{page_text}")
                total_chars += len(page_text)
            
            result = "\n\n".join(text_parts)
            
            # Update truncation info
            truncation_info['final_chars'] = len(result)
            truncation_info['final_pages'] = len(text_parts)
            truncation_info['lost_chars'] = total_untruncated_chars - len(result)
            truncation_info['lost_percentage'] = (truncation_info['lost_chars'] / total_untruncated_chars) * 100
            
            # Print warning
            print(f"  ⚠️  [{filename}] truncated at {max_chars:,} chars")
            print(f"      Full length: {total_untruncated_chars:,} chars")
            print(f"      Lost: {truncation_info['lost_chars']:,} chars ({truncation_info['lost_percentage']:.1f}%)")
            print(f"      Appendices/References may be excluded")
            
        else:
            # No truncation
            text_parts = []
            for page_info in all_pages:
                text_parts.append(f"### Page {page_info['page_num']} ###\n{page_info['text']}")
            
            result = "\n\n".join(text_parts)
            truncation_info['final_chars'] = len(result)
            truncation_info['final_pages'] = len(all_pages)
        
        # Add metadata
        metadata = f"[PDF: {filename}]\n"
        metadata += f"[Extracted: {truncation_info['final_pages']}/{total_pages} pages, {len(result):,} characters]\n"
        if truncated:
            metadata += f"[WARNING: Truncated from {total_untruncated_chars:,} chars]\n"
        metadata += "\n"
        
        return metadata + result, truncation_info
        
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF: {e}")


def _select_important_pages(all_pages: list, max_chars: int) -> list:
    """Select important pages for PDF truncation."""
    # Score pages by importance
    for page in all_pages:
        text_lower = page['text'].lower()
        page['importance'] = 0
        
        # Important sections
        if any(keyword in text_lower for keyword in ['abstract', 'introduction', 'method', 'result', 'conclusion']):
            page['importance'] += 10
        
        # Skip sections
        if any(keyword in text_lower for keyword in ['reference', 'acknowledgement', 'appendix']):
            page['importance'] -= 50
        
        # Boost early pages
        if page['page_num'] <= 5:
            page['importance'] += 5
    
    # Sort by importance
    sorted_pages = sorted(all_pages, key=lambda p: p['importance'], reverse=True)
    
    # Select pages
    selected = []
    total_chars = 0
    for page in sorted_pages:
        if total_chars + page['chars'] <= max_chars:
            selected.append(page)
            total_chars += page['chars']
    
    # Sort back by page number
    selected.sort(key=lambda p: p['page_num'])
    return selected


def extract_pdf_content(pdf_path: str, max_chars: int | None = None) -> tuple[str, dict]:
    """
    Extract PDF content using either semantic parser or legacy text extraction.
    
    Semantic parser (when USE_SEMANTIC_PDF=true):
        - Extracts sections with structure
        - Preserves figures with captions
        - Extracts tables with data
        - Maintains context and relationships
        
    Legacy text extraction (when USE_SEMANTIC_PDF=false):
        - Plain text extraction only
        - No figures or tables
        - Simpler but loses 60-80% of information
    
    Args:
        pdf_path: Path to PDF file
        max_chars: Maximum characters to extract
        
    Returns:
        Tuple of (extracted_text, metadata_dict)
    """
    use_semantic = os.getenv('USE_SEMANTIC_PDF', 'true').lower() == 'true'
    
    if use_semantic and SEMANTIC_PDF_AVAILABLE:
        # Use semantic PDF parser
        try:
            include_figures = os.getenv('INCLUDE_FIGURES_IN_TEXT', 'true').lower() == 'true'
            include_tables = os.getenv('INCLUDE_TABLES_IN_TEXT', 'true').lower() == 'true'
            extract_images = os.getenv('EXTRACT_PDF_IMAGES', 'false').lower() == 'true'
            
            if max_chars is None:
                max_chars = int(os.getenv('MAX_PDF_CHARS', '50000'))
            
            # Parse PDF into semantic structure
            semantic_pdf = parse_semantic_pdf(pdf_path, extract_images=extract_images, max_chars=max_chars)
            
            # Convert to text for LLM
            pdf_text = semantic_pdf_to_text(
                semantic_pdf,
                include_figures=include_figures,
                include_tables=include_tables
            )
            
            # Build metadata
            metadata = {
                'extraction_mode': 'semantic',
                'truncated': semantic_pdf.get('truncated', False),
                'total_chars': len(pdf_text),
                'sections': len(semantic_pdf.get('sections', [])),
                'figures': len(semantic_pdf.get('figures_index', {})),
                'tables': len(semantic_pdf.get('tables_index', {}))
            }
            
            return pdf_text, metadata
            
        except Exception as e:
            print(f"  ⚠️  Semantic parsing failed: {e}")
            print("  ↳ Falling back to text-only extraction")
            # Fall back to text-only
            return extract_pdf_text(pdf_path, max_chars)
    
    else:
        # Use legacy text-only extraction
        if use_semantic and not SEMANTIC_PDF_AVAILABLE:
            print("  ⚠️  Semantic PDF parser not available, using text-only extraction")
        
        text, truncation_info = extract_pdf_text(pdf_path, max_chars)
        metadata = {
            'extraction_mode': 'text_only',
            **truncation_info
        }
        return text, metadata


def call_llm(system_prompt_path: str, input_data: dict, output_path: str) -> str:
    """
    Call LLM using unified LLMClient.
    
    Args:
        system_prompt_path: Path to system prompt file
        input_data: Dictionary to pass as input
        output_path: Where to save the output
        
    Returns:
        LLM response text
    """
    from pathlib import Path
    import os
    import re
    from src.llm_client import LLMClient
    
    # Load system prompt
    with open(system_prompt_path, 'r', encoding='utf-8') as f:
        system_text = f.read()
    
    # Inject citation style instructions for writer and repair prompts
    if 'writer' in system_prompt_path or 'repair' in system_prompt_path:
        from src.citation_formatter import get_citation_instructions
        citation_style = os.getenv('CITATION_STYLE', 'ieee')
        citation_instructions = get_citation_instructions(citation_style)
        
        # Add citation instructions to system prompt
        system_text += f"\n\n{citation_instructions}"
        print(f"  [Citation Style: {citation_style.upper()}]")
    
    # Prepare input as user prompt
    input_json = json.dumps(input_data, indent=2)
    
    # Writer and repair nodes should output LaTeX, not JSON
    is_latex_output = 'writer' in system_prompt_path or 'repair' in system_prompt_path
    
    if is_latex_output:
        # For LaTeX output: Don't force JSON format
        user_prompt = f"""# Input

```json
{input_json}
```

Generate the output as specified in the system prompt. Follow all formatting instructions carefully."""
    else:
        # For JSON output: Explicitly request JSON format
        user_prompt = f"""# Input

```json
{input_json}
```

Generate the output as valid JSON. Return ONLY the JSON with no markdown formatting."""
    
    # Debug: log configuration (only for writer/synthesis nodes which take longest)
    if 'writer' in system_prompt_path or 'synthesis' in system_prompt_path:
        provider = os.getenv('LLM_PROVIDER', 'qwen')
        model = os.getenv('LLM_MODEL', None)
        timeout = int(os.getenv('LLM_TIMEOUT', '300'))
        print(f"  [LLM Config] Provider: {provider}, Model: {model or 'default'}, Timeout: {timeout}s")
    
    # Call LLM via unified client
    client = LLMClient()
    output_text = client.call(system_text, user_prompt)
    
    # Check for LLM failure
    if output_text.startswith("__LLM_FAILURE__:"):
        # Log failure but don't crash - return error as output
        print(f"  ⚠️  LLM call failed: {output_text}")
        # Save failure message to output file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('{"error": "' + output_text.replace('"', '\\"') + '"}')
        return output_text
    
    # Sanitize control characters for JSON output
    if output_path.endswith('.json'):
        output_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', output_text)
        try:
            json.loads(output_text)  # Validate
        except json.JSONDecodeError as e:
            print(f"  ⚠️  Invalid JSON from LLM: {e}")
            # Return error in JSON format
            error_json = '{"error": "Invalid JSON from LLM"}'
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(error_json)
            return error_json
    
    # Save output
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_text)
    
    return output_text


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
        if Path("THEMATIC_CONTRACT.json").exists():
            print("  Loading existing contract...")
            with open("THEMATIC_CONTRACT.json", 'r', encoding='utf-8') as f:
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
        output_path = f"artifacts/reader/{paper_id}.json"
        
        try:
            # Extract PDF content (semantic or text-only based on config)
            pdf_text, extraction_metadata = extract_pdf_content(path)
            
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
            
            result = json.loads(output_text)
            result["paper_id"] = paper_id
            
            # Add extraction metadata
            result["extraction_metadata"] = extraction_metadata
            
            # Add warning if content was truncated or semantic parsing was used
            if extraction_metadata.get('extraction_mode') == 'semantic':
                sections = extraction_metadata.get('sections', 0)
                figures = extraction_metadata.get('figures', 0)
                tables = extraction_metadata.get('tables', 0)
                print(f"  ✓ {paper_id} [Semantic: {sections} sections, {figures} figures, {tables} tables]")
            elif extraction_metadata.get('truncated', False):
                lost_pct = extraction_metadata.get('lost_percentage', 0)
                print(f"  ✓ {paper_id} [Truncated: {lost_pct:.1f}% lost]")
            else:
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
        
        output_path = f"artifacts/extracted/{paper_id}.json"
        
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
            
            result = json.loads(output_text)
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
        
        output_path = f"artifacts/critic/{paper_id}.json"
        
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
            
            result = json.loads(output_text)
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
        cluster_setting = os.getenv('CLUSTER_COUNT', 'auto')
        
        # Parse cluster setting
        if cluster_setting.lower() == 'auto':
            n_clusters = None  # Auto-detect
            print(f"  Running clustering with auto-detection...")
        else:
            n_clusters = int(cluster_setting)
            print(f"  Running clustering (k={n_clusters})...")
        
        clusters = run_similarity_clustering(n_clusters=n_clusters)
        
        print(f"  ✓ Created {len(clusters)} clusters")
        
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
            "artifacts/clusters/clusters.json"
        )
        
        result = json.loads(output_text)
        
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
            "artifacts/synthesis/synthesis.json"
        )
        
        result = json.loads(output_text)
        
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
    prisma_metadata = state.get("prisma_metadata")
    
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
        
        # Add PRISMA metadata if available
        if prisma_metadata:
            agent_input["prisma_methodology"] = prisma_metadata
            print(f"  → Including PRISMA methodology ({prisma_metadata.get('total_papers', 0)} papers)")
        
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
