"""
Automatic rewrite and self-repair loop for State of the Art.
Built according to rewriter.md specifications.

Principle: Never rewrite the whole document.
Only rewrite provably broken sentences using explicit evidence.
"""

import json
from pathlib import Path
from .hallucination_detector import run_hallucination_checks
from src.toon_utils import load_toon, dump_toon


MAX_REPAIR_ITERATIONS = 3


def get_evidence(violation, extracted_db):
    """
    Get supporting evidence for a violation repair.
    Evidence must come from cited papers or be empty.
    """
    evidence = []
    
    # Get cited paper IDs
    citations = violation.get("citations", [])
    
    for pid in citations:
        if pid not in extracted_db:
            continue
        
        paper = extracted_db[pid]
        
        # Collect relevant facts
        evidence.extend(paper.get("claimed_contributions", []))
        evidence.extend(paper.get("limitations_explicit", []))
        evidence.extend(paper.get("assumptions", []))
        
        # Add method information
        if paper.get("prediction_component", {}).get("method"):
            evidence.append(f"Prediction method: {paper['prediction_component']['method']}")
        
        if paper.get("optimization_component", {}).get("method"):
            evidence.append(f"Optimization method: {paper['optimization_component']['method']}")
    
    return {
        "paper_id": citations,
        "facts": evidence[:10]  # Limit to top 10 facts
    }


def run_repair_agent(sentence, issue, evidence):
    """
    Run the repair agent to rewrite a single sentence.
    
    Args:
        sentence: The sentence to repair
        issue: The detected issue type
        evidence: Allowed evidence for rewriting
        
    Returns:
        Repaired sentence
    """
    import os
    from pathlib import Path
    from src.llm_client import LLMClient
    
    # Prepare input for repair agent
    repair_input = {
        "original_sentence": sentence,
        "issue_type": issue,
        "allowed_evidence": evidence
    }
    
    try:
        # Load repair system prompt
        system_prompt_path = Path("prompts/repair.system.txt")
        if not system_prompt_path.exists():
            print(f"[!] Repair system prompt not found: {system_prompt_path}")
            return sentence
        
        with open(system_prompt_path, 'r', encoding='utf-8') as f:
            system_prompt = f.read()
        
        # Create user prompt with repair input
        user_prompt = f"""# Repair Request

Original Sentence: {sentence}

Issue Type: {issue}

Allowed Evidence:
```json
{json.dumps(evidence, indent=2)}
```

Rewrite the sentence to fix the issue using ONLY the allowed evidence. Return ONLY the repaired sentence with no explanations or markdown."""
        
        # Use LLM client for repair
        client = LLMClient(
            provider=os.getenv('LLM_PROVIDER', 'qwen'),
            model=os.getenv('LLM_MODEL', 'qwen-turbo'),
            timeout=60,
            max_retries=2
        )
        
        repaired = client.call(
            system=system_prompt,
            user=user_prompt,
            temperature=0.2,
            max_tokens=512
        )
        
        repaired = repaired.strip()
        
        # Remove any markdown formatting
        if repaired.startswith("```") or repaired.startswith('"'):
            lines = repaired.split("\n")
            repaired = "\n".join(
                line for line in lines 
                if not line.strip().startswith("```")
            ).strip().strip('"')
        
        return repaired if repaired else sentence
        
    except Exception as e:
        print(f"[!] Error in repair agent: {e}")
        return sentence


