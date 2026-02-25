#!/usr/bin/env python3
"""
Thematic Contract Builder - Stage 0
Single source of truth that defines what matters before any agent runs.

This module creates an immutable thematic contract that guides all downstream agents
to focus only on globally relevant information.
"""

import json
import subprocess
from pathlib import Path
from src.toon_utils import dump_toon, load_toon, loads as toon_loads


THEME_CONTRACT_FILE = "THEMATIC_CONTRACT.toon"


def build_thematic_contract(user_input_file="theme_input.json", model=None):
    """
    Build the global thematic contract from user input.
    
    This runs ONCE at the start of the pipeline and creates an immutable
    contract that all agents must obey.
    
    Args:
        user_input_file: Path to user's research scope definition
        model: LLM model to use
        
    Returns:
        Dictionary containing the thematic contract
    """
    print("\n" + "="*60)
    print("STAGE 0: BUILDING THEMATIC CONTRACT")
    print("="*60)
    
    # Check if user input exists
    if not Path(user_input_file).exists():
        print(f"[!] Theme input not found: {user_input_file}")
        print("[+] Creating template...")
        create_theme_input_template(user_input_file)
        print(f"\n[!] Please edit {user_input_file} with your research scope")
        print("[!] Then run the pipeline again")
        raise RuntimeError("Thematic contract requires user input")
    
    # Load user input
    with open(user_input_file, 'r', encoding='utf-8') as f:
        user_input = json.load(f)
    
    print(f"[+] Loaded research scope definition")
    print(f"    Title: {user_input.get('title', 'Not specified')}")
    
    # Load system prompt
    system_prompt_path = Path("prompts/theme_builder.system.txt")
    if not system_prompt_path.exists():
        raise RuntimeError(f"System prompt not found: {system_prompt_path}")
    
    with open(system_prompt_path, 'r', encoding='utf-8') as f:
        system_prompt = f.read()
    
    # Construct combined prompt for Qwen
    user_input_json = json.dumps(user_input, indent=2)
    combined_prompt = f"""{system_prompt}

# Input

```json
{user_input_json}
```

Generate a thematic contract based on the above input. Return ONLY valid JSON with no markdown formatting."""
    
    # Run theme builder agent
    output_file = THEME_CONTRACT_FILE
    
    try:
        print(f"[+] Generating thematic contract with Qwen...")
        
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
            timeout=120
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Theme builder failed: {result.stderr}")
        
        # Parse JSON from output
        output_text = result.stdout.strip()
        
        # Remove markdown code blocks if present
        if output_text.startswith("```"):
            lines = output_text.split("\n")
            # Find first line after opening ``` and last line before closing ```
            start_idx = 1
            if lines[0].startswith("```json"):
                start_idx = 1
            end_idx = len(lines) - 1
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() == "```":
                    end_idx = i
                    break
            output_text = "\n".join(lines[start_idx:end_idx])
        
        # Try to find JSON object in the text
        json_start = output_text.find('{')
        json_end = output_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            output_text = output_text[json_start:json_end]
        
        contract = toon_loads(output_text)
        
        # Validate contract structure
        required_fields = [
            "global_theme",
            "core_questions",
            "in_scope",
            "out_of_scope",
            "preferred_methods",
            "evaluation_focus"
        ]
        
        for field in required_fields:
            if field not in contract:
                raise ValueError(f"Theme contract missing required field: {field}")
        
        # Save final contract
        dump_toon(contract, output_file)
        
        print(f"[✓] Thematic contract created: {output_file}")
        print(f"\n[Theme] {contract['global_theme']}")
        print(f"[In Scope] {len(contract['in_scope'])} items")
        print(f"[Out of Scope] {len(contract['out_of_scope'])} items")
        print(f"[Core Questions] {len(contract['core_questions'])}")
        
        return contract
        
    except json.JSONDecodeError as e:
        print(f"[!] Failed to parse JSON from Qwen output: {e}")
        print(f"[!] Raw output: {result.stdout[:500]}")
        raise
    except Exception as e:
        print(f"[!] Error building thematic contract: {e}")
        raise


def load_thematic_contract(contract_file=THEME_CONTRACT_FILE):
    """
    Load existing thematic contract.
    
    Returns:
        Dictionary containing the thematic contract
    """
    if not Path(contract_file).exists():
        # Try fallback to .json for backward compatibility
        json_file = contract_file.replace('.toon', '.json')
        if Path(json_file).exists():
            contract_file = json_file
        else:
            raise RuntimeError(f"Thematic contract not found: {contract_file}")
    
    if contract_file.endswith('.toon'):
        return load_toon(contract_file)
    else:
        with open(contract_file, 'r', encoding='utf-8') as f:
            return json.load(f)


def create_theme_input_template(output_file="theme_input.json"):
    """
    Create a template for user to fill in their research scope.
    """
    template = {
        "title": "Your Thesis/Paper Title Here",
        "research_goals": [
            "goal 1 (e.g., dynamic ambulance relocation)",
            "goal 2 (e.g., predict-then-optimize methods)",
            "goal 3 (e.g., real-time decision making)",
            "goal 4 (e.g., urban EMS systems)"
        ],
        "specific_constraints": [
            "Must focus on operational decisions, not clinical outcomes",
            "Real-time or near-real-time methods only",
            "Urban context primarily"
        ],
        "what_to_exclude": [
            "Hospital staffing",
            "Triage policy design",
            "Non-emergency logistics",
            "Clinical outcome prediction"
        ]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2)
    
    print(f"[✓] Template created: {output_file}")


