Below is a **practical, implementable hallucination-detection layer** that works **without human reading**, fits your **CLI multi-agent architecture**, and is **LLM-agnostic**.

No theory fluff. This is how you actually catch hallucinations.

---

# 🎯 What “Hallucination” Means *Here* (Be Precise)

In your pipeline, a hallucination is **any claim that violates one of these invariants**:

1. ❌ A claim not supported by **any extracted paper facts**
2. ❌ A citation to a **paper ID that doesn’t support the claim**
3. ❌ A method / assumption / limitation **never present in source data**
4. ❌ Cross-paper generalization based on **only one paper**
5. ❌ Logical contradiction between agents

We will detect **all five**.

---

# 🧠 Strategy Overview (Multi-Layer Defense)

We use **4 complementary detectors**:

```
Writer Output
 ├─ Detector 1: Claim–Evidence Grounding
 ├─ Detector 2: Citation Verification
 ├─ Detector 3: Fact Coverage Consistency
 └─ Detector 4: Cross-Agent Contradiction
```

No single detector is enough. Combined → robust.

---

# 1️⃣ Detector 1 — Claim–Evidence Grounding (Core)

### Idea

Every **sentence** in the SoA must be grounded in **≥1 extracted facts**.

### Step A — Split SoA into Atomic Claims

```python
import re

def split_into_claims(latex_text):
    sentences = re.split(r'(?<=[.!?])\s+', latex_text)
    return [s for s in sentences if len(s.strip()) > 20]
```

---

### Step B — Retrieve Supporting Evidence (Vector-Based)

We reuse the **same vector DB**, but now for **verification**.

```python
def retrieve_support(claim, index, meta, embedder, top_k=5):
    vec = embedder.encode([claim], normalize_embeddings=True)
    scores, ids = index.search(vec, top_k)

    return [
        meta[i]["paper_id"]
        for i, s in zip(ids[0], scores[0])
        if s > 0.45   # similarity threshold
    ]
```

---

### Step C — Flag Ungrounded Claims

```python
def detect_ungrounded_claims(claims):
    violations = []

    for c in claims:
        support = retrieve_support(c, index, meta, model)
        if len(support) == 0:
            violations.append({
                "claim": c,
                "issue": "no supporting papers"
            })

    return violations
```

✔ Catches **fabricated generalizations**
✔ Catches **LLM “common knowledge” leakage**

---

# 2️⃣ Detector 2 — Citation Verification (Brutally Effective)

### Rule

If a sentence cites `{P12, P19}`, then **those papers must support it**.

---

### Extract Citations

```python
def extract_citations(sentence):
    return re.findall(r'P\d+', sentence)
```

---

### Verify Citation Support

```python
def verify_citations(sentence, cited_papers, extracted_db):
    supported = False

    for pid in cited_papers:
        paper = extracted_db[pid]
        if any(
            kw.lower() in sentence.lower()
            for kw in (
                paper["claimed_contributions"]
                + paper["assumptions"]
                + paper["limitations_explicit"]
            )
        ):
            supported = True

    return supported
```

---

### Flag Citation Hallucinations

```python
def detect_bad_citations(claims, extracted_db):
    violations = []

    for c in claims:
        cited = extract_citations(c)
        if cited and not verify_citations(c, cited, extracted_db):
            violations.append({
                "claim": c,
                "issue": "citation does not support claim",
                "citations": cited
            })

    return violations
```

✔ Detects **fake citation usage**
✔ Detects **“citation laundering”**

---

# 3️⃣ Detector 3 — Fact Coverage Consistency

### Rule

The SoA **may not introduce new methods, assumptions, or datasets**.

---

### Build Allowed Vocabulary (From Extractor)

```python
def build_fact_vocabulary(extracted_papers):
    vocab = set()

    for p in extracted_papers:
        vocab.update(p["assumptions"])
        vocab.update(p["evaluation_metrics"])
        vocab.add(p["prediction_component"]["method"])
        vocab.add(p["optimization_component"]["method"])

    return {v.lower() for v in vocab if v}
```

---

### Scan SoA for Out-of-Vocabulary Concepts

```python
def detect_new_concepts(soa_text, vocab):
    tokens = set(re.findall(r'\b[a-zA-Z\-]{5,}\b', soa_text.lower()))
    return [t for t in tokens if t not in vocab]
```

✔ Catches **invented methods**
✔ Catches **imaginary assumptions**
✔ Catches **LLM “academic style” drift**

---

# 4️⃣ Detector 4 — Cross-Agent Contradiction Check

### Example

* Critic agent says *“no real-time evaluation”*
* Writer claims *“validated in real-time settings”*

---

### Contradiction Prompt (Mini-Verifier Agent)

This is the **only place** we allow another LLM call.

#### `verifier.system.txt`

```
You are a factual consistency checker.

You are given:
1) A claim
2) Extracted facts and critiques

Determine whether the claim contradicts the evidence.

Output:
- "consistent"
- "contradiction"
- "unsupported"
```

Run this **only on flagged claims** (cheap).

---

# 5️⃣ Unified Hallucination Report (Actionable)

```json
{
  "severity": "high",
  "total_claims": 214,
  "violations": {
    "ungrounded": 7,
    "bad_citations": 3,
    "new_concepts": 2,
    "contradictions": 1
  },
  "details": [...]
}
```

---

# 6️⃣ Pipeline Integration Point

Add **after Writer Agent**:

```
Writer → Hallucination Check → (PASS) → Final SoA
                           → (FAIL) → Rewrite with constraints
```

If violations > threshold:

* Automatically **re-run writer agent**
* Inject a **repair instruction**:

  > “Rewrite ONLY flagged sentences using provided evidence.”

---

# 🧨 Why This Actually Works (Not Marketing)

| Problem                | Typical Fix         | Your System            |
| ---------------------- | ------------------- | ---------------------- |
| Hallucinated claims    | “Lower temperature” | Evidence grounding     |
| Fake citations         | Manual checking     | Automatic verification |
| Made-up methods        | Reviewer rejection  | Vocabulary guard       |
| Logical contradictions | Missed              | Cross-agent checking   |

This is **reviewer-grade robustness**.

---
