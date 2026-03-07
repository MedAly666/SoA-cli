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


def find_optimal_clusters(vectors, min_k=2, max_k=10):
    """
    Find optimal number of clusters using silhouette analysis.
    
    Args:
        vectors: Embedding vectors (n_samples x n_features)
        min_k: Minimum number of clusters to try
        max_k: Maximum number of clusters to try
        
    Returns:
        Tuple of (optimal_k, silhouette_score, all_scores)
    """
    n_samples = len(vectors)
    
    # Adjust max_k to not exceed n_samples - 1
    max_k = min(max_k, n_samples - 1)
    
    if n_samples < min_k:
        print(f"  ⚠️  Too few papers ({n_samples}) for clustering, treating as single cluster")
        return 1, 0.0, {}
    
    print(f"  [Silhouette Analysis] Testing k from {min_k} to {max_k}")
    
    scores = {}
    best_k = min_k
    best_score = -1.0
    
    for k in range(min_k, max_k + 1):
        # Perform clustering
        clustering = AgglomerativeClustering(
            n_clusters=k,
            metric="cosine",
            linkage="average"
        )
        labels = clustering.fit_predict(vectors)
        
        # Calculate silhouette score
        score = silhouette_score(vectors, labels, metric='cosine')
        scores[k] = score
        
        print(f"    k={k}: silhouette={score:.4f}")
        
        if score > best_score:
            best_score = score
            best_k = k
    
    print(f"  ✓ Optimal k={best_k} with silhouette score={best_score:.4f}")
    
    return best_k, best_score, scores


def run_similarity_clustering(n_clusters=None, output_file="artifacts/clusters/preclusters.json"):
    """
    Perform agglomerative clustering on paper vectors.
    
    This is MATHEMATICAL clustering - the LLM will only interpret these clusters,
    not create them from scratch.
    
    Args:
        n_clusters: Number of clusters to create. If None, auto-detect optimal k.
        output_file: Where to save the cluster assignments
        
    Returns:
        Dictionary mapping cluster IDs to paper IDs
    """
    print(f"[+] Loading vector database")
    index = faiss.read_index("artifacts/vector_db/index.faiss")
    
    # Load JSON metadata
    with open("artifacts/vector_db/meta.json", "r", encoding='utf-8') as f:
        meta = json.load(f)
    
    n_papers = len(meta)
    print(f"[+] Found {n_papers} papers")
    
    # Handle edge case: too few papers for clustering
    if n_papers < 3:
        print(f"  ⚠️  Warning: Only {n_papers} paper(s) - treating as single cluster")
        clusters = {"C0": [paper["paper_id"] for paper in meta]}
        
        # Save to disk
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        if not output_file.endswith('.json'):
            output_file = output_file + '.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(clusters, f, indent=2)
        
        print(f"[✓] Created 1 cluster with {n_papers} paper(s)")
        print(f"[✓] Saved to {output_file}")
        return clusters
    
    print(f"[+] Reconstructing vectors from FAISS index")
    vectors = np.zeros((index.ntotal, index.d), dtype='float32')
    for i in range(index.ntotal):
        vectors[i] = index.reconstruct(i)
    
    # Auto-detect optimal k if not specified
    if n_clusters is None:
        print(f"[+] Auto-detecting optimal number of clusters...")
        n_clusters, silhouette, all_scores = find_optimal_clusters(
            vectors,
            min_k=2,
            max_k=min(10, n_papers - 1)
        )
    else:
        # Manual override - still show silhouette score
        print(f"[+] Using manually specified n_clusters={n_clusters}")
        silhouette = None
    
    print(f"[+] Running agglomerative clustering (n_clusters={n_clusters})")
    clustering = AgglomerativeClustering(
        n_clusters=n_clusters,
        metric="cosine",
        linkage="average"
    )
    
    labels = clustering.fit_predict(vectors)
    
    # Calculate silhouette score if not already done
    if silhouette is None and n_clusters > 1:
        silhouette = silhouette_score(vectors, labels, metric='cosine')
        print(f"  Silhouette score: {silhouette:.4f}")
    
    # Group papers by cluster
    clusters = {}
    for label, paper in zip(labels, meta):
        cluster_id = f"C{label}"
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(paper["paper_id"])
    
    # Save to disk
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    # Save as JSON
    if not output_file.endswith('.json'):
        output_file = output_file + '.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(clusters, f, indent=2)
    
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
    
    n = None  # Auto-detect by default
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.lower() == 'auto':
            n = None  # Explicit auto-detect
        else:
            n = int(arg)
    
    clusters = run_similarity_clustering(n_clusters=n)
    summary = get_cluster_summary(clusters)
    
    print("\n[Summary]")
    print(json.dumps(summary, indent=2))
