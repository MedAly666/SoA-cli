Below is a **clean, minimal, production-grade extension** that adds a **Vector DB + similarity-based clustering**, while keeping your existing agents intact.

I’ll show you:

1. **Where vectors fit in the pipeline**
2. **Embedding strategy (what to embed, what NOT)**
3. **Vector DB schema**
4. **Python code (drop-in)**
5. **How clustering now works (hybrid: math + LLM)**

No fluff.

---

# 1️⃣ Updated Pipeline (Important Change)

### Before

```
Extractor → Cluster Agent
```

### After (Correct)

```
Extractor
 → Embedding
 → Vector DB
 → Similarity Clustering (math)
 → Cluster Agent (label + reasoning)
```

👉 **LLM no longer decides clusters from scratch**
👉 It **explains and names clusters discovered by similarity**

---

# 2️⃣ What We Embed (Critical Design Choice)

**DO NOT embed full papers**
**DO NOT embed abstracts**

Embed **methodological fingerprints** only.

### Embedding Text Template (per paper)

```text
Research problem: {research_problem}
Prediction method: {prediction_component.method}
Optimization method: {optimization_component.method}
Decision variables: {decision_variables}
Objective: {optimization_component.objective_function}
Assumptions: {assumptions}
Limitations: {limitations_explicit}
```

This gives **method similarity**, not topic similarity.

---

# 3️⃣ Vector DB Choice

For CLI + local:

✅ **FAISS** (fast, simple, offline)

```bash
pip install faiss-cpu sentence-transformers
```

---

# 4️⃣ Directory Additions

```text
soa-cli/
├── vector_db/
│   ├── index.faiss
│   ├── meta.json
```

---

# 5️⃣ Embedding + Indexing Code

### `vectorize.py`

```python
from sentence_transformers import SentenceTransformer
import faiss
import json
import numpy as np
from pathlib import Path

MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def build_embedding_text(paper):
    return f"""
    Research problem: {paper['research_problem']}
    Prediction method: {paper['prediction_component']['method']}
    Optimization method: {paper['optimization_component']['method']}
    Decision variables: {paper['decision_variables']}
    Objective: {paper['optimization_component']['objective_function']}
    Assumptions: {', '.join(paper['assumptions'])}
    Limitations: {', '.join(paper['limitations_explicit'])}
    """

def build_vector_db(extracted_files):
    model = SentenceTransformer(MODEL)
    texts, meta = [], []

    for f in extracted_files:
        paper = json.load(open(f))
        texts.append(build_embedding_text(paper))
        meta.append({"paper_id": paper["paper_id"]})

    embeddings = model.encode(texts, normalize_embeddings=True)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(np.array(embeddings))

    Path("vector_db").mkdir(exist_ok=True)

    faiss.write_index(index, "vector_db/index.faiss")
    json.dump(meta, open("vector_db/meta.json", "w"), indent=2)
```

---

# 6️⃣ Similarity-Based Clustering (Mathematical)

We do **agglomerative clustering on vectors**, not LLM guessing.

### `similarity_cluster.py`

```python
import faiss
import json
import numpy as np
from sklearn.cluster import AgglomerativeClustering

def run_similarity_clustering(n_clusters=6):
    index = faiss.read_index("vector_db/index.faiss")
    meta = json.load(open("vector_db/meta.json"))

    vectors = index.reconstruct_n(0, index.ntotal)

    clustering = AgglomerativeClustering(
        n_clusters=n_clusters,
        metric="cosine",
        linkage="average"
    )

    labels = clustering.fit_predict(vectors)

    clusters = {}
    for label, paper in zip(labels, meta):
        clusters.setdefault(f"C{label}", []).append(paper["paper_id"])

    return clusters
```

This gives **raw clusters** like:

```json
{
  "C0": ["P01", "P12", "P19"],
  "C1": ["P03", "P27"]
}
```

---

# 7️⃣ Feeding Clusters to the LLM (Correct Way)

Now the **Cluster Agent** does NOT decide grouping.

It receives:

```json
{
  "precomputed_clusters": {
    "C0": ["P01", "P12"],
    "C1": ["P03", "P27"]
  },
  "paper_metadata": [...]
}
```

### Modified Cluster Agent Prompt (IMPORTANT CHANGE)

```text
You are a research synthesis agent.

You are given precomputed similarity-based clusters.

Your task:
- Interpret and name each cluster
- Explain why papers belong together
- Identify shared assumptions and limitations

Rules:
- Do NOT move papers between clusters
- Do NOT create new clusters
- Focus on methodological similarity
```

👉 This makes clustering **explainable and defensible**.

---

# 8️⃣ Orchestrator Integration

### Add to `orchestrator.py`

```python
from vectorize import build_vector_db
from similarity_cluster import run_similarity_clustering
```

### After extraction step:

```python
build_vector_db(extracted)

raw_clusters = run_similarity_clustering(n_clusters=6)

with open("artifacts/clusters/preclusters.json", "w") as f:
    json.dump(raw_clusters, f, indent=2)
```

Then pass `preclusters.json` into the Cluster Agent input.

---

# 9️⃣ Why This Is Academically Strong

✔ Clusters are **data-driven**
✔ LLM only **interprets**, not invents
✔ You can **justify clusters mathematically** in defense
✔ Reviewers cannot say “arbitrary grouping”

You can literally write:

> “We first clustered works using cosine similarity over methodological embeddings, then interpreted clusters qualitatively.”

That sentence alone signals **research maturity**.

---

# 🔥 Coach-Level Advice (Read This)

If your supervisor asks *“How did you group papers?”*
and you answer *“by similarity-based clustering on extracted methodological features”*
—you instantly sound like a **serious researcher**, not a ChatGPT user.

---

