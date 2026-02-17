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
import argparse
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
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'qwen')  # CLI provider: qwen, claude, gemini, openai, kilo, etc.
LLM_MODEL = os.getenv('LLM_MODEL', None)  # Specific model within the provider
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.3'))
LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '300'))  # Timeout in seconds

# Pipeline Configuration
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '10'))  # For parallel execution
MAX_PDF_CHARS = int(os.getenv('MAX_PDF_CHARS', '30000'))  # Limit PDF text to ~15-20 pages
CLUSTER_COUNT = int(os.getenv('CLUSTER_COUNT', '6'))  # Number of clusters for similarity clustering


# ========== LLM PROVIDER CONFIGURATIONS ==========

LLM_PROVIDERS = {
    'qwen': {
        'command': 'qwen',
        'model_flag': '-m',
        'auto_yes': ['-y'],
        'supports_temperature': False,
        'supports_system_prompt': True,
        'input_method': 'stdin',
        'output_method': 'stdout'
    },
    'claude': {
        'command': 'claude',
        'model_flag': '-m',
        'auto_yes': [],
        'supports_temperature': True,
        'temperature_flag': '--temperature',
        'supports_system_prompt': True,
        'input_method': 'stdin',
        'output_method': 'stdout'
    },
    'gemini': {
        'command': 'gemini',
        'model_flag': '-m',
        'auto_yes': [],
        'supports_temperature': True,
        'temperature_flag': '--temperature',
        'supports_system_prompt': True,
        'input_method': 'stdin',
        'output_method': 'stdout'
    },
    'openai': {
        'command': 'openai',
        'model_flag': '-m',
        'auto_yes': [],
        'supports_temperature': True,
        'temperature_flag': '--temperature',
        'supports_system_prompt': True,
        'input_method': 'stdin',
        'output_method': 'stdout'
    },
    'kilo': {
        'command': 'kilo run',
        'model_flag': '-m',
        'auto_yes': ['--auto', '--format', 'json'],
        'supports_temperature': False,
        'supports_system_prompt': True,
        'input_method': 'args',
        'output_method': 'stdout'
    },
    'glm': {
        'command': 'glm',
        'model_flag': '--model',
        'auto_yes': [],
        'supports_temperature': True,
        'temperature_flag': '--temperature',
        'supports_system_prompt': True,
        'input_method': 'stdin',
        'output_method': 'stdout'
    }
}


# ========== LLM INVOCATION ==========

def get_provider_config(provider_name):
    """
    Get configuration for specified LLM provider.
    
    Args:
        provider_name: Name of the provider (qwen, claude, gemini, etc.)
        
    Returns:
        dict: Provider configuration
        
    Raises:
        ValueError: If provider is not supported
    """
    if provider_name not in LLM_PROVIDERS:
        available = ', '.join(LLM_PROVIDERS.keys())
        raise ValueError(
            f"Unsupported LLM provider: '{provider_name}'. "
            f"Available providers: {available}"
        )
    return LLM_PROVIDERS[provider_name]

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


