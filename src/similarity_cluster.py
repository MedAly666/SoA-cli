"""
Similarity-based clustering using FAISS vectors.
Mathematical clustering - LLM only interprets, not decides.
Built according to vectordb.md specifications.
"""

import faiss
import json
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score
from pathlib import Path
from src.toon_utils import load_toon, dump_toon


def find_optimal_clusters(embeddings, min_k=2, max_k=10):
    """
    Find optimal number of clusters using silhouette score.
    
    Args:
        embeddings: numpy array of paper embeddings
        min_k: Minimum number of clusters to try
        max_k: Maximum number of clusters to try
        
    Returns:
        Tuple of (optimal_k, best_score, all_scores)
    """
    n_samples = len(embeddings)
    
    # Adjust max_k to not exceed n_samples - 1
    max_k = min(max_k, n_samples - 1)
    
    # Need at least 2 clusters and 2 samples
    if n_samples < 2 or max_k < min_k:
        print(f"  [!] Not enough samples ({n_samples}) for clustering")
        return 1, 0.0, {}
    
    scores = {}
    best_k = min_k
    best_score = -1.0
    
    print(f"  [+] Evaluating cluster counts from {min_k} to {max_k}...")
    
    for k in range(min_k, max_k + 1):
        try:
            # Perform clustering
            clustering = AgglomerativeClustering(
                n_clusters=k,
                metric="cosine",
                linkage="average"
            )
            labels = clustering.fit_predict(embeddings)
            
            # Calculate silhouette score
            score = silhouette_score(embeddings, labels, metric='cosine')
            scores[k] = score
            
            print(f"    k={k}: silhouette score = {score:.3f}")
            
            # Track best score
            if score > best_score:
                best_score = score
                best_k = k
                
        except Exception as e:
            print(f"    k={k}: failed ({e})")
            scores[k] = -1.0
    
    return best_k, best_score, scores


def run_similarity_clustering(n_clusters=None, output_file="artifacts/clusters/preclusters.json"):
    """
    Perform agglomerative clustering on paper vectors.
    
    This is MATHEMATICAL clustering - the LLM will only interpret these clusters,
    not create them from scratch.
    
    Args:
        n_clusters: Number of clusters to create. 
                   If None, automatically determines optimal number using silhouette score.
        output_file: Where to save the cluster assignments
        
    Returns:
        Dictionary mapping cluster IDs to paper IDs
    """
    print(f"[+] Loading vector database")
    index = faiss.read_index("vector_db/index.faiss")
    
    # Try .toon first, fallback to .json
    meta_file = Path("vector_db/meta.toon")
    if meta_file.exists():
        meta = load_toon(meta_file)
    else:
        with open("vector_db/meta.json", "r", encoding='utf-8') as f:
            meta = json.load(f)
    
    n_papers = len(meta)
    print(f"[+] Found {n_papers} papers in vector database")
    
    # Handle edge case: too few papers
    if n_papers < 3:
        print(f"  [!] Warning: Only {n_papers} paper(s) found. Clustering requires at least 3.")
        print(f"  [!] Treating all papers as a single cluster.")
        
        # Create a single cluster with all papers
        clusters = {"C0": [paper["paper_id"] for paper in meta]}
        
        # Save to disk
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        if output_file.endswith('.json'):
            output_file = output_file.replace('.json', '.toon')
        dump_toon(clusters, output_file)
        
        print(f"[✓] Created 1 cluster with {n_papers} paper(s)")
        print(f"[✓] Saved to {output_file}")
        
        return clusters
    
    print(f"[+] Reconstructing vectors from FAISS index")
    vectors = np.zeros((index.ntotal, index.d), dtype='float32')
    for i in range(index.ntotal):
        vectors[i] = index.reconstruct(i)
    
    # Determine optimal number of clusters
    if n_clusters is None:
        print(f"[+] Finding optimal number of clusters...")
        min_k = 2
        max_k = min(10, n_papers - 1)
        
        optimal_k, best_score, all_scores = find_optimal_clusters(vectors, min_k, max_k)
        
        print(f"\n  [✓] Optimal cluster count: {optimal_k} (silhouette score: {best_score:.3f})")
        n_clusters = optimal_k
    else:
        # User-specified cluster count
        if n_clusters > n_papers:
            print(f"  [!] Warning: Requested {n_clusters} clusters but only {n_papers} papers.")
            print(f"  [!] Reducing to {n_papers} clusters.")
            n_clusters = n_papers
        print(f"[+] Using user-specified cluster count: {n_clusters}")
    
    print(f"[+] Running agglomerative clustering (n_clusters={n_clusters})")
    clustering = AgglomerativeClustering(
        n_clusters=n_clusters,
        metric="cosine",
        linkage="average"
    )
    
    labels = clustering.fit_predict(vectors)
    
    # Group papers by cluster
    clusters = {}
    for label, paper in zip(labels, meta):
        cluster_id = f"C{label}"
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(paper["paper_id"])
    
    # Save to disk
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    # Change extension to .toon if it was .json
    if output_file.endswith('.json'):
        output_file = output_file.replace('.json', '.toon')
    dump_toon(clusters, output_file)
    
    print(f"[✓] Clustered {len(meta)} papers into {len(clusters)} clusters")
    for cid, papers in sorted(clusters.items()):
        print(f"    {cid}: {len(papers)} papers")
    
    print(f"[✓] Saved to {output_file}")
    
    return clusters


def get_cluster_summary(clusters):
    """Generate a summary of cluster sizes."""
    summary = {
        "total_clusters": len(clusters),
        "total_papers": sum(len(papers) for papers in clusters.values()),
        "cluster_sizes": {cid: len(papers) for cid, papers in clusters.items()}
    }
    return summary


if __name__ == "__main__":
    import sys
    
    n = 6  # Default number of clusters
    if len(sys.argv) > 1:
        n = int(sys.argv[1])
    
    clusters = run_similarity_clustering(n_clusters=n)
    summary = get_cluster_summary(clusters)
    
    print("\n[Summary]")
    print(json.dumps(summary, indent=2))
