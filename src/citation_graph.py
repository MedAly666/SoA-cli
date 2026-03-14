"""Citation graph utilities for SoA-CLI.

Builds a directed graph over extracted papers using:
1) Explicit citation relationships (references/cited_works fields)
2) Thematic similarity edges from embedding cosine similarity
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


def _load_extracted_papers(extracted_dir: str | Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Load extracted paper JSON files and return papers + title->id map."""
    extracted_path = Path(extracted_dir)
    papers: list[dict[str, Any]] = []

    for json_file in sorted(extracted_path.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "error" not in data:
                paper_id = data.get("paper_id") or json_file.stem
                data["paper_id"] = paper_id
                papers.append(data)
        except Exception:
            continue

    title_to_id: dict[str, str] = {}
    for paper in papers:
        title = str(paper.get("title", "")).strip().lower()
        if title:
            title_to_id[title] = str(paper["paper_id"])

    return papers, title_to_id


def _resolve_reference_to_id(ref_item: Any, known_ids: set[str], title_to_id: dict[str, str]) -> str | None:
    """Resolve a reference item to a known paper_id when possible."""
    if isinstance(ref_item, str):
        candidate = ref_item.strip()
        if candidate in known_ids:
            return candidate
        title_match = title_to_id.get(candidate.lower())
        if title_match:
            return title_match
        return None

    if isinstance(ref_item, dict):
        candidate = str(ref_item.get("paper_id") or ref_item.get("id") or "").strip()
        if candidate in known_ids:
            return candidate

        title = str(ref_item.get("title") or "").strip().lower()
        if title and title in title_to_id:
            return title_to_id[title]

    return None


def _extract_embeddings(faiss_index: Any, embeddings: Any, n_items: int) -> np.ndarray | None:
    """Get embeddings matrix from provided argument or FAISS index."""
    if embeddings is not None:
        arr = np.asarray(embeddings, dtype=np.float32)
        if arr.ndim == 2 and arr.shape[0] >= n_items:
            return arr[:n_items]

    if faiss_index is None:
        return None

    try:
        vecs = [faiss_index.reconstruct(i) for i in range(n_items)]
        arr = np.asarray(vecs, dtype=np.float32)
        return arr
    except Exception:
        return None


def build_citation_graph(extracted_dir: str | Path, faiss_index: Any, embeddings: Any) -> dict[str, Any]:
    """Build directed citation/thematic graph from extracted artifacts.

    Returns:
        {
          "nodes": [{"id": "P01", "title": "...", "year": 2022}],
          "edges": [{"source": "P01", "target": "P03", "type": "citation", "weight": 1.0}]
        }
    """
    papers, title_to_id = _load_extracted_papers(extracted_dir)
    if not papers:
        return {"nodes": [], "edges": []}

    nodes: list[dict[str, Any]] = []
    paper_ids: list[str] = []
    for paper in papers:
        pid = str(paper.get("paper_id"))
        paper_ids.append(pid)
        nodes.append(
            {
                "id": pid,
                "title": str(paper.get("title", "")),
                "year": paper.get("year"),
            }
        )

    known_ids = set(paper_ids)
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()

    # Explicit citation edges
    for paper in papers:
        source = str(paper["paper_id"])
        refs: list[Any] = []

        raw_refs = paper.get("references")
        if isinstance(raw_refs, list):
            refs.extend(raw_refs)

        raw_cited = paper.get("cited_works")
        if isinstance(raw_cited, list):
            refs.extend(raw_cited)

        for ref in refs:
            target = _resolve_reference_to_id(ref, known_ids, title_to_id)
            if not target or target == source:
                continue

            edge_key = (source, target, "citation")
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "type": "citation",
                    "weight": 1.0,
                }
            )

    # Thematic edges based on cosine similarity
    emb = _extract_embeddings(faiss_index=faiss_index, embeddings=embeddings, n_items=len(paper_ids))
    if emb is not None and len(emb) == len(paper_ids):
        # Normalize to ensure cosine similarity from dot product
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        emb = emb / norms

        sim_matrix = emb @ emb.T
        threshold = 0.65

        for i, source in enumerate(paper_ids):
            for j, target in enumerate(paper_ids):
                if i == j:
                    continue
                score = float(sim_matrix[i, j])
                if score <= threshold:
                    continue

                edge_key = (source, target, "thematic")
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)
                edges.append(
                    {
                        "source": source,
                        "target": target,
                        "type": "thematic",
                        "weight": round(score, 4),
                    }
                )

    return {"nodes": nodes, "edges": edges}


def get_grounding_context(graph: dict[str, Any], paper_id: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Return top-k connected neighbors for a given paper id."""
    if not graph:
        return []

    nodes = graph.get("nodes", []) or []
    edges = graph.get("edges", []) or []
    if not nodes or not edges:
        return []

    node_map = {str(n.get("id")): n for n in nodes}
    if paper_id not in node_map:
        return []

    scores: dict[str, float] = {}
    edge_types: dict[str, set[str]] = {}

    for edge in edges:
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        if source != paper_id and target != paper_id:
            continue

        other = target if source == paper_id else source
        if other == paper_id or other not in node_map:
            continue

        weight = float(edge.get("weight", 0.0))
        scores[other] = scores.get(other, 0.0) + max(weight, 0.0)
        edge_types.setdefault(other, set()).add(str(edge.get("type", "unknown")))

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    context: list[dict[str, Any]] = []
    for neighbor_id, score in ranked:
        meta = node_map.get(neighbor_id, {})
        context.append(
            {
                "paper_id": neighbor_id,
                "title": meta.get("title", ""),
                "year": meta.get("year"),
                "connection_score": round(score, 4),
                "edge_types": sorted(edge_types.get(neighbor_id, set())),
            }
        )

    return context