def run_llm(system_prompt, input_file, output_file, provider=LLM_PROVIDER, model=LLM_MODEL, temperature=LLM_TEMPERATURE):
    """
    Invoke LLM CLI with specified parameters.
    
    This function supports multiple LLM providers (Qwen, Claude, Gemini, OpenAI, Kilo, GLM, etc.)
    and automatically adapts to their specific CLI interfaces.
    
    Args:
        system_prompt: Path to system prompt file
        input_file: Path to input file
        output_file: Path to output file
        provider: LLM provider name (qwen, claude, gemini, openai, kilo, glm, etc.)
        model: Model name (provider-specific, e.g., 'claude-sonnet-4.5', 'gpt-5.2', 'gemini-3-pro')
        temperature: Temperature setting (0.0-1.0, if supported by provider)
        
    Raises:
        RuntimeError: If LLM execution fails
        ValueError: If provider is not supported
    """
    # Get provider configuration
    try:
        config = get_provider_config(provider)
    except ValueError as e:
        raise ValueError(f"LLM provider error: {e}")
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
        # Build command based on provider configuration
        if provider == 'kilo':
            # Kilo has a special interface - needs 'kilo run' as base command
            cmd = ['kilo', 'run']
            
            # Add model flag if specified (kilo uses format: kilo/provider/model)
            if model:
                # If user provided short form like 'glm-5', expand to full kilo format
                if not model.startswith('kilo/'):
                    if 'glm' in model.lower():
                        model = f'kilo/z-ai/{model}:free'
                    else:
                        model = f'kilo/{model}'
                cmd.extend(['-m', model])
            
            # Add auto-approval flags for non-interactive pipeline usage
            cmd.extend(['--auto', '--format', 'json'])
            
            # For kilo, save prompt to temp file and use --file option
            # This avoids command-line length limits
            # Note: message must come BEFORE -f flag in kilo CLI
            temp_prompt_file = f"{output_file}.prompt.txt"
            try:
                with open(temp_prompt_file, 'w', encoding='utf-8') as f:
                    f.write(combined_prompt)
                
                # Add message first, then file attachment
                cmd.append("Process the attached file and respond with valid JSON only.")
                cmd.extend(['-f', temp_prompt_file])
                
                # Invoke Kilo with file attachment
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=LLM_TIMEOUT
                )
            finally:
                # Clean up temp prompt file
                Path(temp_prompt_file).unlink(missing_ok=True)
        else:
            # Standard provider interface (qwen, claude, gemini, openai, glm)
            cmd = [config['command']]
            
            # Add model flag if specified
            if model:
                cmd.extend([config['model_flag'], model])
            
            # Add temperature flag if supported and specified
            if config['supports_temperature'] and temperature is not None:
                cmd.extend([config['temperature_flag'], str(temperature)])
            
            # Add auto-yes flags (for providers that need confirmation)
            cmd.extend(config['auto_yes'])
            
            # Invoke LLM CLI with stdin/stdout
            result = subprocess.run(
                cmd,
                input=combined_prompt,
                capture_output=True,
                text=True,
                timeout=LLM_TIMEOUT
            )
        
        if result.returncode != 0:
            raise RuntimeError(
                f"{provider.upper()} CLI failed (exit code {result.returncode}): {result.stderr}"
            )
        
        # Parse and clean output
        output_text = result.stdout.strip()
        
        # Special handling for Kilo's JSON event stream
        if provider == 'kilo':
            # Kilo returns a stream of JSON events; extract text from "text" events
            text_chunks = []
            for line in output_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if event.get('type') == 'text' and 'part' in event:
                        text_content = event['part'].get('text', '')
                        if text_content:
                            text_chunks.append(text_content)
                except json.JSONDecodeError:
                    # Skip malformed JSON lines
                    continue
            
            if text_chunks:
                output_text = '\n'.join(text_chunks)
            else:
                raise RuntimeError(f"No text content found in Kilo response. Raw output: {output_text[:500]}")
        
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
        
        # Validate JSON before saving
        try:
            json.loads(output_text)  # Validate it's valid JSON
        except json.JSONDecodeError as je:
            raise RuntimeError(
                f"LLM output is not valid JSON: {je}. "
                f"Output preview: {output_text[:500]}"
            )
        
        # Save output
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_text)
        
        return output_file
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{provider.upper()} timeout after {LLM_TIMEOUT}s for {input_file}")
    except Exception as e:
        raise RuntimeError(f"{provider.upper()} error: {e}")


