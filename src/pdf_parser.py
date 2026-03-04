"""
Semantic PDF Parser - Extract structured content from academic PDFs.

This module parses PDFs into a semantic structure that preserves:
- Section hierarchy (Introduction, Methods, Results, etc.)
- Figures with captions and locations
- Tables with structure preserved
- Equations and algorithms
- Contextual relationships between elements

The output is a JSON structure that maintains document organization
and enables context-aware processing by downstream agents.
"""

import fitz  # PyMuPDF
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re
import os


def parse_semantic_pdf(pdf_path: str, extract_images: bool = True, max_chars: Optional[int] = None) -> dict:
    """
    Parse PDF into semantic structure with sections, figures, tables.
    
    Args:
        pdf_path: Path to the PDF file
        extract_images: Whether to extract and store image bytes
        max_chars: Maximum characters to extract (None = no limit)
        
    Returns:
        Dictionary with semantic structure:
        {
            "metadata": {...},
            "sections": [...],
            "figures_index": {...},
            "tables_index": {...}
        }
    """
    if max_chars is None:
        max_chars = int(os.getenv('MAX_PDF_CHARS', '50000'))
    
    doc = fitz.open(pdf_path)
    filename = Path(pdf_path).name
    
    print(f"  [Semantic Parser] Analyzing {filename}...")
    
    # Step 1: Extract metadata
    metadata = extract_metadata(doc, filename)
    print(f"    ✓ Metadata: {metadata['total_pages']} pages")
    
    # Step 2: Extract sections (with text content)
    sections = extract_sections_with_text(doc)
    print(f"    ✓ Sections: {len(sections)} detected")
    
    # Step 3: Extract figures with captions
    figures = extract_figures_with_captions(doc, extract_images=extract_images)
    if len(figures) == 0:
        print(f"    ℹ️  Note: No raster images found (figures may be vector graphics)")
    else:
        print(f"    ✓ Figures: {len(figures)} extracted")
    
    # Step 4: Extract tables
    tables = extract_tables_from_pdf(pdf_path)
    print(f"    ✓ Tables: {len(tables)} extracted")
    
    # Step 5: Build semantic structure
    semantic_pdf = build_semantic_structure(
        metadata=metadata,
        sections=sections,
        figures=figures,
        tables=tables,
        max_chars=max_chars
    )
    
    doc.close()
    
    return semantic_pdf


def extract_metadata(doc, filename: str) -> dict:
    """Extract basic metadata from PDF."""
    metadata = doc.metadata or {}
    
    return {
        'filename': filename,
        'title': metadata.get('title', filename.replace('.pdf', '')),
        'author': metadata.get('author', 'Unknown'),
        'total_pages': len(doc),
        'has_toc': len(doc.get_toc()) > 0
    }


def extract_sections_with_text(doc) -> List[dict]:
    """
    Extract section hierarchy with text content.
    Tries PDF outline first, then falls back to heuristic detection.
    """
    sections = []
    
    # Method 1: Use PDF outline/bookmarks (most reliable)
    outline = doc.get_toc()
    if outline:
        print("      Using PDF outline for sections")
        sections = extract_from_outline(doc, outline)
    
    # Method 2: Heuristic - detect headings by font size
    if not sections or len(sections) < 3:
        print("      Using heuristic section detection")
        sections = detect_sections_by_font(doc)
    
    return sections


def extract_from_outline(doc, outline: List[Tuple]) -> List[dict]:
    """Extract sections from PDF outline/table of contents."""
    sections = []
    
    for i, (level, title, page_num) in enumerate(outline):
        # Determine end page (start of next section or end of doc)
        if i + 1 < len(outline):
            end_page = outline[i + 1][2] - 1
        else:
            end_page = len(doc)
        
        # Extract text from this section's pages
        section_text = []
        for p in range(page_num - 1, min(end_page, len(doc))):
            if p >= 0:
                page = doc[p]
                text = page.get_text()
                if text.strip():
                    section_text.append(text)
        
        sections.append({
            'title': title.strip(),
            'level': level,
            'start_page': page_num,
            'end_page': end_page,
            'text': '\n\n'.join(section_text),
            'type': 'section'
        })
    
    return sections


