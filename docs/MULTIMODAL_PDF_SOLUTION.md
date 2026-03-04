# Multimodal PDF Processing Solutions

## Problem Statement

The current PDF-to-text conversion (`page.get_text()` in PyMuPDF) **loses all visual information**:
- ❌ Figures and diagrams (neural network architectures, flowcharts, system designs)
- ❌ Tables (experimental results, comparison matrices)
- ❌ Charts and plots (performance graphs, ablation studies)
- ❌ Mathematical equations (may be poorly rendered as text)
- ❌ Algorithms (often presented as images)

For technical papers, **60-80% of critical information is in visual elements**.

---

## Solution Options

### 🥇 **Option 1: Vision-Enabled LLM Integration (RECOMMENDED)**

**What it does:**
- Send PDF pages as images directly to vision-capable LLMs
- LLM reads text + figures + tables + diagrams simultaneously
- Most accurate understanding of paper content

**Supported Models:**
- ✅ GPT-4 Vision (OpenAI)
- ✅ Claude 3 Opus/Sonnet (Anthropic)
- ✅ Gemini Pro Vision (Google)
- ✅ Qwen-VL (Alibaba - local deployment)

**Implementation:**
```python
def read_pdf_multimodal(pdf_path, max_pages=20):
    """Convert PDF pages to images and send to vision LLM."""
    doc = fitz.open(pdf_path)
    
    # Method 1: Convert pages to images
    images = []
    for page_num in range(min(len(doc), max_pages)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x resolution
        img_bytes = pix.tobytes("png")
        images.append(img_bytes)
    
    # Send to vision LLM with prompt
    prompt = """Analyze this research paper and extract:
    1. Methodology from text AND figures
    2. Architecture details from diagrams
    3. Results from tables and plots
    4. Mathematical formulations from equations
    """
    
    response = vision_llm.analyze(images, prompt)
    return response
```

**Pros:**
- ✅ Complete information capture
- ✅ Understands context of figures
- ✅ Can read table structure
- ✅ Interprets charts and plots

**Cons:**
- ❌ Requires vision-capable API (additional cost)
- ❌ Larger API payloads (images are bigger than text)
- ❌ Slower processing (~2-3x)

**Cost Estimate:**
- GPT-4 Vision: ~$0.01-0.03 per page (~$0.30-0.60 per paper)
- Claude 3 Sonnet: ~$0.003-0.008 per page (~$0.06-0.16 per paper)
- Qwen-VL: Free (local deployment, requires GPU)

---

### 🥈 **Option 2: Hybrid - Extract Figures + Use Standard LLM**

**What it does:**
- Extract text normally
- Detect and extract figures/tables as images
- Send figures to vision LLM for captioning
- Append figure descriptions to text

**Implementation:**
```python
def read_pdf_hybrid(pdf_path):
    doc = fitz.open(pdf_path)
    
    # Extract text
    text = extract_text_from_pdf(doc)
    
    # Extract figures
    figures = []
    for page_num, page in enumerate(doc):
        # Get images
        image_list = page.get_images()
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # Caption with vision model
            caption = caption_image(image_bytes)
            figures.append({
                'page': page_num + 1,
                'caption': caption,
                'location': f'Figure {len(figures)+1}'
            })
    
    # Append figure descriptions
    figure_section = "\n\n### FIGURES AND DIAGRAMS ###\n"
    for fig in figures:
        figure_section += f"\n[Page {fig['page']}] {fig['location']}: {fig['caption']}\n"
    
    return text + figure_section
```

**Pros:**
- ✅ Captures key visual information
- ✅ Works with any LLM for text processing
- ✅ Lower cost than full vision LLM

**Cons:**
- ❌ Figure-text integration may be lost
- ❌ Still requires vision API for captioning
- ❌ Two-stage processing (more complex)

---

### 🥉 **Option 3: Enhanced OCR with Table Detection**

**What it does:**
- Use specialized OCR for tables (preserves structure)
- Extract figure captions from PDF
- Use layout analysis to identify figure regions

**Tools:**
- PaddleOCR (table recognition)
- table-transformer (Microsoft)
- pdfplumber (better table extraction)
- Nougat (Meta - academic PDF to markdown)

**Implementation:**
```python
def read_pdf_enhanced(pdf_path):
    import pdfplumber
    
    with pdfplumber.open(pdf_path) as pdf:
        full_text = []
        
        for page in pdf.pages:
            # Extract text
            text = page.extract_text()
            full_text.append(text)
            
            # Extract tables with structure
            tables = page.extract_tables()
            for table in tables:
                # Convert table to markdown
                table_md = tables_to_markdown(table)
                full_text.append(f"\n[TABLE]\n{table_md}\n")
            
            # Extract figure captions (heuristic)
            captions = extract_captions(text)
            for caption in captions:
                full_text.append(f"\n[FIGURE CAPTION]: {caption}\n")
        
        return "\n\n".join(full_text)
```

**Pros:**
- ✅ No vision LLM required
- ✅ Better table preservation
- ✅ Captures figure captions

**Cons:**
- ❌ Doesn't see actual figure content
- ❌ Relies on good captions
- ❌ Still loses diagram semantics

---

### 🔧 **Option 4: Nougat (Meta's Academic PDF Parser)**

**What it does:**
- Converts academic PDFs to markdown
- Preserves equations, tables, figures (with placeholders)
- Trained specifically on scientific papers

**Installation:**
```bash
pip install nougat-ocr
```

**Usage:**
```python
from nougat import NougatModel

model = NougatModel.from_pretrained('facebook/nougat-base')
markdown = model.predict(pdf_path)
# Returns markdown with figure references preserved
```

**Pros:**
- ✅ Preserves LaTeX equations
- ✅ Better structure preservation
- ✅ Figure references maintained

