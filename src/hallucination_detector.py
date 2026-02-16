"""
Multi-layer hallucination detection system.
Built according to hallucination.md specifications.

Detects:
1. Ungrounded claims (no supporting evidence)
2. Bad citations (cited papers don't support claim)
3. New concepts (out-of-vocabulary methods/assumptions)
4. Cross-agent contradictions
"""

import re
import json
import numpy as np
from pathlib import Path


def split_into_claims(latex_text):
    """Split LaTeX text into atomic claims (sentences)."""
    # Remove LaTeX commands for cleaner processing
    text = re.sub(r'\\cite\{[^}]+\}', '', latex_text)
    text = re.sub(r'\\[a-z]+\{[^}]*\}', '', text)
    text = re.sub(r'\\[a-z]+', '', text)
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Filter out very short sentences
    return [s.strip() for s in sentences if len(s.strip()) > 20]


def extract_citations(sentence):
    """Extract paper IDs from a sentence (e.g., P01, P12)."""
    return re.findall(r'\bP\d+\b', sentence)


# ========== DETECTOR 1: Claim-Evidence Grounding ==========

def retrieve_support(claim, index, meta, embedder, top_k=5, threshold=0.45):
    """
    Retrieve supporting papers for a claim using vector similarity.
    
    Args:
        claim: The claim to verify
        index: FAISS index
        meta: Paper metadata
        embedder: SentenceTransformer model
        top_k: Number of similar papers to retrieve
        threshold: Minimum similarity score
        
    Returns:
        List of supporting paper IDs
    """
    vec = embedder.encode([claim], normalize_embeddings=True).astype('float32')
    scores, ids = index.search(vec, top_k)
    
    return [
        meta[i]["paper_id"]
        for i, s in zip(ids[0], scores[0])
        if s > threshold
    ]


def detect_ungrounded_claims(claims, index, meta, embedder):
    """
    Detector 1: Find claims with no supporting evidence in the corpus.
    """
    violations = []
    
    print(f"[+] Detector 1: Checking {len(claims)} claims for evidence grounding")
    
    for c in claims:
        support = retrieve_support(c, index, meta, embedder)
        if len(support) == 0:
            violations.append({
                "claim": c,
                "issue": "no supporting papers",
                "detector": "claim_evidence_grounding"
            })
    
    print(f"    Found {len(violations)} ungrounded claims")
    return violations


# ========== DETECTOR 2: Citation Verification ==========

def verify_citations(sentence, cited_papers, extracted_db):
    """
    Check if cited papers actually support the claim.
    """
    supported = False
    
    for pid in cited_papers:
        if pid not in extracted_db:
            continue
            
        paper = extracted_db[pid]
        
        # Check if key terms from the sentence appear in paper's contributions/assumptions/limitations
        sentence_lower = sentence.lower()
        
        # Build searchable content from paper
        searchable = []
        searchable.extend(paper.get("claimed_contributions", []))
        searchable.extend(paper.get("assumptions", []))
        searchable.extend(paper.get("limitations_explicit", []))
        searchable.append(paper.get("research_problem", ""))
        searchable.append(paper.get("prediction_component", {}).get("method", ""))
        searchable.append(paper.get("optimization_component", {}).get("method", ""))
        
        # Check for keyword overlap
        for item in searchable:
            if item and len(str(item)) > 3:
                keywords = [w.lower() for w in str(item).split() if len(w) > 3]
                if any(kw in sentence_lower for kw in keywords[:5]):  # Check first 5 keywords
                    supported = True
                    break
        
        if supported:
            break
    
    return supported


def detect_bad_citations(claims, extracted_db):
    """
    Detector 2: Find claims where citations don't support the statement.
    """
    violations = []
    
    print(f"[+] Detector 2: Verifying citations")
    
    for c in claims:
        cited = extract_citations(c)
        if cited and not verify_citations(c, cited, extracted_db):
            violations.append({
                "claim": c,
                "issue": "citation does not support claim",
                "citations": cited,
                "detector": "citation_verification"
            })
    
    print(f"    Found {len(violations)} bad citations")
    return violations