def detect_sections_by_font(doc) -> List[dict]:
    """
    Detect section headings by analyzing font sizes and styles.
    Assumes headings have larger font size than body text.
    """
    sections = []
    current_section = None
    body_font_size = estimate_body_font_size(doc)
    
    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        page_text = []
        
        for block in blocks:
            if "lines" not in block:
                continue
                
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    font_size = span["size"]
                    
                    # Potential heading: larger than body + not too long
                    if font_size > body_font_size * 1.2 and len(text) < 100 and text:
                        # Save previous section
                        if current_section:
                            sections.append(current_section)
                        
                        # Start new section
                        current_section = {
                            'title': text,
                            'start_page': page_num + 1,
                            'font_size': font_size,
                            'text': '',
                            'type': 'heading'
                        }
                    
                    # Body text - add to current section
                    elif current_section and font_size <= body_font_size * 1.2:
                        page_text.append(text)
        
        # Add page text to current section
        if current_section and page_text:
            current_section['text'] += '\n'.join(page_text) + '\n\n'
    
    # Add last section
    if current_section:
        sections.append(current_section)
    
    return sections


def estimate_body_font_size(doc) -> float:
    """Estimate the most common font size (body text)."""
    font_sizes = []
    
    # Sample first 3 pages
    for page_num in range(min(3, len(doc))):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        font_sizes.append(span["size"])
    
    # Return median font size
    if font_sizes:
        font_sizes.sort()
        return font_sizes[len(font_sizes) // 2]
    return 10.0  # Default fallback


def extract_figures_with_captions(doc, extract_images: bool = True) -> List[dict]:
    """Extract figures with their captions and optional image data."""
    figures = []
    
    for page_num, page in enumerate(doc):
        # Get images on this page
        image_list = page.get_images()
        
        # Get text blocks (to find captions)
        text_blocks = page.get_text("blocks")
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            
            # Get actual bounding box(es) for this image on the page
            # An image can appear multiple times (e.g., in header/footer)
            try:
                image_rects = page.get_image_rects(xref)
                if not image_rects:
                    continue
                
                # Use the first/largest occurrence
                bbox = list(image_rects[0]) if image_rects else None
                if not bbox:
                    continue
                    
            except Exception as e:
                # Fallback: try get_image_bbox
                try:
                    bbox = list(page.get_image_bbox(xref))
                except:
                    continue
            
            # Skip very small images (likely icons/logos)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if width < 50 or height < 50:
                continue
            
            # Find caption near this image
            caption = find_caption_near_bbox(text_blocks, bbox)
            
            # Extract image data if requested
            image_bytes = None
            image_width = 0
            image_height = 0
            
            if extract_images:
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_width = base_image["width"]
                    image_height = base_image["height"]
                except:
                    pass  # Some images can't be extracted
            
            figure_id = f'page{page_num+1}_fig{img_index+1}'
            
            figures.append({
                'figure_id': figure_id,
                'page': page_num + 1,
                'bbox': bbox,
                'caption': caption,
                'image_bytes': image_bytes,
                'width': image_width,
                'height': image_height,
                'type': 'figure'
            })
    
    return figures


def find_caption_near_bbox(text_blocks: List, img_bbox: List, threshold: int = 100) -> Optional[str]:
    """
    Find text that looks like a figure caption near the image.
    Looks for text starting with 'Figure', 'Fig.', 'Fig', etc.
    """
    img_x0, img_y0, img_x1, img_y1 = img_bbox
    
    candidates = []
    
    for block in text_blocks:
        if len(block) < 5:
            continue
            
        x0, y0, x1, y1, text, *_ = block
        text = text.strip()
        
        # Calculate distance from image
        # Check below image (most common) or above
        vertical_distance = min(abs(y0 - img_y1), abs(img_y0 - y1))
        
        if vertical_distance < threshold:
            # Check if text looks like a caption
            if re.match(r'^(Figure|Fig\.?|TABLE|Table)\s+\d+', text, re.IGNORECASE):
                candidates.append((vertical_distance, text))
    
    # Return closest candidate
    if candidates:
        candidates.sort(key=lambda x: x[0])  # Sort by distance
        return candidates[0][1]
    
    return None


def extract_tables_from_pdf(pdf_path: str) -> List[dict]:
    """
    Extract tables with structure preserved using pdfplumber.
    Falls back to basic extraction if pdfplumber not available.
    """
    tables = []
    
    try:
        import pdfplumber
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_tables = page.extract_tables()
                
                if not page_tables:
                    continue
                
                for table_idx, table in enumerate(page_tables):
                    if not table or len(table) < 2:
                        continue
                    
                    # Clean table data
                    cleaned_table = []
                    for row in table:
                        cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                        cleaned_table.append(cleaned_row)
                    
                    table_id = f'page{page_num+1}_tab{table_idx+1}'
                    
                    tables.append({
                        'table_id': table_id,
                        'page': page_num + 1,
                        'data': {
                            'headers': cleaned_table[0] if cleaned_table else [],
                            'rows': cleaned_table[1:] if len(cleaned_table) > 1 else []
                        },
                        'type': 'table'
                    })
    
    except ImportError:
        print("      ⚠️  pdfplumber not installed - table extraction limited")
        print("         Install with: pip install pdfplumber")
    
    except Exception as e:
        print(f"      ⚠️  Table extraction error: {e}")
    
    return tables


def build_semantic_structure(
    metadata: dict,
    sections: List[dict],
    figures: List[dict],
    tables: List[dict],
    max_chars: int
) -> dict:
    """
    Build final semantic PDF structure with content organized by sections.
    Interleaves text, figures, and tables in document order.
    """
    semantic = {
        'metadata': metadata,
        'sections': [],
        'figures_index': {fig['figure_id']: fig for fig in figures},
        'tables_index': {tab['table_id']: tab for tab in tables},
        'total_chars': 0,
        'truncated': False
    }
    
    # Build sections with embedded figures and tables
    total_chars = 0
    
    for section in sections:
        if total_chars >= max_chars:
            semantic['truncated'] = True
            break
        
        section_obj = {
            'title': section['title'],
            'start_page': section.get('start_page', 1),
            'content': []
        }
        
        # Add section text
        section_text = section.get('text', '').strip()
        if section_text:
            # Truncate if needed
            remaining = max_chars - total_chars
            if len(section_text) > remaining:
                section_text = section_text[:remaining]
                semantic['truncated'] = True
            
            section_obj['content'].append({
                'type': 'text',
                'value': section_text
            })
            total_chars += len(section_text)
        
        # Add figures from this section's pages
        section_start = section.get('start_page', 1)
        section_end = section.get('end_page', section_start)
        
        for fig in figures:
            if section_start <= fig['page'] <= section_end:
                section_obj['content'].append({
                    'type': 'figure',
                    'figure_id': fig['figure_id'],
                    'page': fig['page'],
                    'caption': fig.get('caption', 'No caption')
                })
        
        # Add tables from this section's pages
        for tab in tables:
            if section_start <= tab['page'] <= section_end:
                section_obj['content'].append({
                    'type': 'table',
                    'table_id': tab['table_id'],
                    'page': tab['page']
                })
        
        semantic['sections'].append(section_obj)
    
    semantic['total_chars'] = total_chars
    
    return semantic


def semantic_pdf_to_text(semantic_pdf: dict, include_figures: bool = True, include_tables: bool = True) -> str:
    """
    Convert semantic PDF structure to formatted text for LLM processing.
    Maintains structure with clear markers for figures and tables.
    """
    text_parts = []
    
    # Add metadata header
    meta = semantic_pdf['metadata']
    text_parts.append(f"[PAPER: {meta['title']}]")
    text_parts.append(f"[PAGES: {meta['total_pages']}]")
    if semantic_pdf.get('truncated'):
        text_parts.append(f"[WARNING: Content truncated at {semantic_pdf['total_chars']:,} chars]")
    text_parts.append("")
    
    # Process each section
    for section in semantic_pdf['sections']:
        text_parts.append(f"\n{'='*80}")
        text_parts.append(f"## {section['title']}")
        text_parts.append(f"{'='*80}\n")
        
        for item in section['content']:
            if item['type'] == 'text':
                text_parts.append(item['value'])
                text_parts.append("")
            
            elif item['type'] == 'figure' and include_figures:
                fig = semantic_pdf['figures_index'].get(item['figure_id'], {})
                caption = fig.get('caption', 'No caption')
                description = fig.get('description', '')
                
                text_parts.append(f"\n[FIGURE: {item['figure_id']} (Page {item['page']})]")
                text_parts.append(f"Caption: {caption}")
                if description:
                    text_parts.append(f"Description: {description}")
                text_parts.append("")
            
            elif item['type'] == 'table' and include_tables:
                tab = semantic_pdf['tables_index'].get(item['table_id'], {})
                text_parts.append(f"\n[TABLE: {item['table_id']} (Page {item['page']})]")
                
                # Format table as markdown
                if 'data' in tab:
                    table_md = format_table_markdown(tab['data'])
                    text_parts.append(table_md)
                text_parts.append("")
    
    return "\n".join(text_parts)


def format_table_markdown(table_data: dict) -> str:
    """Convert table data to markdown format."""
    if not table_data or 'headers' not in table_data:
        return "[Empty table]"
    
    headers = table_data.get('headers', [])
    rows = table_data.get('rows', [])
    
    if not headers:
        return "[Table with no headers]"
    
    lines = []
    
    # Header row
    lines.append("| " + " | ".join(str(h) for h in headers) + " |")
    
    # Separator
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    
    # Data rows
    for row in rows:
        # Pad row if it's shorter than header
        padded_row = list(row) + [""] * (len(headers) - len(row))
        lines.append("| " + " | ".join(str(cell) for cell in padded_row[:len(headers)]) + " |")
    
    return "\n".join(lines)


def save_semantic_pdf(semantic_pdf: dict, output_path: str):
    """Save semantic PDF structure to JSON file."""
    # Remove image bytes before saving (too large)
    save_copy = json.loads(json.dumps(semantic_pdf, default=str))
    
    for fig_id in save_copy.get('figures_index', {}):
        if 'image_bytes' in save_copy['figures_index'][fig_id]:
            del save_copy['figures_index'][fig_id]['image_bytes']
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(save_copy, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # Test the parser
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.pdf_parser <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    print(f"Parsing: {pdf_path}\n")
    
    semantic_pdf = parse_semantic_pdf(pdf_path)
    
    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Sections: {len(semantic_pdf['sections'])}")
    print(f"Figures: {len(semantic_pdf['figures_index'])}")
    print(f"Tables: {len(semantic_pdf['tables_index'])}")
    print(f"Total characters: {semantic_pdf['total_chars']:,}")
    print(f"Truncated: {semantic_pdf['truncated']}")
    
    # Save to file
    output_path = pdf_path.replace('.pdf', '_semantic.json')
    save_semantic_pdf(semantic_pdf, output_path)
    print(f"\nSaved to: {output_path}")
    
    # Print text representation
    print(f"\n{'='*80}")
    print("TEXT REPRESENTATION (first 2000 chars)")
    print(f"{'='*80}")
    text = semantic_pdf_to_text(semantic_pdf)
    print(text[:2000])