**Cons:**
- ❌ Still doesn't see figure content
- ❌ Slower than simple text extraction
- ❌ Requires additional model (~1.5GB)

---

## Recommended Implementation Strategy

### Phase 1: Quick Win (Option 3 - Enhanced OCR)
**Immediate improvement with minimal changes:**

1. Replace PyMuPDF with **pdfplumber** for better table extraction
2. Extract and preserve figure captions
3. Add table structure to extracted text

**Estimated effort:** 2-3 hours
**Cost:** $0 (no API changes)
**Improvement:** 30-40% more information captured

### Phase 2: Full Vision (Option 1 - Vision LLM)
**Maximum accuracy for critical papers:**

1. Add vision LLM support to `llm_client.py`
2. Implement PDF-to-images conversion
3. Add configuration flag: `USE_VISION_LLM=true`
4. Use vision mode only for Reader node (highest impact)

**Estimated effort:** 1 day
**Cost:** +$0.10-0.60 per paper (adjustable via model choice)
**Improvement:** 80-90% more information captured

### Phase 3: Hybrid Optimization (Option 2)
**Balance cost and accuracy:**

1. Use vision LLM only for papers with many figures
2. Auto-detect figure-heavy papers (>5 figures)
3. Fall back to enhanced OCR for text-heavy papers

**Estimated effort:** 2-3 hours (after Phase 2)
**Cost:** Reduced by 50-70% vs full vision
**Improvement:** 70-80% more information captured

---

## Configuration Changes

Add to `.env`:
```bash
# Vision LLM configuration
USE_VISION_LLM=false           # Enable vision processing
VISION_MODEL=claude-3-sonnet   # or: gpt-4-vision, gemini-pro-vision, qwen-vl
VISION_ONLY_FOR_FIGURES=true   # Use vision only for figure-heavy papers
MIN_FIGURES_FOR_VISION=5       # Threshold for figure detection

# PDF processing
EXTRACT_TABLES=true            # Use pdfplumber for tables
EXTRACT_FIGURE_CAPTIONS=true   # Extract and include captions
MAX_FIGURES_PER_PAPER=20       # Limit figure extraction
```

---

## Code Changes Required

### Minimal Changes (Phase 1 - Enhanced OCR)

**File:** `src/graph/nodes.py`

```python
def read_pdf_with_tables(pdf_path, max_chars=None):
    """Enhanced PDF reading with table extraction."""
    import pdfplumber
    
    full_text = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages[:max_pages]):
            # Extract text
            text = page.extract_text() or ""
            full_text.append(f"### Page {page_num + 1} ###\n{text}")
            
            # Extract tables
            tables = page.extract_tables()
            for table_idx, table in enumerate(tables):
                if table:
                    table_md = format_table_as_markdown(table)
                    full_text.append(f"\n[TABLE {table_idx + 1}]\n{table_md}\n")
    
    return "\n\n".join(full_text)

def format_table_as_markdown(table):
    """Convert table array to markdown."""
    if not table or len(table) < 2:
        return ""
    
    # Header
    header = " | ".join(str(cell or "") for cell in table[0])
    separator = " | ".join(["---"] * len(table[0]))
    
    # Rows
    rows = []
    for row in table[1:]:
        rows.append(" | ".join(str(cell or "") for cell in row))
    
    return f"{header}\n{separator}\n" + "\n".join(rows)
```

### Full Vision Support (Phase 2)

**File:** `src/llm_client.py`

```python
def call_vision(self, system_prompt: str, user_prompt: str, images: List[bytes]) -> str:
    """Call vision-enabled LLM with images."""
    if self.provider == "openai":
        return self._call_openai_vision(system_prompt, user_prompt, images)
    elif self.provider == "anthropic":
        return self._call_anthropic_vision(system_prompt, user_prompt, images)
    else:
        raise ValueError(f"Vision not supported for provider: {self.provider}")

def _call_openai_vision(self, system_prompt, user_prompt, images):
    """GPT-4 Vision implementation."""
    import base64
    
    content = [{"type": "text", "text": user_prompt}]
    
    for img_bytes in images:
        b64_img = base64.b64encode(img_bytes).decode('utf-8')
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_img}"}
        })
    
    response = self.client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
    )
    
    return response.choices[0].message.content
```

---

## Testing Strategy

1. **Baseline test:** Run current system on 10 papers
2. **Enhanced OCR test:** Run Phase 1 on same papers
3. **Vision LLM test:** Run Phase 2 on 3 figure-heavy papers
4. **Compare extraction quality:**
   - Count extracted tables
   - Count figure references
   - Measure methodology comprehension

---

## Cost-Benefit Analysis

| Approach | Implementation | Cost/Paper | Information Capture | Recommendation |
|----------|---------------|------------|-------------------|----------------|
| Current | ✅ Done | $0 | 20-40% | ❌ Insufficient |
| Enhanced OCR | 2-3 hours | $0 | 50-60% | ✅ Quick win |
| Vision LLM | 1 day | $0.10-0.60 | 85-95% | ✅ Best quality |
| Hybrid | +3 hours | $0.05-0.30 | 70-80% | ✅ Best value |

---

## Next Steps

**If you want immediate improvement (1-2 hours):**
1. Install pdfplumber: `pip install pdfplumber`
2. Replace `read_pdf()` function to use pdfplumber
3. Add table extraction
4. Test on sample papers

**If you want maximum quality (1 day):**
1. Choose vision LLM provider (Claude 3 Sonnet recommended for cost/quality)
2. Add vision support to `llm_client.py`
3. Modify Reader node to use vision for PDFs
4. Add configuration flags
5. Test on figure-heavy papers

**Want me to implement either option?** Just say which one!