def detect_theme_violation(text, contract):
    """
    Detect if text violates the thematic contract.
    
    This is a hard guardrail - violations are automatically flagged.
    
    Args:
        text: Text to check
        contract: Thematic contract dictionary
        
    Returns:
        List of violations (empty if clean)
    """
    violations = []
    text_lower = text.lower()
    
    # Check for out-of-scope terms
    for oos in contract.get("out_of_scope", []):
        if len(oos) > 3 and oos.lower() in text_lower:
            violations.append({
                "type": "out_of_scope",
                "term": oos,
                "severity": "high"
            })
    
    return violations


def thematic_filter_paper(paper, contract):
    """
    Determine if a paper is thematically relevant.
    
    This is used before embedding to ensure vector DB contains only relevant papers.
    Uses flexible keyword matching instead of exact phrase matching.
    
    Args:
        paper: Extracted paper dictionary
        contract: Thematic contract dictionary
        
    Returns:
        Boolean - True if paper is relevant
    """
    # Get in_scope and out_of_scope terms from contract
    in_scope = contract.get("in_scope", [])
    out_of_scope = contract.get("out_of_scope", [])
    
    # Recursively extract all text from nested structures
    def extract_all_text(obj, max_depth=5, current_depth=0):
        """Recursively extract text from any JSON structure"""
        if current_depth > max_depth:
            return []
        
        texts = []
        if isinstance(obj, dict):
            for v in obj.values():
                texts.extend(extract_all_text(v, max_depth, current_depth + 1))
        elif isinstance(obj, list):
            for item in obj:
                texts.extend(extract_all_text(item, max_depth, current_depth + 1))
        elif isinstance(obj, str):
            if len(obj) > 5:  # Skip very short strings
                texts.append(obj)
        elif obj is not None:
            texts.append(str(obj))
        return texts
    
    # Collect all text from the paper
    paper_text_parts = extract_all_text(paper)
    
    # Combine all text
    paper_text = " ".join(paper_text_parts).lower()
    
    # Extract key terms from in_scope items (e.g., "ambulance", "relocation", "ems", "demand", etc.)
    in_scope_keywords = set()
    for scope_item in in_scope:
        # Split into words and keep substantive ones (3+ chars, not common words)
        words = scope_item.lower().split()
        keywords = [w.strip('(),.:;') for w in words if len(w) > 3 and w not in {'using', 'with', 'from', 'that', 'this', 'have'}]
        in_scope_keywords.update(keywords)
    
    # Check for keyword matches (need at least 2 keywords to match)
    keyword_matches = sum(1 for kw in in_scope_keywords if kw in paper_text)
    keyword_threshold = min(3, max(1, len(in_scope_keywords) // 4))  # Adaptive threshold
    
    in_scope_match = keyword_matches >= keyword_threshold
    
    # Check for out-of-scope terms (strict matching)
    out_of_scope_match = any(
        oos.lower() in paper_text 
        for oos in out_of_scope 
        if len(oos) > 3
    )
    
    # Paper is relevant if it matches enough keywords AND does not match out-of-scope
    is_relevant = in_scope_match and not out_of_scope_match
    
    return is_relevant


def inject_theme_into_input(data, contract):
    """
    Inject thematic contract into agent input data.
    
    This ensures every agent receives the global theme.
    
    Args:
        data: Agent input dictionary
        contract: Thematic contract dictionary
        
    Returns:
        Modified data with contract injected
    """
    data["thematic_contract"] = contract
    return data


def print_theme_summary(contract):
    """
    Print a human-readable summary of the thematic contract.
    """
    print("\n" + "="*60)
    print("THEMATIC CONTRACT SUMMARY")
    print("="*60)
    
    print(f"\n[Global Theme]")
    print(f"  {contract['global_theme']}")
    
    print(f"\n[Core Questions] ({len(contract['core_questions'])})")
    for i, q in enumerate(contract['core_questions'], 1):
        print(f"  {i}. {q}")
    
    print(f"\n[In Scope] ({len(contract['in_scope'])})")
    for item in contract['in_scope']:
        print(f"  ✓ {item}")
    
    print(f"\n[Out of Scope] ({len(contract['out_of_scope'])})")
    for item in contract['out_of_scope']:
        print(f"  ✗ {item}")
    
    print(f"\n[Preferred Methods]")
    for method in contract['preferred_methods']:
        print(f"  • {method}")
    
    print(f"\n[Evaluation Focus]")
    for metric in contract['evaluation_focus']:
        print(f"  • {metric}")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "template":
            create_theme_input_template()
        elif sys.argv[1] == "build":
            contract = build_thematic_contract()
            print_theme_summary(contract)
        elif sys.argv[1] == "show":
            contract = load_thematic_contract()
            print_theme_summary(contract)
        else:
            print("Usage:")
            print("  python theme_builder.py template  - Create input template")
            print("  python theme_builder.py build     - Build thematic contract")
            print("  python theme_builder.py show      - Show existing contract")
    else:
        print("Creating theme input template...")
        create_theme_input_template()
        print("\nEdit theme_input.json, then run:")
        print("  python theme_builder.py build")
