#!/usr/bin/env python3
"""
Citation Style Formatter

Provides citation formatting instructions for different academic styles:
- IEEE (default): Numerical citations [1], [2], etc.
- APA: Author-date citations (Author, Year)
- Chicago: Footnote or author-date citations
- Harvard: Author-date citations

These instructions are injected into LLM prompts to ensure consistent
citation formatting throughout the generated State of the Art document.
"""

import os
from typing import Dict, Optional


class CitationFormatter:
    """
    Provides citation style instructions for LLM prompts.
    
    Usage:
        formatter = CitationFormatter("ieee")
        instructions = formatter.get_instructions()
        # Inject into system prompt: prompt.format(citation_style_instructions=instructions)
    """
    
    # Citation style instructions for LLMs
    STYLES = {
        "ieee": {
            "name": "IEEE", 
            "description": "Institute of Electrical and Electronics Engineers",
            "instructions": """
## Citation Style: IEEE

Use IEEE citation style with numerical citations in square brackets.

**In-text citations:**
- Use numbers in square brackets: [1], [2], [3]
- Multiple citations: [1], [2], [5]
- Citation ranges: [1]-[5]
- Place citations before periods and commas
- Example: "Machine learning has shown promise [1], [3]."

**Reference format:**
[1] A. Author, "Title of paper," Journal Name, vol. X, no. Y, pp. Z-W, Month Year.
[2] B. Author and C. Coauthor, "Title," in Proc. Conference Name, Year, pp. Z-W.
[3] D. Author et al., "Title," Journal, vol. X, pp. Y-Z, Year.

**Key rules:**
- Use abbreviated first names (initial only)
- Italicize journal names
- Use "et al." for more than 3 authors
- List all authors for 3 or fewer authors
""",
            "example": '[1] J. Smith, "Deep learning methods," IEEE Trans. Neural Netw., vol. 25, no. 3, pp. 123-134, Mar. 2020.'
        },
        
        "apa": {
            "name": "APA",
            "description": "American Psychological Association",
            "instructions": """
## Citation Style: APA (7th Edition)

Use APA citation style with author-date citations in parentheses.

**In-text citations:**
- Single author: (Smith, 2020)
- Two authors: (Smith & Jones, 2020)
- Three+ authors: (Smith et al., 2020)
- Multiple works: (Smith, 2020; Jones, 2021)
- Direct quote: (Smith, 2020, p. 45)
- Example: "Recent studies (Smith, 2020; Jones et al., 2021) demonstrate..."

**Reference format:**
Author, A. A. (Year). Title of article. Journal Name, Volume(Issue), Pages. https://doi.org/xxx

Smith, J. A., & Johnson, B. C. (2020). Deep learning methods for classification. 
    Journal of Machine Learning Research, 25(3), 123-134. https://doi.org/10.XXXX/xxxxx

**Key rules:**
- Use full first and middle names (initials)
- Capitalize only first word of title and proper nouns
- Italicize journal name and volume number
- Include DOI when available
- Use "&" before last author in citations
""",
            "example": 'Smith, J. A., & Johnson, B. (2020). Deep learning in medicine. Nature Medicine, 15(2), 234-245.'
        },
        
        "chicago": {
            "name": "Chicago",
            "description": "Chicago Manual of Style",
            "instructions": """
## Citation Style: Chicago (Author-Date System)

Use Chicago author-date citation style.

**In-text citations:**
- Single author: (Smith 2020)
- Two authors: (Smith and Jones 2020)
- Three+ authors: (Smith et al. 2020)
- Multiple works: (Smith 2020; Jones 2021)
- Page reference: (Smith 2020, 45)
- Example: "Recent advances (Smith 2020) show..."

**Reference format:**
Author, First. Year. "Title of Article." Journal Name Volume (Issue): Pages.

Smith, John. 2020. "Deep Learning Methods for Image Classification." 
    Journal of Machine Learning Research 25, no. 3: 123-34.

**Key rules:**
- Use full first names
- Capitalize all major words in titles
- Use "and" (not "&") between authors
- No comma after author in citation
- Include page numbers without "pp."
""",
            "example": 'Smith, John, and Mary Johnson. 2020. "Neural networks in practice." IEEE Transactions 15 (2): 234-45.'
        },
        
        "harvard": {
            "name": "Harvard",
            "description": "Harvard referencing style",
            "instructions": """
## Citation Style: Harvard

Use Harvard citation style with author-date citations.

**In-text citations:**
- Single author: (Smith 2020)
- Two authors: (Smith and Jones 2020)
- Three+ authors: (Smith et al. 2020)
- Multiple works: (Smith 2020; Jones 2021)
- Page reference: (Smith 2020, p. 45)
- Example: "Studies show (Smith 2020) that..."

**Reference format:**
Author, A.A. (Year) 'Title of article', Journal Name, Volume(Issue), pp. Pages.

Smith, J.A. (2020) 'Deep learning methods for classification', 
    Journal of Machine Learning Research, 25(3), pp. 123-134.

**Key rules:**
- Use initials for first names
- Single quotes around article titles
- Italicize journal names
- Use "and" (not "&") in references
- Include "pp." before page numbers
- Use comma before year in references
""",
            "example": "Smith, J. and Johnson, M. (2020) 'Neural networks in medical imaging', Nature Medicine, 15(2), pp. 234-245."
        }
    }
    
    def __init__(self, style: Optional[str] = None):
        """
        Initialize citation formatter.
        
        Args:
            style: Citation style (ieee, apa, chicago, harvard)
                  If None, uses CITATION_STYLE from environment or defaults to ieee
        """
        if style is None:
            style = os.getenv("CITATION_STYLE", "ieee").lower()
        
        self.style = style.lower()
        
        if self.style not in self.STYLES:
            print(f"[!] Warning: Unknown citation style '{style}', using IEEE")
            self.style = "ieee"
    
    def get_instructions(self) -> str:
        """
        Get citation style instructions for LLM prompts.
        
        Returns:
            Formatted instructions string
        """
        style_info = self.STYLES[self.style]
        return style_info["instructions"]
    
    def get_example(self) -> str:
        """
        Get an example citation in the current style.
        
        Returns:
            Example citation string
        """
        return self.STYLES[self.style]["example"]
    
    def get_name(self) -> str:
        """Get the full name of the citation style."""
        return self.STYLES[self.style]["name"]
    
    def get_description(self) -> str:
        """Get the description of the citation style."""
        return self.STYLES[self.style]["description"]
    
    @classmethod
    def list_styles(cls) -> list:
        """
        List all available citation styles.
        
        Returns:
            List of style identifiers
        """
        return list(cls.STYLES.keys())
    
    @classmethod
    def get_style_info(cls, style: str) -> Dict[str, str]:
        """
        Get information about a specific citation style.
        
        Args:
            style: Style identifier (ieee, apa, chicago, harvard)
        
        Returns:
            Dictionary with name, description, instructions, example
        """
        return cls.STYLES.get(style.lower(), cls.STYLES["ieee"])


def inject_citation_style(prompt: str, style: Optional[str] = None) -> str:
    """
    Inject citation style instructions into a prompt.
    
    Replaces {citation_style_instructions} placeholder with actual instructions.
    
    Args:
        prompt: Prompt template with {citation_style_instructions} placeholder
        style: Citation style (ieee, apa, chicago, harvard)
    
    Returns:
        Prompt with injected citation instructions
    """
    formatter = CitationFormatter(style)
    instructions = formatter.get_instructions()
    
    return prompt.replace("{citation_style_instructions}", instructions)


def get_citation_style() -> str:
    """
    Get the current citation style from environment.
    
    Returns:
        Citation style identifier (ieee, apa, chicago, harvard)
    """
    return os.getenv("CITATION_STYLE", "ieee").lower()