def load_json(path, skip_on_error=False):
    """Load and validate JSON file.
    
    Args:
        path: Path to JSON file
        skip_on_error: If True, return None on error instead of raising exception
    
    Returns:
        Parsed JSON data or None if skip_on_error=True and error occurs
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                raise ValueError("File is empty")
            return json.loads(content)
    except Exception as e:
        error_msg = f"Failed to load JSON from {path}: {e}"
        if skip_on_error:
            print(f"    [!] Warning: {error_msg} - Skipping this file")
            return None
        raise RuntimeError(error_msg)


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
        run_llm(
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
        run_llm(
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
        run_llm(
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
    extracted_data_raw = [load_json(f, skip_on_error=True) for f in extracted_files]
    
    # Filter out None values (corrupted/missing files)
    extracted_data = [data for data in extracted_data_raw if data is not None]
    
    if len(extracted_data) < len(extracted_files):
        skipped = len(extracted_files) - len(extracted_data)
        print(f"[!] Warning: Skipped {skipped} corrupted/invalid JSON files")
    
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
                if i < len(extracted_data) and extracted_data[i] in relevant_papers:
                    critic_json = load_json(critic_file, skip_on_error=True)
                    if critic_json is not None:
                        critic_data.append(critic_json)
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
    
    run_llm(
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
        "papers": [p for p in [load_json(f, skip_on_error=True) for f in extracted_files] if p is not None]
    }
    
    synthesis_input = prepare_agent_input(data, contract, "artifacts/synthesis/input.json")
    
    output = "artifacts/synthesis/synthesis.json"
    
    print("[+] Running synthesis agent")
    run_llm(
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
    run_llm(
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

def main(force_reprocess=False):
    """
    Main orchestrator pipeline with thematic priming.
    
    Args:
        force_reprocess: If True, re-process all papers from scratch (ignore existing artifacts)
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
    
    # If force_reprocess is enabled, clear existing artifacts
    if force_reprocess and existing_extracted:
        print("\n[!] Force re-processing enabled: ignoring existing artifacts")
        existing_extracted = []
        existing_critics = []
    
    # Check for raw papers
    papers_dir = Path("papers")
    pdfs = list(papers_dir.glob("*.pdf"))
    
    if not pdfs:
        print("[!] No PDF files found in papers/ directory")
        print("[!] Please add your papers to the papers/ folder")
        sys.exit(1)
    
    # Build set of paper names that have been extracted (without extension)
    # Also validate that extracted files are valid JSON (not corrupted)
    extracted_names = set()
    valid_extracted = []
    corrupted_files = []
    
    for f in existing_extracted:
        try:
            # Try to load to verify it's valid JSON
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read().strip()
                if content and not content.startswith("JSON output written"):
                    json.loads(content)  # Validate JSON
                    extracted_names.add(Path(f).stem)
                    valid_extracted.append(f)
                else:
                    corrupted_files.append(Path(f).stem)
        except (json.JSONDecodeError, ValueError):
            corrupted_files.append(Path(f).stem)
    
    # Update existing_extracted to only include valid files
    existing_extracted = valid_extracted
    
    # Filter critics to match valid extracted files
    valid_critic_names = {Path(f).stem for f in existing_extracted}
    existing_critics = [c for c in existing_critics if Path(c).stem in valid_critic_names]
    
    if corrupted_files:
        print(f"\n[!] Found {len(corrupted_files)} corrupted/invalid files that will be re-extracted:")
        for cf in corrupted_files[:5]:
            print(f"    - {cf}")
        if len(corrupted_files) > 5:
            print(f"    ... and {len(corrupted_files) - 5} more")
    
    pdf_names = {pdf.stem for pdf in pdfs}
    
    # Find papers that need processing (new, failed, or corrupted)
    missing_papers = (pdf_names - extracted_names) | set(corrupted_files)
    
    # Determine if we can skip stages 1-3
    if existing_extracted and not missing_papers:
        print(f"\n[+] Found {len(existing_extracted)} existing extracted papers")
        print(f"[+] All {len(pdfs)} papers already processed")
        print("[+] Skipping stages 1-3 (already completed)")
        extracted = existing_extracted
        critics = existing_critics
    elif existing_extracted and missing_papers:
        # Partial skip - process only new/missing papers
        print(f"\n[+] Found {len(existing_extracted)} existing extracted papers")
        print(f"[+] Found {len(missing_papers)} new/unprocessed papers: {', '.join(list(missing_papers)[:5])}{'...' if len(missing_papers) > 5 else ''}")
        print(f"[+] Processing only new papers")
        
        # Filter PDFs to only process missing ones
        pdfs_to_process = [pdf for pdf in pdfs if pdf.stem in missing_papers]
        
        print(f"\n[+] Processing {len(pdfs_to_process)} papers")
        
        # Stage 1: Reader Agent (only for new papers)
        print("\n[Stage 1] Reading Papers (incremental)")
        print("="*60)
        reader_outputs = []
        for pdf in pdfs_to_process:
            result = run_reader(pdf)
            if result:
                reader_outputs.append(result)
        
        if not reader_outputs:
            print("[!] No new papers were successfully read")
            # Use existing artifacts
            extracted = existing_extracted
            critics = existing_critics
        else:
            print(f"\n[✓] Successfully read {len(reader_outputs)} new papers")
            
            # Stage 2+3: Extraction and Critique (parallel, only for new papers)
            new_extracted, new_critics = run_extraction_and_critique(reader_outputs)
            
            # Combine with existing artifacts
            extracted = existing_extracted + new_extracted
            critics = existing_critics + new_critics
            
            print(f"\n[✓] Total papers: {len(extracted)} ({len(existing_extracted)} existing + {len(new_extracted)} new)")
    else:
        # No existing artifacts - process all papers
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
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="SOA-CLI: Multi-Agent State of the Art Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python soa_cli.py              # Normal run (incremental processing)
  python soa_cli.py --force      # Re-process all papers from scratch
  python soa_cli.py --help       # Show this help message
        """
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force re-processing of all papers (ignore existing artifacts)'
    )
    
    args = parser.parse_args()
    
    try:
        main(force_reprocess=args.force)
    except KeyboardInterrupt:
        print("\n[!] Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