def repair_document(soa_text, violations, extracted_db):
    """
    Iteratively repair document until all violations are fixed or max iterations reached.
    
    Args:
        soa_text: Original SoA text
        violations: List of detected violations
        extracted_db: Database of extracted papers
        
    Returns:
        (repaired_text, success)
    """
    repaired_text = soa_text
    
    print("\n" + "="*60)
    print("STARTING REPAIR LOOP")
    print("="*60)
    
    for iteration in range(MAX_REPAIR_ITERATIONS):
        print(f"\n[Iteration {iteration + 1}/{MAX_REPAIR_ITERATIONS}]")
        
        if not violations:
            print("[✓] No violations detected - document is clean")
            return repaired_text, True
        
        print(f"[+] Repairing {len(violations)} violations")
        
        # Process each violation
        repairs_made = 0
        for v in violations:
            # Skip violations without specific claims
            if "claim" not in v:
                continue
            
            claim = v["claim"]
            issue = v.get("issue", "unspecified")
            
            print(f"    Repairing: {claim[:60]}...")
            
            # Get evidence for repair
            evidence = get_evidence(v, extracted_db)
            
            # Run repair agent
            repaired_sentence = run_repair_agent(claim, issue, evidence)
            
            # Replace in text
            if repaired_sentence != claim:
                repaired_text = repaired_text.replace(claim, repaired_sentence)
                repairs_made += 1
                print(f"      ✓ Repaired")
            else:
                print(f"      - No change")
        
        print(f"[+] Made {repairs_made} repairs")
        
        # Re-validate
        print(f"[+] Re-validating document...")
        
        # Re-run hallucination checks
        report = run_hallucination_checks(repaired_text, extracted_db)
        
        # Update violations for next iteration
        violations = [v for v in report["details"] if "claim" in v]
        
        if len(violations) == 0:
            print("[✓] All violations resolved!")
            return repaired_text, True
    
    # Max iterations reached
    print(f"\n[!] Max iterations ({MAX_REPAIR_ITERATIONS}) reached")
    print(f"[!] {len(violations)} unrepairable violations remain")
    
    # Generate failure report
    failure_report = {
        "status": "failed",
        "iterations": MAX_REPAIR_ITERATIONS,
        "unrepairable_claims": [
            {
                "sentence": v.get("claim", ""),
                "reason": v.get("issue", "unknown")
            }
            for v in violations
            if "claim" in v
        ]
    }
    
    dump_toon(failure_report, "artifacts/soa/repair_failure.toon")
    
    print("[✓] Failure report saved to artifacts/soa/repair_failure.toon")
    
    return repaired_text, False


def repair_pipeline(soa_file, extracted_db, critic_db=None):
    """
    Complete repair pipeline: load, check, repair, save.
    
    Args:
        soa_file: Path to SoA LaTeX file
        extracted_db: Dictionary of extracted papers
        critic_db: Dictionary of critic assessments (optional)
        
    Returns:
        success status
    """
    # Load SoA text
    with open(soa_file, 'r', encoding='utf-8') as f:
        soa_text = f.read()
    
    print(f"[+] Loaded SoA from {soa_file}")
    
    # Run initial hallucination checks
    print("[+] Running initial hallucination detection...")
    violations_report = run_hallucination_checks(soa_text, extracted_db, critic_db)
    
    # Check if repair is needed
    if violations_report["total_violations"] == 0:
        print("[✓] No violations detected - SoA is clean")
        
        # Save final version
        output_file = "artifacts/soa/state_of_the_art_final.tex"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(soa_text)
        
        print(f"[✓] Saved final SoA to {output_file}")
        return True
    
    # Extract violations with claims
    violations = [v for v in violations_report["details"] if "claim" in v or v.get("detector") == "fact_coverage"]
    
    print(f"[!] {len(violations)} violations detected - starting repair")
    
    # Run repair loop
    final_text, success = repair_document(soa_text, violations, extracted_db)
    
    # Save final version
    if success:
        output_file = "artifacts/soa/state_of_the_art_final.tex"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_text)
        
        print(f"\n[✓] Successfully repaired SoA")
        print(f"[✓] Saved final version to {output_file}")
        return True
    else:
        output_file = "artifacts/soa/state_of_the_art_repaired_partial.tex"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_text)
        
        print(f"\n[!] Partial repair only")
        print(f"[!] Saved partially repaired version to {output_file}")
        print(f"[!] See artifacts/soa/repair_failure.json for details")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python repair_loop.py <soa_file> <extracted_folder>")
        sys.exit(1)
    
    # Load extracted papers
    extracted_path = Path(sys.argv[2])
    extracted_db = {}
    # Support both .toon and .json files
    for f in list(extracted_path.glob("*.toon")) + list(extracted_path.glob("*.json")):
        if f.suffix == '.toon':
            data = load_toon(f)
        else:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
        extracted_db[data["paper_id"]] = data
    
    # Run repair pipeline
    success = repair_pipeline(sys.argv[1], extracted_db)
    
    sys.exit(0 if success else 1)
