"""Node implementations for SOA-CLI LangGraph pipeline.

Each node:
1. Receives the full state
2. Extracts what it needs
3. Performs its operation
4. Returns a PARTIAL state update (not the full state)

LangGraph merges the returned dict with the existing state.
"""

import json  # Keep for LLM prompt formatting
import re
import time
import subprocess
from datetime import datetime
from functools import wraps
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
import fitz  # PyMuPDF
import os

from .state import SOAState

# Import utilities from parent src package
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from theme_builder import build_thematic_contract, inject_theme_into_input
from vectorize import build_vector_db
from vectorize import load_vector_db
from similarity_cluster import run_similarity_clustering
from citation_graph import build_citation_graph, get_grounding_context
from reflector import run_reflector
from rubric_evaluator import run_rubric_evaluator

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


def _collect_seed_paper_ids(obj: Any) -> list[str]:
    """Recursively collect likely cluster seed paper IDs from nested structures."""
    ids: set[str] = set()

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = str(key).lower()
            if key_lower in {
                "paper_id",
                "seed_paper_id",
                "representative_paper_id",
                "seed",
                "representative_paper",
            } and isinstance(value, str) and value.strip():
                ids.add(value.strip())
            else:
                for nested_id in _collect_seed_paper_ids(value):
                    ids.add(nested_id)

    elif isinstance(obj, list):
        for item in obj:
            for nested_id in _collect_seed_paper_ids(item):
                ids.add(nested_id)

    return sorted(ids)


