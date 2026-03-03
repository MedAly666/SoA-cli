"""
Citation style formatter for academic writing.

Supports multiple citation styles: IEEE, APA, Chicago, Harvard.
"""

from typing import Dict, Optional


class CitationFormatter:
    """
    Format citations according to different academic styles.
    
    Supported styles:
    - IEEE: Numeric citations [1], [2], etc.
    - APA: Author-date citations (Author, Year)
    - Chicago: Author-date with full names
    - Harvard: Author-date with surnames only
    """
    
    STYLES = ['ieee', 'apa', 'chicago', 'harvard']
    
    def __init__(self, style: str = 'ieee'):
        """
        Initialize citation formatter.
        
        Args:
            style: Citation style (ieee, apa, chicago, harvard)
        """
        self.style = style.lower()
        if self.style not in self.STYLES:
            raise ValueError(f"Unsupported citation style: {style}. Must be one of {self.STYLES}")
    
    def get_instructions(self) -> str:
        """
        Get citation style instructions for LLM prompts.
        
        Returns:
            Detailed instructions for the citation style
        """
        instructions = {
            'ieee': self._get_ieee_instructions(),
            'apa': self._get_apa_instructions(),
            'chicago': self._get_chicago_instructions(),
            'harvard': self._get_harvard_instructions()
        }
        return instructions[self.style]
    
    def _get_ieee_instructions(self) -> str:
        """IEEE citation style instructions."""
        return """**IEEE Citation Style:**

Use numeric citations in square brackets [1], [2], etc.

**In-text Citations:**
- Cite as: "The method was proposed in [1]"
- Multiple citations: "Several studies [1, 2, 5] have shown..."
- Sequential citations: "Recent work [3]-[7] demonstrates..."

**Reference List Format:**
[1] A. Author, B. Author, "Title of Paper," *Journal Name*, vol. X, no. Y, pp. Z-W, Month Year.
[2] A. Author, "Title of Book," Edition. City: Publisher, Year.

**Key Rules:**
- Number citations sequentially in order of appearance
- Use square brackets [N]
- List all authors (up to 6), then "et al." for more
- Italicize journal/book titles
- Include volume, issue, pages, and year"""
    
    def _get_apa_instructions(self) -> str:
        """APA citation style instructions."""
        return """**APA Citation Style (7th Edition):**

Use author-date citations in parentheses.

**In-text Citations:**
- Single author: (Smith, 2020)
- Two authors: (Smith & Jones, 2020)
- Three or more: (Smith et al., 2020)
- Multiple citations: (Jones, 2019; Smith, 2020)
- Narrative citation: Smith (2020) proposed...

**Reference List Format:**
Author, A. A., & Author, B. B. (Year). Title of article. *Journal Name*, *Volume*(Issue), Pages. https://doi.org/xxx

**Key Rules:**
- Use ampersand (&) in parenthetical citations
- Use "and" in narrative citations
- Italicize journal names and volume numbers
- Include DOI when available
- Alphabetize reference list by first author's surname"""
    
    def _get_chicago_instructions(self) -> str:
        """Chicago citation style instructions."""
        return """**Chicago Citation Style (Author-Date System):**

Use author-date citations in parentheses with full names on first mention.

**In-text Citations:**
- First mention: (Smith and Johnson 2020)
- Subsequent: (Smith and Johnson 2020)
- Multiple authors: (Smith et al. 2020)
- Multiple citations: (Jones 2019; Smith 2020)
- Page-specific: (Smith 2020, 45)

**Reference List Format:**
Smith, John A., and Mary B. Johnson. 2020. "Title of Article." *Journal Name* 15 (3): 123-145.

**Key Rules:**
- Use "and" (not &) between authors
- First and middle names spelled out in references
- Sentence case for article titles
- Title case for journal names
- No comma before year in citations"""
    
    def _get_harvard_instructions(self) -> str:
        """Harvard citation style instructions."""
        return """**Harvard Citation Style:**

Use author-date citations with surnames in parentheses.

**In-text Citations:**
- Single author: (Smith 2020)
- Two authors: (Smith and Jones 2020)
- Three or more: (Smith et al. 2020)
- Multiple citations: (Jones 2019; Smith 2020)
- Narrative: Smith (2020) argued...
- Page-specific: (Smith 2020, p. 45)

**Reference List Format:**
Smith, A. and Jones, B. (2020) 'Title of article', *Journal Name*, 15(3), pp. 123-145.

**Key Rules:**
- Use 'and' between authors
- Initials only for first/middle names
- Single quotes for article titles
- Italicize journal names
- Use 'pp.' for page ranges
- Alphabetize by surname"""
    
    def format_citation(self, authors: list, year: int, title: Optional[str] = None,
                       journal: Optional[str] = None, volume: Optional[int] = None,
                       issue: Optional[int] = None, pages: Optional[str] = None,
                       number: Optional[int] = None) -> str:
        """
        Format a full citation according to the style.
        
        Args:
            authors: List of author names
            year: Publication year
            title: Paper title
            journal: Journal name
            volume: Volume number
            issue: Issue number
            pages: Page range (e.g., "123-145")
            number: Citation number (for IEEE)
            
        Returns:
            Formatted citation string
        """
        # Provide defaults for None values
        title = title or "Untitled"
        journal = journal or "Unknown Journal"
        volume = volume or 1
        issue = issue or 1
        pages = pages or "1-10"
        
        if self.style == 'ieee':
            return self._format_ieee(number or 1, authors, title, journal, volume, issue, pages, year)
        elif self.style == 'apa':
            return self._format_apa(authors, year, title, journal, volume, issue, pages)
        elif self.style == 'chicago':
            return self._format_chicago(authors, year, title, journal, volume, issue, pages)
        elif self.style == 'harvard':
            return self._format_harvard(authors, year, title, journal, volume, issue, pages)
        
        return ""  # Fallback for unknown styles
    
    def _format_ieee(self, number: int, authors: list, title: str, journal: str,
                    volume: int, issue: int, pages: str, year: int) -> str:
        """Format IEEE citation."""
        # Format authors
        if len(authors) > 6:
            author_str = f"{authors[0]} et al."
        else:
            author_str = ", ".join(authors)
        
        # Build citation
        parts = [f"[{number}]", author_str]
        if title:
            parts.append(f'"{title},"')
        if journal:
            parts.append(f"*{journal}*,")
        if volume:
            parts.append(f"vol. {volume},")
        if issue:
            parts.append(f"no. {issue},")
        if pages:
            parts.append(f"pp. {pages},")
        parts.append(f"{year}.")
        
        return " ".join(parts)
    
    def _format_apa(self, authors: list, year: int, title: str, journal: str,
                   volume: int, issue: int, pages: str) -> str:
        """Format APA citation."""
        # Format authors (Last, F. M. format)
        if len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]}, & {authors[1]}"
        else:
            author_str = f"{authors[0]}, et al."
        
        # Build citation
        parts = [f"{author_str}. ({year})."]
        if title:
            parts.append(f"{title}.")
        if journal:
            parts.append(f"*{journal}*,")
        if volume and issue:
            parts.append(f"*{volume}*({issue}),")
        elif volume:
            parts.append(f"*{volume}*,")
        if pages:
            parts.append(f"{pages}.")
        
        return " ".join(parts)
    
    def _format_chicago(self, authors: list, year: int, title: str, journal: str,
                       volume: int, issue: int, pages: str) -> str:
        """Format Chicago citation."""
        # Format authors (Full names)
        if len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]}, and {authors[1]}"
        else:
            author_str = f"{authors[0]}, et al."
        
        # Build citation
        parts = [f"{author_str}. {year}."]
        if title:
            parts.append(f'"{title}."')
        if journal:
            parts.append(f"*{journal}*")
        if volume and issue:
            parts.append(f"{volume} ({issue}):")
        elif volume:
            parts.append(f"{volume}:")
        if pages:
            parts.append(f"{pages}.")
        
        return " ".join(parts)
    
    def _format_harvard(self, authors: list, year: int, title: str, journal: str,
                       volume: int, issue: int, pages: str) -> str:
        """Format Harvard citation."""
        # Format authors (Surname, Initials)
        if len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]} and {authors[1]}"
        else:
            author_str = f"{authors[0]} et al."
        
        # Build citation
        parts = [f"{author_str} ({year})"]
        if title:
            parts.append(f"'{title}',")
        if journal:
            parts.append(f"*{journal}*,")
        if volume and issue:
            parts.append(f"{volume}({issue}),")
        elif volume:
            parts.append(f"{volume},")
        if pages:
            parts.append(f"pp. {pages}.")
        
        return " ".join(parts)


def get_citation_instructions(style: str = 'ieee') -> str:
    """
    Get citation style instructions for the given style.
    
    Args:
        style: Citation style name
        
    Returns:
        Formatted citation instructions
    """
    formatter = CitationFormatter(style)
    return formatter.get_instructions()
