Below is a **production-grade CLI multi-agent architecture**, designed to work **on top of Qwen (CLI / local / API)**, that will **read, extract, reason, cross-compare, and finally write a defensible State of the Art (SoA)** for a thesis or paper.

---

## 1. High-Level Principles (important)

Before architecture, align on **non-negotiables**:

1. **No single agent writes the SoA**

   * Writing is the *last* step.
   * Most LLM failures come from skipping synthesis.

2. **Paper reading ≠ summarization**

   * We extract **models, assumptions, datasets, metrics, limitations, gaps**.

3. **Cross-paper reasoning must be explicit**

   * We force agents to compare papers, not just stack summaries.

4. **Everything is traceable**

   * Every paragraph in the SoA must map back to paper IDs.

---

## 2. Overall Architecture (CLI-First)

```
soa-cli/
├── papers/
│   ├── P01.pdf
│   ├── P02.pdf
│   └── ...
├── artifacts/
│   ├── extracted/
│   ├── summaries/
│   ├── comparisons/
│   ├── clusters/
│   └── soa_draft/
├── agents/
│   ├── reader_agent.py
│   ├── extractor_agent.py
│   ├── critic_agent.py
│   ├── cluster_agent.py
│   ├── synthesis_agent.py
│   └── writer_agent.py
├── memory/
│   ├── vector_db/
│   └── structured_db.json
├── orchestrator.py
└── qwen.sh
```

Everything runs from **CLI**, no UI dependency.

---

## 3. Agent Roles (Very Important)

### 1️⃣ Reader Agent (PDF → Clean Text)

**Responsibility**

* Convert PDF → structured text
* Remove references section (handled later)
* Preserve equations, tables, section headers

**Input**

* PDF file

**Output**

```json
{
  "paper_id": "P12",
  "sections": {
    "abstract": "...",
    "introduction": "...",
    "methodology": "...",
    "results": "...",
    "limitations": "..."
  }
}
```

**Notes**

* Use `pdftotext + heuristics`
* No LLM reasoning here → deterministic

---

### 2️⃣ Extractor Agent (Core Intelligence)

**Responsibility**
Extract **structured scientific knowledge**, not prose.

**Prompt style (Qwen)**

> Extract factual, verifiable information. Do not summarize.

**Output schema**

```json
{
  "paper_id": "P12",
  "problem_definition": "...",
  "proposed_model": "...",
  "mathematical_formulation": true,
  "prediction_method": "LSTM / GNN / Poisson / none",
  "optimization_method": "MIP / heuristic / RL / none",
  "data_used": "real EMS data / synthetic",
  "metrics": ["response time", "coverage"],
  "assumptions": ["static demand", "perfect compliance"],
  "limitations": ["no relocation cost", "offline evaluation"],
  "claimed_contribution": "..."
}
```

This agent runs **43 times (parallel)**.

---

### 3️⃣ Critic Agent (Paper Quality Filter)

**Responsibility**

* Identify **overclaiming**
* Spot missing baselines
* Flag weak evaluations

**Output**

```json
{
  "paper_id": "P12",
  "methodological_strength": "medium",
  "main_weaknesses": [
    "no real-time deployment",
    "limited city scale"
  ],
  "reliability_score": 0.63
}
```

This is crucial for **academic credibility**.

---

### 4️⃣ Cluster Agent (State-of-the-Art Backbone)

**Responsibility**
Group papers by **approach**, not by year.

**Typical clusters**

* Demand prediction only
* Optimization only
* Sequential (predict → optimize)
* End-to-end learning
* Static vs dynamic relocation

**Output**

```json
{
  "cluster_id": "C3",
  "theme": "Predict-then-optimize EMS relocation",
  "papers": ["P03", "P12", "P27"],
  "common_assumptions": [...],
  "shared_limitations": [...]
}
```

This agent **defines your SoA structure**.

---

### 5️⃣ Synthesis Agent (Cross-Paper Reasoning)

This is where normal LLMs usually fail — so we isolate it.

**Responsibility**

* Compare clusters
* Identify **research gaps**
* Track **evolution of methods**
* Explicitly state trade-offs

**Output**

```json
{
  "theme": "Predict-then-optimize",
  "what_works": "...",
  "what_fails": "...",
  "open_problems": [
    "joint learning of prediction and optimization",
    "real-time relocation under uncertainty"
  ],
  "conflicting_results": [...]
}
```

---

### 6️⃣ Writer Agent (Final SoA Writer)

**Responsibility**

* Convert structured synthesis → academic prose
* Cite papers by ID
* Maintain logical flow

**Constraints**

* Cannot invent facts
* Can only use provided artifacts

**Input**

* Cluster outputs
* Synthesis outputs

**Output**

```latex
\section{Predict-then-Optimize Approaches}
Several studies \cite{P03,P12,P27} adopt...
```

---

## 4. Orchestrator (Brain of the System)

**Key features**

* Dependency-aware execution
* Retry on hallucination
* Parallelism
* Deterministic artifacts

**Execution order**

```text
PDFs
 → Reader
 → Extractor + Critic (parallel)
 → Vector DB indexing
 → Cluster Agent
 → Synthesis Agent
 → Writer Agent
```

---

## 5. Memory Design (This Matters)

### 🔹 Structured Memory (JSON)

Used for **fact grounding**

### 🔹 Vector Memory

Used for:

* Cross-paper similarity
* Cluster detection
* Gap discovery

**DO NOT let the writer agent query PDFs directly**

---

## 6. Qwen CLI Integration

Example invocation pattern:

```bash
qwen run \
  --model qwen3.5-32b \
  --system agents/extractor.system.txt \
  --input artifacts/reader/P12.json \
  --output artifacts/extracted/P12.json
```

Each agent has:

* Fixed system prompt
* Strict output schema
* Temperature ≤ 0.3

---

## 7. Output You Will Get

✔ A **full State of the Art**
✔ Clustered, logical, thesis-ready
✔ Explicit research gaps
✔ Zero hallucinated citations
✔ Reusable for journal version

---

## 8. Hard Truth (Coach Mode)

If you try to:

* Use **one agent**
* Or skip clustering
* Or let the writer “be creative”

👉 Your SoA will be **academically weak**, and reviewers will smell it instantly.

This architecture is **the minimum viable serious system**.

---