def _write_json(path: str, payload: dict) -> None:
    """Write JSON payload to disk safely."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)


def _count_citations_in_text(text: str) -> int:
    """Count citations in either pandoc markdown or LaTeX citation forms."""
    latex_count = len(re.findall(r'\\cite\{[^}]+\}', text))
    md_count = len(re.findall(r'\[@[^\]]+\]', text))
    md_inline_count = len(re.findall(r'(?<!\w)@[A-Za-z0-9_:\-.]+', text))
    return max(latex_count, md_count + md_inline_count)


def _with_timing(state: SOAState, result: dict, stage_name: str, started_at: float) -> dict:
    """Merge timing updates into node result."""
    elapsed = time.time() - started_at
    stage_start_times = dict(state.get("stage_start_times") or {})
    stage_durations = dict(state.get("stage_durations") or {})

    # Preserve any updates the node already returned.
    stage_start_times.update(result.get("stage_start_times") or {})
    stage_durations.update(result.get("stage_durations") or {})

    stage_start_times[stage_name] = started_at
    stage_durations[stage_name] = round(elapsed, 3)

    result["stage_start_times"] = stage_start_times
    result["stage_durations"] = stage_durations
    print(f"[TIMING] {stage_name}: {elapsed:.1f}s")
    return result


def record_timing(stage_name: str):
    """Decorator to instrument node runtime and persist it in state."""

    def decorator(func):
        @wraps(func)
        def wrapper(state: SOAState) -> dict:
            started_at = time.time()
            result = func(state)
            if not isinstance(result, dict):
                result = {}
            return _with_timing(state, result, stage_name, started_at)

        return wrapper

    return decorator


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


def call_llm(system_prompt_path: str, input_data: dict, output_path: str, max_retries: int = 3) -> str:
    """
    Call LLM using unified LLMClient with retry logic for JSON errors.
    
    Args:
        system_prompt_path: Path to system prompt file
        input_data: Dictionary to pass as input
        output_path: Where to save the output
        max_retries: Maximum retry attempts for JSON parsing errors
        
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
    
    # Writer and repair nodes should output Markdown, not JSON
    is_markdown_output = 'writer' in system_prompt_path or 'repair' in system_prompt_path

    def _validate_markdown_output(text: str) -> tuple[bool, str]:
        """Validate generated Markdown for writer/repair outputs."""
        stripped = text.strip()

        if stripped.startswith("```"):
            return False, "Output contains wrapper code fences instead of raw Markdown"

        if "\\documentclass" in text:
            return False, "Output appears to be LaTeX, expected Markdown"

        if len(stripped) < 500:
            return False, "Markdown output is too short/incomplete"

        if not re.search(r'(?m)^#{1,3}\s+', text):
            return False, "Markdown should contain section headings"

        if "/* Lines" in text or "omitted */" in text:
            return False, "Contains placeholder/truncation markers (e.g., /* Lines ... omitted */)"

        return True, ""
    
    if is_markdown_output:
        # For Markdown output: Don't force JSON format
        user_prompt = f"""# Input

```json
{input_json}
```

CRITICAL: Output ONLY a complete academic Markdown document (no JSON, no explanation text, no code fences).
The output will be saved directly as a `.md` file and later converted to LaTeX.

Use Pandoc-compatible markdown:
- Headings: `#`, `##`, `###`
- Citations: use `[@paper_id]` format
- Figures: `![Caption](path/to/figure.png){{#fig:label width=80%}}`
- Tables: pipe tables with a caption line above or below
- Equations: `$...$` and `$$...$$`

The document MUST be complete and self-contained. Never output placeholders such as "/* Lines ... omitted */" or partial/truncated sections.
If you are close to output limits, reduce verbosity but ALWAYS finish with complete valid Markdown.

Follow ALL formatting instructions in the system prompt exactly."""
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
    
    # Retry loop for JSON and Markdown outputs
    for attempt in range(max_retries):
        # Call LLM via unified client
        client = LLMClient()
        output_text = client.call(system_text, user_prompt)
        
        # Check for LLM failure
        if output_text.startswith("__LLM_FAILURE__:"):
            # Log failure but don't crash - return error as output
            print(f"  ⚠️  LLM call failed (attempt {attempt + 1}/{max_retries}): {output_text}")
            if attempt < max_retries - 1:
                print(f"  ↻ Retrying...")
                continue  # Retry
            # Final attempt failed
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('{"error": "' + output_text.replace('"', '\\"') + '"}')
            return output_text
        
        # Sanitize control characters for JSON output
        if output_path.endswith('.json'):
            output_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', output_text)
            try:
                json.loads(output_text)  # Validate
                # Success! Break retry loop
                print(f"  ✓ Valid JSON received")
                break
            except json.JSONDecodeError as e:
                print(f"  ⚠️  Invalid JSON from LLM (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"  ↻ Retrying with stronger instruction...")
                    # Add stronger JSON instruction for retry
                    user_prompt += "\n\nIMPORTANT: You MUST output valid JSON. Do not include any markdown formatting, code blocks, or explanatory text. Return ONLY the raw JSON object."
                    continue  # Retry
                # All retries exhausted
                print(f"  ✗ All {max_retries} attempts failed - saving error")
                error_json = '{"error": "Invalid JSON from LLM after ' + str(max_retries) + ' attempts"}'
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(error_json)
                return error_json
        else:
            # Non-JSON output (Markdown), validate integrity to catch truncation.
            is_valid_markdown, md_error = _validate_markdown_output(output_text)
            if is_valid_markdown:
                print("  ✓ Valid Markdown received")
                break

            print(f"  ⚠️  Invalid Markdown from LLM (attempt {attempt + 1}/{max_retries}): {md_error}")
            if attempt < max_retries - 1:
                print("  ↻ Retrying with stricter completion instruction...")
                user_prompt += (
                    "\n\nIMPORTANT RETRY INSTRUCTION: Your previous output was invalid because: "
                    f"{md_error}. "
                    "Return ONLY complete Pandoc-compatible Markdown with no placeholders "
                    "and include proper headings and citations."
                )
                continue

            # All retries exhausted for Markdown output
            print(f"  ✗ All {max_retries} attempts produced invalid Markdown")
            output_text = (
                "# Generation Error\n\n"
                "The LLM did not return a valid complete Markdown document after "
                f"{max_retries} attempts. Last error: {md_error}\n"
            )
            break
    
    # Save output
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_text)
    
    return output_text


# ========== NODE FUNCTIONS ==========

@record_timing("theme_builder")
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


@record_timing("reader")
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


@record_timing("extractor")
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


@record_timing("critic")
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


@record_timing("vectorize")
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
            "embeddings": {
                "source": "faiss_index",
                "count": len(temp_files)
            },
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