# ========== DETECTOR 3: Fact Coverage Consistency ==========

def build_fact_vocabulary(extracted_papers):
    """
    Build allowed vocabulary from extracted papers.
    The SoA cannot introduce methods/assumptions not in the corpus.
    """
    vocab = set()
    
    for p in extracted_papers:
        # Add assumptions (handle strings and dicts)
        for a in p.get("assumptions", []):
            if isinstance(a, str):
                vocab.add(a.lower())
            elif isinstance(a, dict):
                # Extract text from dict values
                for v in a.values():
                    if isinstance(v, str):
                        vocab.add(v.lower())
        
        # Add metrics (handle strings and dicts)
        for m in p.get("evaluation_metrics", []):
            if isinstance(m, str):
                vocab.add(m.lower())
            elif isinstance(m, dict):
                # Extract text from dict values
                for v in m.values():
                    if isinstance(v, str):
                        vocab.add(v.lower())
        
        # Add methods
        pred = p.get("prediction_component", {})
        if pred and pred.get("method"):
            vocab.add(str(pred["method"]).lower())
        
        opt = p.get("optimization_component", {})
        if opt and opt.get("method"):
            vocab.add(str(opt["method"]).lower())
        
        # Add learning paradigm
        lp = p.get("learning_paradigm", "")
        if lp:
            vocab.add(lp.lower())
        
        # Add data types
        data = p.get("data", {})
        if data.get("type"):
            vocab.add(data["type"].lower())
    
    return vocab


def detect_new_concepts(soa_text, vocab):
    """
    Detector 3: Find technical terms in SoA that don't exist in corpus.
    """
    # Extract potential technical terms (5+ char words)
    tokens = set(re.findall(r'\b[a-zA-Z\-]{5,}\b', soa_text.lower()))
    
    # Remove common academic words
    common_words = {
        'paper', 'study', 'research', 'method', 'approach', 'model', 'system',
        'problem', 'solution', 'results', 'section', 'figure', 'table',
        'shows', 'demonstrated', 'proposed', 'using', 'based', 'literature',
        'state', 'however', 'therefore', 'furthermore', 'several', 'various'
    }
    tokens = tokens - common_words
    
    # Find out-of-vocabulary concepts
    new_concepts = [t for t in tokens if t not in vocab and len(t) > 6]
    
    return new_concepts


# ========== DETECTOR 4: Cross-Agent Contradiction Check ==========

def detect_contradictions(claim, extracted_db, critic_db):
    """
    Detector 4: Check if claim contradicts critic assessments.
    This is a simplified version - full implementation would use LLM verifier.
    """
    # Look for common contradiction patterns
    contradictions = []
    
    claim_lower = claim.lower()
    
    # Extract cited papers from claim
    cited = extract_citations(claim)
    
    for pid in cited:
        if pid not in critic_db:
            continue
        
        critic = critic_db[pid]
        
        # Check for contradictory statements
        if "real-time" in claim_lower or "real time" in claim_lower:
            if not critic.get("real_time_applicability", True):
                contradictions.append({
                    "claim": claim,
                    "issue": "contradiction with critic assessment",
                    "detail": f"{pid} marked as not real-time applicable",
                    "detector": "contradiction_check"
                })
        
        if "scalable" in claim_lower or "scalability" in claim_lower:
            if not critic.get("scalability_addressed", True):
                contradictions.append({
                    "claim": claim,
                    "issue": "contradiction with critic assessment",
                    "detail": f"{pid} scalability not addressed",
                    "detector": "contradiction_check"
                })
    
    return contradictions


# ========== UNIFIED HALLUCINATION CHECK ==========

