"""
Similarity-based clustering using FAISS vectors.
Mathematical clustering - LLM only interprets, not decides.
Built according to vectordb.md specifications.
"""

import faiss
import json
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from pathlib import Path


def run_similarity_clustering(n_clusters=6, output_file="artifacts/clusters/preclusters.json"):
    """
    Perform agglomerative clustering on paper vectors.
    
    This is MATHEMATICAL clustering - the LLM will only interpret these clusters,
    not create them from scratch.
    
    Args:
        n_clusters: Number of clusters to create
        output_file: Where to save the cluster assignments
        
    Returns:
        Dictionary mapping cluster IDs to paper IDs
    """
    print(f"[+] Loading vector database")
    index = faiss.read_index("vector_db/index.faiss")
    
    with open("vector_db/meta.json", "r", encoding='utf-8') as f:
        meta = json.load(f)
    
    print(f"[+] Reconstructing vectors from FAISS index")
    vectors = np.zeros((index.ntotal, index.d), dtype='float32')
    for i in range(index.ntotal):
        vectors[i] = index.reconstruct(i)
    
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
    with open(output_file, "w", encoding='utf-8') as f:
        json.dump(clusters, f, indent=2)
    
    print(f"[✓] Clustered {len(meta)} papers into {len(clusters)} clusters")
    for cid, papers in clusters.items():
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
