"""
Vector embedding and indexing module for methodological similarity clustering.
Built according to vectordb.md specifications.
"""

from sentence_transformers import SentenceTransformer
import faiss
import json
import numpy as np
from pathlib import Path

MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def build_embedding_text(paper):
    """
    Build methodological fingerprint for embedding.
    DO NOT embed full papers - only method signatures.
    """
    prediction_method = paper.get('prediction_component', {}).get('method', 'not specified')
    optimization_method = paper.get('optimization_component', {}).get('method', 'not specified')
    objective = paper.get('optimization_component', {}).get('objective_function', 'not specified')
    decision_vars = paper.get('decision_variables', 'not specified')
    assumptions = ', '.join(paper.get('assumptions', []))
    limitations = ', '.join(paper.get('limitations_explicit', []))
    research_problem = paper.get('research_problem', 'not specified')
    
    return f"""
Research problem: {research_problem}
Prediction method: {prediction_method}
Optimization method: {optimization_method}
Decision variables: {decision_vars}
Objective: {objective}
Assumptions: {assumptions}
Limitations: {limitations}
"""


def build_vector_db(extracted_files):
    """
    Build FAISS vector database from extracted paper facts.
    
    Args:
        extracted_files: List of paths to extracted JSON files
        
    Returns:
        None (writes to disk: vector_db/index.faiss and vector_db/meta.json)
    """
    print(f"[+] Loading embedding model: {MODEL}")
    model = SentenceTransformer(MODEL)
    
    texts, meta = [], []
    
    print(f"[+] Processing {len(extracted_files)} papers")
    for f in extracted_files:
        try:
            # Convert to Path object if it's a string
            f_path = Path(f) if isinstance(f, str) else f
            
            # Load JSON files only
            if f_path.suffix == '.json':
                with open(f_path, 'r', encoding='utf-8') as file:
                    paper = json.load(file)
            
            texts.append(build_embedding_text(paper))
            meta.append({"paper_id": paper["paper_id"]})
        except Exception as e:
            print(f"[!] Error processing {f}: {e}")
            continue
    
    if not texts:
        print("[!] No papers to encode after processing")
        print("[!] Check if papers passed thematic filter or if extraction format is valid")
        raise ValueError("No papers to encode - vector DB requires at least 1 paper")
    
    print(f"[+] Encoding {len(texts)} methodological fingerprints")
    embeddings = model.encode(texts, normalize_embeddings=True)
    
    # Build FAISS index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product for normalized vectors = cosine similarity
    index.add(np.array(embeddings).astype('float32'))
    
    # Save to disk
    Path("vector_db").mkdir(exist_ok=True)
    
    faiss.write_index(index, "vector_db/index.faiss")
    with open("vector_db/meta.json", 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    
    print(f"[✓] Vector DB built: {index.ntotal} papers indexed")
    print(f"[✓] Saved to vector_db/index.faiss")


def get_embedder():
    """Get the sentence transformer model for encoding queries."""
    return SentenceTransformer(MODEL)


def load_vector_db():
    """Load the FAISS index and metadata from disk."""
    index = faiss.read_index("vector_db/index.faiss")
    
    # Load JSON metadata
    with open("vector_db/meta.json", "r", encoding='utf-8') as f:
        meta = json.load(f)
    
    return index, meta


if __name__ == "__main__":
    # Simple test
    import sys
    if len(sys.argv) > 1:
        extracted_path = Path(sys.argv[1])
        # Load JSON files only
        files = list(extracted_path.glob("*.json"))
        build_vector_db(files)
    else:
        print("Usage: python vectorize.py <path_to_extracted_folder>")
