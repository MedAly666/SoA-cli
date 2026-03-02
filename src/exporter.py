#!/usr/bin/env python3
"""
Multi-Format output exporter for State of the Art documents.

Supports:
- LaTeX (.tex) - Default academic format
- Markdown (.md) - Clean format for documentation/web
- Microsoft Word (.docx) - For non-LaTeX workflows
"""

import re
from pathlib import Path
from typing import Optional


class SOAExporter:
    """
    Export State of the Art documents to multiple formats.
    
    Usage:
        exporter = SOAExporter()
        exporter.to_latex(content, "state_of_the_art.tex")
        exporter.to_markdown(content, "state_of_the_art.md")
        exporter.to_docx(content, "state_of_the_art.docx")
    """
    
    def to_latex(self, content: str, output_path: str):
        """
        Export to LaTeX format (pass-through, already in LaTeX).
        
        Args:
            content: LaTeX content
            output_path: Output file path (.tex)
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✓ LaTeX exported to: {output_path}")
    
    def to_markdown(self, content: str, output_path: str):
        """
        Convert LaTeX to Markdown.
        
        Args:
            content: LaTeX content
            output_path: Output file path (.md)
        """
        # Convert LaTeX to Markdown
        md_content = self._latex_to_markdown(content)
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"  ✓ Markdown exported to: {output_path}")
    
    def to_docx(self, content: str, output_path: str):
        """
        Convert LaTeX to Microsoft Word format.
        
        Args:
            content: LaTeX content
            output_path: Output file path (.docx)
        """
        try:
            from docx import Document
            from docx.shared import Pt, Inches
            from docx.enum.style import WD_STYLE_TYPE
        except ImportError:
            raise RuntimeError(
                "python-docx is required for .docx export. "
                "Install with: pip install python-docx"
            )
        
        # Convert LaTeX to structured content
        sections = self._parse_latex_sections(content)
        
        # Create Word document
        doc = Document()
        
        # Set default font
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Times New Roman'
        font.size = Pt(11)
        
        # Add title
        if 'title' in sections:
            title = doc.add_heading(sections['title'], level=0)
            title.alignment = 1  # Center
        
        # Add abstract
        if 'abstract' in sections:
            doc.add_heading('Abstract', level=1)
            doc.add_paragraph(sections['abstract'])
        
        # Add main sections
        for section in sections.get('sections', []):
            # Section heading
            doc.add_heading(section['title'], level=section['level'])
            
            # Section content
            for para in section['paragraphs']:
                p = doc.add_paragraph()
                self._add_formatted_text(p, para)
        
        # Add references
        if 'references' in sections:
            doc.add_page_break()
            doc.add_heading('References', level=1)
            for ref in sections['references']:
                doc.add_paragraph(ref, style='List Number')
        
        # Save document
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_file))
        
        print(f"  ✓ Word document exported to: {output_path}")
    
    def _latex_to_markdown(self, latex_content: str) -> str:
        """
        Convert LaTeX to Markdown.
        
        Args:
            latex_content: LaTeX source
        
        Returns:
            Markdown content
        """
        md = latex_content
        
        # Remove LaTeX document structure
        md = re.sub(r'\\documentclass\{.*?\}', '', md)
        md = re.sub(r'\\usepackage\{.*?\}', '', md)
        md = re.sub(r'\\begin\{document\}', '', md)
        md = re.sub(r'\\end\{document\}', '', md)
        
        # Convert title
        md = re.sub(r'\\title\{(.*?)\}', r'# \1', md)
        md = re.sub(r'\\maketitle', '', md)
        
        # Convert sections
        md = re.sub(r'\\section\{(.*?)\}', r'\n## \1\n', md)
        md = re.sub(r'\\subsection\{(.*?)\}', r'\n### \1\n', md)
        md = re.sub(r'\\subsubsection\{(.*?)\}', r'\n#### \1\n', md)
        
        # Convert text formatting
        md = re.sub(r'\\textbf\{(.*?)\}', r'**\1**', md)
        md = re.sub(r'\\textit\{(.*?)\}', r'*\1*', md)
        md = re.sub(r'\\emph\{(.*?)\}', r'*\1*', md)
        md = re.sub(r'\\texttt\{(.*?)\}', r'`\1`', md)
        
        # Convert citations
        md = re.sub(r'\\cite\{(.*?)\}', r'[\1]', md)
        md = re.sub(r'\\citep\{(.*?)\}', r'[\1]', md)
        md = re.sub(r'\\citet\{(.*?)\}', r'[\1]', md)
        
        # Convert lists
        md = re.sub(r'\\begin\{itemize\}', '', md)
        md = re.sub(r'\\end\{itemize\}', '', md)
        md = re.sub(r'\\begin\{enumerate\}', '', md)
        md = re.sub(r'\\end\{enumerate\}', '', md)
        md = re.sub(r'\\item\s+', '- ', md)
        
        # Convert abstract
        md = re.sub(r'\\begin\{abstract\}', '\n## Abstract\n', md)
        md = re.sub(r'\\end\{abstract\}', '', md)
        
        # Remove remaining LaTeX commands (generic)
        md = re.sub(r'\\[a-zA-Z]+\{(.*?)\}', r'\1', md)
        md = re.sub(r'\\[a-zA-Z]+', '', md)
        
        # Clean up whitespace
        md = re.sub(r'\n\n\n+', '\n\n', md)
        md = md.strip()
        
        return md
    
    def _parse_latex_sections(self, latex_content: str) -> dict:
        """
        Parse LaTeX into structured sections.
        
        Args:
            latex_content: LaTeX source
        
        Returns:
            Dictionary with title, abstract, sections, references
        """
        result = {
            'sections': [],
            'references': []
        }
        
        # Extract title
        title_match = re.search(r'\\title\{(.*?)\}', latex_content)
        if title_match:
            result['title'] = self._clean_latex(title_match.group(1))
        
        # Extract abstract
        abstract_match = re.search(
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}',
            latex_content,
            re.DOTALL
        )
        if abstract_match:
            result['abstract'] = self._clean_latex(abstract_match.group(1)).strip()
        
        # Extract sections
        # Match \section{...}, \subsection{...}, etc.
        section_pattern = r'\\((?:sub){0,2}section)\{([^}]+)\}'
        section_matches = list(re.finditer(section_pattern, latex_content))
        
        for i, match in enumerate(section_matches):
            section_type = match.group(1)
            section_title = self._clean_latex(match.group(2))
            
            # Determine heading level
            if section_type == 'section':
                level = 1
            elif section_type == 'subsection':
                level = 2
            else:  # subsubsection
                level = 3
            
            # Extract content until next section
            start = match.end()
            if i + 1 < len(section_matches):
                end = section_matches[i + 1].start()
            else:
                end = len(latex_content)
            
            content = latex_content[start:end].strip()
            
            # Split into paragraphs
            paragraphs = [
                self._clean_latex(p.strip())
                for p in content.split('\n\n')
                if p.strip() and not p.strip().startswith('\\')
            ]
            
            result['sections'].append({
                'title': section_title,
                'level': level,
                'paragraphs': paragraphs
            })
        
        # Extract references (if in thebibliography environment)
        bib_match = re.search(
            r'\\begin\{thebibliography\}.*?(.*?)\\end\{thebibliography\}',
            latex_content,
            re.DOTALL
        )
        if bib_match:
            bib_content = bib_match.group(1)
            # Extract \bibitem entries
            bib_items = re.findall(r'\\bibitem\{.*?\}(.*?)(?=\\bibitem|$)', bib_content, re.DOTALL)
            result['references'] = [
                self._clean_latex(item.strip())
                for item in bib_items
                if item.strip()
            ]
        
        return result
    
    def _clean_latex(self, text: str) -> str:
        """
        Remove LaTeX commands and clean text.
        
        Args:
            text: LaTeX text
        
        Returns:
            Cleaned text
        """
        # Remove common LaTeX commands
        text = re.sub(r'\\textbf\{(.*?)\}', r'\1', text)
        text = re.sub(r'\\textit\{(.*?)\}', r'\1', text)
        text = re.sub(r'\\emph\{(.*?)\}', r'\1', text)
        text = re.sub(r'\\texttt\{(.*?)\}', r'\1', text)
        text = re.sub(r'\\cite\{(.*?)\}', r'[\1]', text)
        text = re.sub(r'\\citep\{(.*?)\}', r'[\1]', text)
        text = re.sub(r'\\citet\{(.*?)\}', r'[\1]', text)
        text = re.sub(r'\\ref\{(.*?)\}', r'[\1]', text)
        text = re.sub(r'\\label\{.*?\}', '', text)
        
        # Remove generic LaTeX commands
        text = re.sub(r'\\[a-zA-Z]+\{(.*?)\}', r'\1', text)
        text = re.sub(r'\\[a-zA-Z]+', '', text)
        
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _add_formatted_text(self, paragraph, text: str):
        """
        Add formatted text to a Word paragraph.
        
        Handles inline formatting like bold, italic, citations.
        
        Args:
            paragraph: python-docx Paragraph object
            text: Text with potential LaTeX formatting
        """
        # For simplicity, just add as plain text
        # In a more sophisticated version, we could parse and apply formatting
        paragraph.add_run(text)


def export_all_formats(
    content: str,
    base_name: str = "state_of_the_art_final",
    output_dir: str = "artifacts/soa"
):
    """
    Export content to all formats (LaTeX, Markdown, Word).
    
    Args:
        content: LaTeX content to export
        base_name: Base filename (without extension)
        output_dir: Output directory
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    exporter = SOAExporter()
    
    print("\n[Export] Generating multi-format outputs...")
    
    # Export to LaTeX
    latex_file = output_path / f"{base_name}.tex"
    exporter.to_latex(content, str(latex_file))
    
    # Export to Markdown
    md_file = output_path / f"{base_name}.md"
    exporter.to_markdown(content, str(md_file))
    
    # Export to Word (if python-docx available)
    try:
        docx_file = output_path / f"{base_name}.docx"
        exporter.to_docx(content, str(docx_file))
    except RuntimeError as e:
        print(f"  ! Skipping .docx export: {e}")
    
    print("  ✓ Export complete")