@record_timing("build_graph")
def build_graph_node(state: SOAState) -> dict:
    """
    Build hierarchical citation graph using extracted papers + embedding similarity.

    Returns:
        Partial state with citation_graph
    """
    print("\n[Node: Build Graph]")

    try:
        extracted_dir = "artifacts/extracted"
        index = None
        embeddings = None

        try:
            index, _ = load_vector_db()
        except Exception as e:
            print(f"  ⚠️  Could not load vector index: {e}")
            print("  ↳ Building citation graph without thematic edges from embeddings")

        graph = build_citation_graph(extracted_dir, index, embeddings)
        _write_json("artifacts/clusters/citation_graph.json", graph)

        print(f"  ✓ Citation graph built ({len(graph.get('nodes', []))} nodes, {len(graph.get('edges', []))} edges)")

        return {
            "citation_graph": graph,
            "pipeline_stage": "build_graph_complete",
            "errors": []
        }

    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "citation_graph": {"nodes": [], "edges": []},
            "pipeline_stage": "build_graph_failed",
            "errors": [{
                "node": "build_graph",
                "error": str(e)
            }]
        }


@record_timing("cluster")
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


@record_timing("interpret_clusters")
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


@record_timing("synthesis")
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
    citation_graph = state.get("citation_graph") or {"nodes": [], "edges": []}
    
    try:
        # Prepare input
        relevant_papers = [p for p in extracted.values() if "error" not in p]

        seed_ids = _collect_seed_paper_ids(clusters)
        citation_graph_context = {
            seed_id: get_grounding_context(citation_graph, seed_id, top_k=5)
            for seed_id in seed_ids
        }
        
        data = {
            "clusters": clusters,
            "papers": relevant_papers,
            "citation_graph_context": citation_graph_context,
        }
        
        agent_input = inject_contract(data, contract)
        
        # Save input
        input_path = "artifacts/synthesis/input.json"
        _write_json(input_path, agent_input)
        
        # Call LLM
        output_text = call_llm(
            "prompts/synthesis.system.txt",
            agent_input,
            "artifacts/synthesis/synthesis.json"
        )
        
        result = json.loads(output_text)

        paper_ids = sorted([p.stem for p in Path("artifacts/extracted").glob("*.json")])
        mentioned_ids = [pid for pid in paper_ids if pid in output_text]
        coverage = (len(mentioned_ids) / len(paper_ids)) if paper_ids else 0.0
        print(f"[SYNTHESIS] Paper coverage: {coverage:.1%} ({len(mentioned_ids)}/{len(paper_ids)})")

        synthesis_errors: list[dict] = []
        if paper_ids and coverage < 0.5:
            synthesis_errors.append({
                "node": "synthesis",
                "error": (
                    f"SYNTHESIS_LOW_COVERAGE: only {len(mentioned_ids)}/{len(paper_ids)} "
                    f"papers referenced in synthesis ({coverage:.1%}). Consider re-running."
                )
            })
        
        print(f"  ✓ Synthesis complete")
        
        return {
            "synthesis": result,
            "synthesis_paper_coverage": round(coverage, 4),
            "pipeline_stage": "synthesis_complete",
            "errors": synthesis_errors
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


@record_timing("writer")
def writer_node(state: SOAState) -> dict:
    """
    Generate Markdown State of the Art and convert to LaTeX.
    
    Returns:
        Partial state with soa_draft
    """
    print("\n[Node: Writer]")
    contract = state["thematic_contract"]
    synthesis = state["synthesis"]
    prisma_metadata = state.get("prisma_metadata")
    citation_graph = state.get("citation_graph") or {"nodes": [], "edges": []}
    reflector_feedback = state.get("reflector_feedback") or {}
    
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

        extracted_dir = Path("artifacts/extracted")
        paper_ids = sorted([f.stem for f in extracted_dir.glob("*.json")])
        paper_ids_str = "\n".join(f"  - {pid}" for pid in paper_ids) if paper_ids else "  - NO_PAPERS_FOUND"

        # Build paper reference sheet and numerical grounding context from extracted artifacts.
        reference_lines: list[str] = []
        numerical_facts: list[str] = []
        unit_pattern = r"\d+\.?\d*\s*(?:%|ms|s|min|hours?|km|m²)"

        for json_file in extracted_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    pdata = json.load(f)
            except Exception:
                continue

            pid = json_file.stem
            title = str(pdata.get("title", "Untitled")).strip()
            key_findings = pdata.get("key_findings", [])
            top_findings: list[str] = []
            if isinstance(key_findings, list):
                for item in key_findings:
                    if isinstance(item, str) and item.strip():
                        top_findings.append(item.strip())
                    if len(top_findings) >= 3:
                        break
            findings_part = "; ".join(top_findings) if top_findings else "No key findings available"
            reference_lines.append(f"[{pid}]: {title} — {findings_part}")

            for field_name, field_value in pdata.items():
                if isinstance(field_value, str):
                    if re.findall(unit_pattern, field_value):
                        numerical_facts.append(f"[{pid}] {field_name}: {field_value[:200]}")
                elif isinstance(field_value, list):
                    for item in field_value[:3]:
                        if isinstance(item, str) and re.findall(unit_pattern, item):
                            numerical_facts.append(f"[{pid}] {item[:200]}")

        # Inject grounding materials into user prompt payload (serialized JSON user prompt).
        agent_input["paper_ids_list"] = paper_ids
        agent_input["paper_reference_sheet"] = (
            "PAPER REFERENCE SHEET\n" + "\n".join(reference_lines)
            if reference_lines else "PAPER REFERENCE SHEET\nNo extracted papers found."
        )
        if numerical_facts:
            agent_input["key_numerical_results_to_preserve"] = (
                "KEY NUMERICAL RESULTS TO PRESERVE\n" + "\n".join(numerical_facts[:100])
            )

        # Inject synthesis intelligence blocks for originality and cross-paper writing.
        try:
            synthesis_json_path = Path("artifacts/synthesis/synthesis.json")
            synth_payload = {}
            if synthesis_json_path.exists():
                with open(synthesis_json_path, "r", encoding="utf-8") as f:
                    synth_payload = json.load(f)

            contradictions = synth_payload.get("contradictions", []) if isinstance(synth_payload, dict) else []
            convergences = synth_payload.get("convergences", []) if isinstance(synth_payload, dict) else []
            gaps = synth_payload.get("gaps", []) if isinstance(synth_payload, dict) else []

            contradiction_lines = [
                f"- {c.get('claim', '')} | papers={c.get('paper_ids', [])} | resolution={c.get('resolution', 'unknown')}"
                for c in contradictions if isinstance(c, dict)
            ]
            convergence_lines = [
                f"- {c.get('claim', '')} | papers={c.get('paper_ids', [])} | confidence={c.get('confidence', 'unknown')}"
                for c in convergences if isinstance(c, dict)
            ]
            gap_lines = [
                f"- {g.get('gap', '')} | evidence={g.get('evidence_paper_ids', [])}"
                for g in gaps if isinstance(g, dict)
            ]

            synth_intel = ["SYNTHESIS INTELLIGENCE"]
            synth_intel.append("KNOWN CONTRADICTIONS")
            synth_intel.extend(contradiction_lines or ["- None"])
            synth_intel.append("ESTABLISHED CONSENSUS")
            synth_intel.extend(convergence_lines or ["- None"])
            synth_intel.append("IDENTIFIED GAPS")
            synth_intel.extend(gap_lines or ["- None"])
            agent_input["synthesis_intelligence"] = "\n".join(synth_intel)
        except Exception as e:
            print(f"[WRITER] Warning: could not load synthesis intelligence ({e})")

        # Add graph grounding summary
        agent_input["citation_graph"] = citation_graph

        # Add focused graph neighborhood context for likely seed papers.
        writer_seed_ids = _collect_seed_paper_ids(synthesis)
        if not writer_seed_ids:
            writer_seed_ids = sorted(list((state.get("extracted_facts") or {}).keys()))[:5]

        agent_input["citation_graph_context"] = {
            seed_id: get_grounding_context(citation_graph, seed_id, top_k=5)
            for seed_id in writer_seed_ids
        }

        # Add reflector correction brief when re-writing is requested
        correction_brief = reflector_feedback.get("correction_brief")
        if correction_brief and correction_brief.get("level") != "none":
            agent_input["reflector_correction_brief"] = correction_brief
            print(f"  → Applying reflector correction brief ({correction_brief.get('level')})")
        
        # Add PRISMA metadata if available
        if prisma_metadata:
            agent_input["prisma_methodology"] = prisma_metadata
            print(f"  → Including PRISMA methodology ({prisma_metadata.get('total_papers', 0)} papers)")
        
        # Save input
        input_path = "artifacts/soa/_writer_input.json"
        _write_json(input_path, agent_input)
        
        # Build runtime system prompt with paper IDs injected.
        writer_prompt_path = Path("prompts/writer.system.txt")
        runtime_prompt_path = Path("artifacts/soa/_writer_runtime.system.txt")
        try:
            system_prompt_text = writer_prompt_path.read_text(encoding="utf-8")
            system_prompt_text = system_prompt_text.replace("{PAPER_IDS_LIST}", paper_ids_str)
            runtime_prompt_path.parent.mkdir(parents=True, exist_ok=True)
            runtime_prompt_path.write_text(system_prompt_text, encoding="utf-8")
        except Exception as e:
            print(f"[WRITER] Warning: failed to prepare runtime system prompt ({e}), using default prompt file")
            runtime_prompt_path = writer_prompt_path

        # Call LLM
        output_text = call_llm(
            str(runtime_prompt_path),
            agent_input,
            "artifacts/soa/state_of_the_art_draft.md"  # Save draft markdown for debugging
        )

        # Citation sanity check and single retry if zero citations.
        citation_count_initial = _count_citations_in_text(output_text)
        if citation_count_initial == 0:
            print("[WRITER] zero citations detected, retrying with stricter instruction")
            writer_errors = []
            writer_errors.append({
                "node": "writer",
                "error": "WRITER_NO_CITATIONS: writer produced zero citations. Retrying with stricter prompt."
            })
            retry_suffix = (
                "\n\nCRITICAL: Your previous output had ZERO citations. "
                "This is unacceptable for an academic paper. Rewrite the entire text. "
                "Every paragraph MUST contain at least one citation marker in `[@paper_id]` format. "
                "Start your output with a sentence that contains at least one citation marker."
            )
            retry_input = dict(agent_input)
            retry_input["retry_suffix_instruction"] = retry_suffix
            output_text = call_llm(
                str(runtime_prompt_path),
                retry_input,
                "artifacts/soa/state_of_the_art_draft.md"
            )
        else:
            writer_errors = []

        # Save canonical markdown file for downstream evaluator nodes.
        Path("artifacts/soa").mkdir(parents=True, exist_ok=True)
        with open("artifacts/soa/state_of_the_art.md", 'w', encoding='utf-8') as f:
            f.write(output_text)

        # Convert markdown output to LaTeX for validator/benchmark/tooling compatibility.
        try:
            converter_script = Path("scripts/markdown_to_latex.py")
            converter_cmd = [
                sys.executable,
                str(converter_script),
                "--input", "artifacts/soa/state_of_the_art.md",
                "--output", "artifacts/soa/state_of_the_art.tex",
                "--auto-bib-from-extracted", "artifacts/extracted",
                "--ensure-pandoc",
                "--standalone",
            ]
            proc = subprocess.run(converter_cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "markdown conversion failed")

            # Legacy final output sync for downstream tools expecting *_final.tex.
            with open("artifacts/soa/state_of_the_art.tex", 'r', encoding='utf-8') as src_f:
                latex_text = src_f.read()
            with open("artifacts/soa/state_of_the_art_final.tex", 'w', encoding='utf-8') as f:
                f.write(latex_text)
        except Exception as e:
            writer_errors.append({
                "node": "writer",
                "error": f"WRITER_MD_TO_TEX_CONVERSION_FAILED: {e}",
            })
            print(f"[WRITER] Warning: markdown-to-latex conversion failed ({e})")

        citation_count = _count_citations_in_text(output_text)
        paragraphs = [p for p in re.split(r"\n\s*\n", output_text) if p.strip()]
        cited_paragraphs = [p for p in paragraphs if _count_citations_in_text(p) > 0]
        print(f"[WRITER] {citation_count} citations injected across {len(cited_paragraphs)} paragraphs.")
        
        print(f"  ✓ State of the Art generated ({len(output_text)} chars)")
        
        return {
            "soa_draft": output_text,
            "pipeline_stage": "writer_complete",
            "errors": writer_errors
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


@record_timing("reflector")
def reflector_node(state: SOAState) -> dict:
    """
    Hierarchical reflector (L1 outline -> L2 section -> L3 paragraph).

    Returns:
        Partial state with reflector_feedback and reflector_passed_level.
    """
    return run_reflector(dict(state), llm_caller=call_llm)


@record_timing("rubric_evaluator")
def rubric_evaluator_node(state: SOAState) -> dict:
    """
    Multi-dimensional rubric scoring node.

    Returns:
        Partial state with rubric_scores and rubric_failing dimensions.
    """
    return run_rubric_evaluator(dict(state), llm_caller=call_llm)


@record_timing("verifier")
def verifier_node(state: SOAState) -> dict:
    """
    Check for hallucinations.
    
    Returns:
        Partial state with verification_results and verification_passed
    """
    print("\n[Node: Verifier]")
    extracted = state.get("extracted_facts", {}) or {}
    critics = state.get("critic_assessments", {}) or {}

    report = {
        "run_timestamp": datetime.now().isoformat(),
        "status": "completed",
        "total_claims_checked": 0,
        "total_violations": 0,
        "violations": [],
        "hallucination_rate": 0.0,
        "repair_triggered": False,
        "layers_executed": [],
        "error": None,
    }

    verification_errors: list[dict] = []
    passed = False

    try:
        from hallucination_detector import run_hallucination_checks, resolve_tex_path, count_cited_claims

        tex_path = resolve_tex_path()
        tex_content = tex_path.read_text(encoding="utf-8", errors="ignore")

        claim_count, _ = count_cited_claims(tex_content)
        report["total_claims_checked"] = claim_count

        if claim_count == 0:
            report["status"] = "skipped_no_citations"
            report["error"] = "No cited sentences found in LaTeX output. Run Fix 1 first."
            report["layers_executed"] = []
        else:
            extracted_db = {
                pid: pdata for pid, pdata in extracted.items()
                if isinstance(pdata, dict) and "error" not in pdata
            }
            critic_db = {
                pid: pdata for pid, pdata in critics.items()
                if isinstance(pdata, dict) and "error" not in pdata
            }

            detector_report = run_hallucination_checks(tex_content, extracted_db, critic_db)
            details = detector_report.get("details", []) if isinstance(detector_report, dict) else []
            total_violations = int(detector_report.get("total_violations", len(details))) if isinstance(detector_report, dict) else len(details)

            report["status"] = "completed"
            report["total_violations"] = total_violations
            report["violations"] = details if isinstance(details, list) else []
            report["hallucination_rate"] = (
                total_violations / report["total_claims_checked"]
                if report["total_claims_checked"] > 0 else 0.0
            )
            report["repair_triggered"] = total_violations > 0
            report["layers_executed"] = [
                "claim_grounding",
                "citation_verification",
                "fact_coverage",
                "contradiction_check",
            ]

        passed = report["total_violations"] == 0 and report["status"] in {"completed", "partial"}

    except Exception as e:
        report["status"] = "failed"
        report["error"] = str(e)
        report["repair_triggered"] = False
        verification_errors.append({
            "node": "verifier",
            "error": f"VERIFIER_FAILED: {e}"
        })
        print(f"[VERIFIER] ERROR: {e}")

    finally:
        try:
            Path("artifacts/soa").mkdir(parents=True, exist_ok=True)
            with open("artifacts/soa/hallucination_report.json", "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            print(
                f"[VERIFIER] Report written: {report['total_violations']} violations "
                f"in {report['total_claims_checked']} claims checked."
            )
        except Exception as write_err:
            verification_errors.append({
                "node": "verifier",
                "error": f"VERIFIER_REPORT_WRITE_FAILED: {write_err}"
            })

    return {
        "verification_results": report.get("violations", []),
        "verification_passed": passed,
        "hallucination_report": report,
        "pipeline_stage": "verifier_complete" if report.get("status") != "failed" else "verifier_failed",
        "errors": verification_errors,
    }


@record_timing("repair")
def repair_node(state: SOAState) -> dict:
    """
    Repair hallucinated content in Markdown and regenerate LaTeX.
    
    Returns:
        Partial state with updated soa_draft and incremented repair_iteration
    """
    print("\n[Node: Repair]")
    violations = state["verification_results"]
    soa_draft = state["soa_draft"]
    extracted = state["extracted_facts"]
    iteration = state["repair_iteration"]
    rubric_failing = state.get("rubric_failing", [])
    
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
        print(f"  Rubric failing dimensions: {', '.join(rubric_failing) if rubric_failing else 'None'}")

        repair_input = {
            "soa_draft": soa_draft,
            "verification_results": violations,
            "rubric_failing": rubric_failing,
            "extracted_paper_ids": sorted(list(extracted.keys())),
            "repair_iteration": iteration + 1,
        }

        _write_json("artifacts/soa/_repair_input.json", repair_input)

        repaired_draft = call_llm(
            "prompts/repair.system.txt",
            repair_input,
            "artifacts/soa/state_of_the_art_repaired.md"
        )

        # Keep canonical markdown path in sync for downstream tooling.
        with open("artifacts/soa/state_of_the_art.md", 'w', encoding='utf-8') as f:
            f.write(repaired_draft)

        # Re-generate LaTeX after repair.
        converter_script = Path("scripts/markdown_to_latex.py")
        converter_cmd = [
            sys.executable,
            str(converter_script),
            "--input", "artifacts/soa/state_of_the_art.md",
            "--output", "artifacts/soa/state_of_the_art.tex",
            "--auto-bib-from-extracted", "artifacts/extracted",
            "--ensure-pandoc",
            "--standalone",
        ]
        proc = subprocess.run(converter_cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "markdown conversion failed during repair")

        with open("artifacts/soa/state_of_the_art.tex", 'r', encoding='utf-8') as src_f:
            latex_text = src_f.read()
        with open("artifacts/soa/state_of_the_art_final.tex", 'w', encoding='utf-8') as f:
            f.write(latex_text)
        
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


@record_timing("final_output")
def final_output_node(state: SOAState) -> dict:
    """Finalize run metadata and persist timing summary."""
    print("\n[Node: Final Output]")

    pipeline_start = float(state.get("pipeline_start_time", 0.0) or 0.0)
    total_seconds = (time.time() - pipeline_start) if pipeline_start > 0 else 0.0
    total_minutes = total_seconds / 60.0

    stage_durations = dict(state.get("stage_durations") or {})
    non_zero = {k: v for k, v in stage_durations.items() if isinstance(v, (int, float)) and v >= 0.0}

    slowest_stage = None
    fastest_stage = None
    if non_zero:
        slowest_stage = max(non_zero.items(), key=lambda kv: kv[1])[0]
        fastest_stage = min(non_zero.items(), key=lambda kv: kv[1])[0]

    print(f"[TIMING] Total pipeline: {total_minutes:.1f} minutes")

    timing_summary = {
        "total_seconds": round(total_seconds, 3),
        "total_minutes": round(total_minutes, 3),
        "stage_durations": non_zero,
        "slowest_stage": slowest_stage,
        "fastest_stage": fastest_stage,
    }

    try:
        timing_path = Path("artifacts/benchmark/timing_report.json")
        timing_path.parent.mkdir(parents=True, exist_ok=True)
        with open(timing_path, "w", encoding="utf-8") as f:
            json.dump(timing_summary, f, indent=2)
    except Exception as e:
        print(f"[TIMING] Warning: failed to write timing report ({e})")

    return {
        "total_wall_clock_seconds": round(total_seconds, 3),
        "pipeline_stage": "final_output_complete",
        "errors": [],
    }