def run_hallucination_checks(soa_text, extracted_db, critic_db=None):
    """
    Run all hallucination detectors on the State of the Art text.
    
    Args:
        soa_text: The generated SoA LaTeX text
        extracted_db: Dictionary of extracted paper data (paper_id -> data)
        critic_db: Dictionary of critic assessments (paper_id -> critique)
        
    Returns:
        Dictionary with violation report
    """
    print("\n" + "="*60)
    print("RUNNING HALLUCINATION DETECTION")
    print("="*60)
    
    # Load vector database for claim grounding
    try:
        import faiss
        from .vectorize import get_embedder
        
        index = faiss.read_index("vector_db/index.faiss")
        with open("vector_db/meta.json", "r") as f:
            meta = json.load(f)
        embedder = get_embedder()
    except Exception as e:
        print(f"[!] Warning: Could not load vector DB: {e}")
        index, meta, embedder = None, None, None
    
    # Split text into claims
    claims = split_into_claims(soa_text)
    print(f"[+] Extracted {len(claims)} claims from SoA")
    
    all_violations = []
    
    # Detector 1: Ungrounded claims
    if index and meta and embedder:
        violations_1 = detect_ungrounded_claims(claims, index, meta, embedder)
        all_violations.extend(violations_1)
    else:
        print("[!] Skipping Detector 1 (vector DB not available)")
    
    # Detector 2: Bad citations
    violations_2 = detect_bad_citations(claims, extracted_db)
    all_violations.extend(violations_2)
    
    # Detector 3: New concepts
    print(f"[+] Detector 3: Checking for out-of-vocabulary concepts")
    vocab = build_fact_vocabulary(list(extracted_db.values()))
    new_concepts = detect_new_concepts(soa_text, vocab)
    if new_concepts:
        print(f"    Found {len(new_concepts)} new concepts: {new_concepts[:10]}")
        all_violations.append({
            "issue": "new concepts not in corpus",
            "concepts": new_concepts,
            "detector": "fact_coverage"
        })
    else:
        print(f"    No new concepts found")
    
    # Detector 4: Contradictions (if critic data available)
    if critic_db:
        print(f"[+] Detector 4: Checking for contradictions")
        contradiction_count = 0
        for claim in claims:
            contras = detect_contradictions(claim, extracted_db, critic_db)
            all_violations.extend(contras)
            contradiction_count += len(contras)
        print(f"    Found {contradiction_count} contradictions")
    
    # Generate report
    report = {
        "severity": "high" if len(all_violations) > 5 else "medium" if len(all_violations) > 0 else "low",
        "total_claims": len(claims),
        "violations": {
            "ungrounded": len([v for v in all_violations if v.get("detector") == "claim_evidence_grounding"]),
            "bad_citations": len([v for v in all_violations if v.get("detector") == "citation_verification"]),
            "new_concepts": len([v for v in all_violations if v.get("detector") == "fact_coverage"]),
            "contradictions": len([v for v in all_violations if v.get("detector") == "contradiction_check"])
        },
        "total_violations": len(all_violations),
        "details": all_violations
    }
    
    print("\n" + "="*60)
    print(f"HALLUCINATION DETECTION RESULTS")
    print("="*60)
    print(f"Severity: {report['severity'].upper()}")
    print(f"Total claims: {report['total_claims']}")
    print(f"Total violations: {report['total_violations']}")
    print(f"  - Ungrounded claims: {report['violations']['ungrounded']}")
    print(f"  - Bad citations: {report['violations']['bad_citations']}")
    print(f"  - New concepts: {report['violations']['new_concepts']}")
    print(f"  - Contradictions: {report['violations']['contradictions']}")
    print("="*60 + "\n")
    
    return report


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python hallucination_detector.py <soa_file> <extracted_folder>")
        sys.exit(1)
    
    # Load SoA text
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        soa_text = f.read()
    
    # Load extracted papers
    extracted_path = Path(sys.argv[2])
    extracted_db = {}
    for f in extracted_path.glob("*.json"):
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)
            extracted_db[data["paper_id"]] = data
    
    # Run checks
    report = run_hallucination_checks(soa_text, extracted_db)
    
    # Save report
    with open("artifacts/soa/hallucination_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"[✓] Report saved to artifacts/soa/hallucination_report.json")
