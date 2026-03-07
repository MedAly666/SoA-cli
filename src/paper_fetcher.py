"""
PRISMA-Compliant Paper Fetcher for SOA-CLI.

Implements systematic literature review methodology following:
- PRISMA (Preferred Reporting Items for Systematic Reviews and Meta-Analyses)
- Quality filters to avoid predatory journals
- Multi-database search and deduplication
- Automated screening with LLM assistance
"""

import json
import requests
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import re


@dataclass
class PaperCandidate:
    """Paper metadata with PRISMA tracking."""
    # Basic metadata
    title: str
    authors: List[str]
    year: int
    venue: str
    abstract: str = ""
    
    # Identifiers
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    
    # Quality indicators
    citation_count: int = 0
    publication_type: str = "unknown"  # journal, conference, workshop, preprint
    source: str = ""  # semantic_scholar, arxiv, dblp
    
    # Download info
    pdf_url: Optional[str] = None
    pdf_path: Optional[str] = None
    open_access: bool = False
    
    # PRISMA tracking
    screening_status: str = "pending"  # pending, passed, excluded_abstract
    eligibility_status: str = "pending"  # pending, eligible, excluded_eligibility
    exclusion_reason: str = ""
    exclusion_stage: str = ""  # screening, eligibility_quality, eligibility_criteria
    status: str = "candidate"  # candidate, included, excluded
    
    # Metadata
    identified_date: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class PRISMALog:
    """Tracks PRISMA workflow stages and statistics."""
    
    def __init__(self):
        # Identification
        self.search_date = datetime.now().isoformat()
        self.queries = []
        self.databases = []
        self.total_identified = 0
        self.source_results = {}
        
        # Screening
        self.duplicates_removed = 0
        self.records_screened = 0
        self.excluded_abstract = []
        
        # Eligibility
        self.full_text_assessed = 0
        self.excluded_full_text = []
        
        # Included
        self.total_included = 0
        self.included_papers = []
        self.failed_downloads = []
    
    def log_search_strategy(self, queries, databases, date, inclusion_criteria, exclusion_criteria):
        """Document search strategy for PRISMA report."""
        self.queries = queries
        self.databases = databases
        self.search_date = date
        self.inclusion_criteria = inclusion_criteria
        self.exclusion_criteria = exclusion_criteria
    
    def log_source_results(self, source, count):
        """Log results from each database source."""
        self.source_results[source] = count


class VenueWhitelist:
    """Manages venue whitelists and predatory publisher detection."""
    
    def __init__(self, config_file: str = "config/venues.json"):
        self.config_file = Path(config_file)
        self.whitelist = self._load_whitelist()
    
    def _load_whitelist(self) -> Dict:
        """Load venue whitelist from config file."""
        if not self.config_file.exists():
            print(f"  ⚠️  Venue whitelist not found: {self.config_file}")
            return {"conferences": {}, "journals": {}}
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def is_whitelisted(self, venue: str) -> bool:
        """Check if venue is on the whitelist."""
        if not venue:
            return False
        
        venue_lower = venue.lower().strip()
        
        # Check conferences
        for category, conferences in self.whitelist.get('conferences', {}).items():
            for conf in conferences:
                if conf.lower() in venue_lower or venue_lower in conf.lower():
                    return True
        
        # Check journals
        for category, journals in self.whitelist.get('journals', {}).items():
            for journal in journals:
                if journal.lower() in venue_lower or venue_lower in journal.lower():
                    return True
        
        return False
    
    def is_predatory(self, venue: str, publisher: str = "") -> bool:
        """Check if venue/publisher is predatory."""
        if not venue:
            return False
        
        venue_lower = venue.lower()
        pub_lower = publisher.lower() if publisher else ""
        
        # Check predatory publishers
        for pred_pub in self.whitelist.get('predatory_publishers', []):
            if pred_pub and pub_lower and pred_pub.lower() in pub_lower:
                return True
        
        # Check predatory patterns
        for pattern in self.whitelist.get('predatory_patterns', []):
            if pattern and pattern in venue_lower:
                return True
        
        return False


class PRISMAPaperFetcher:
    """
    PRISMA-compliant paper fetcher for systematic literature reviews.
    Follows all PRISMA guidelines for transparent and reproducible search.
    """
    
    def __init__(self, contract: Dict, config: Dict):
        """
        Initialize PRISMA paper fetcher.
        
        Args:
            contract: Thematic contract with research scope
            config: Configuration dict with search parameters
        """
        self.contract = contract
        self.config = config
        self.prisma_log = PRISMALog()
        self.venue_whitelist = VenueWhitelist()
        
        # Load configuration
        self.sources = config.get('sources', ['semantic_scholar', 'arxiv'])
        self.max_papers = config.get('max_papers', 50)
        self.min_year = config.get('min_year', 2015)
        self.min_citations = config.get('min_citations', 10)
        self.require_whitelist = config.get('require_venue_whitelist', True)
    
    
    # ========== MAIN WORKFLOW ==========
    
    def run_systematic_search(self, auto_download: bool = False) -> Dict:
        """
        Execute complete PRISMA workflow.
        
        Args:
            auto_download: If True, automatically downloads eligible papers.
                          If False, saves candidates for manual review.
        
        Returns:
            Dictionary with PRISMA report data
        """
        print("\n" + "="*80)
        print(" "*20 + "PRISMA SYSTEMATIC REVIEW")
        print("="*80)
        
        # Stage 1: IDENTIFICATION
        identified = self.identification_stage()
        
        # Stage 2: SCREENING
        screened = self.screening_stage(identified)
        
        # Stage 3: ELIGIBILITY
        eligible = self.eligibility_stage(screened)
        
        # Save candidates for review
        self.save_candidates(eligible, "paper_candidates.json")
        
        # Stage 4: INCLUSION (optional auto-download)
        if auto_download:
            included = self.inclusion_stage(eligible)
        else:
            print("\n" + "="*80)
            print("REVIEW REQUIRED")
            print("="*80)
            print(f"\n✓ {len(eligible)} papers passed eligibility assessment")
            print(f"✓ Candidates saved to: paper_candidates.json")
            print(f"\n📋 Next steps:")
            print(f"  1. Review paper_candidates.json")
            print(f"  2. Edit 'status' field: 'approved' or 'rejected'")
            print(f"  3. Run: python soa_cli.py --download-papers")
            included = []
        
        # Generate PRISMA report
        report = self.generate_prisma_report()
        
        return report
    
    
    # ========== STAGE 1: IDENTIFICATION ==========
    
    def identification_stage(self) -> List[PaperCandidate]:
        """
        PRISMA Stage 1: Identify papers from multiple databases.
        """
        print("\n" + "="*80)
        print("STAGE 1: IDENTIFICATION")
        print("="*80)
        
        # Generate search queries from thematic contract
        queries = self.generate_search_queries()
        print(f"\n[Search Queries Generated]: {len(queries)}")
        for i, q in enumerate(queries, 1):
            print(f"  {i}. {q}")
        
        self.prisma_log.log_search_strategy(
            queries=queries,
            databases=self.sources,
            date=datetime.now().isoformat(),
            inclusion_criteria=self.contract.get('in_scope', []),
            exclusion_criteria=self.contract.get('out_of_scope', [])
        )
        
        all_papers = []
        
        # Search each database
        for source in self.sources:
            print(f"\n[Searching: {source.upper()}]")
            try:
                papers = self.search_database(source, queries)
                print(f"  ✓ Found {len(papers)} records")
                
                # Tag with source
                for paper in papers:
                    paper.source = source
                
                all_papers.extend(papers)
                self.prisma_log.log_source_results(source, len(papers))
            
            except Exception as e:
                print(f"  ✗ Error searching {source}: {e}")
                self.prisma_log.log_source_results(source, 0)
        
        print(f"\n[Total Identified]: {len(all_papers)} records from {len(self.sources)} sources")
        self.prisma_log.total_identified = len(all_papers)
        
        return all_papers
    
    
    def generate_search_queries(self) -> List[str]:
        """
        Generate search queries from thematic contract using LLM.
        """
        from src.llm_client import LLMClient
        from pathlib import Path
        
        # Load system prompt from file
        prompt_path = Path("prompts/query_generator.system.txt")
        with open(prompt_path, 'r', encoding='utf-8') as f:
            system_prompt = f.read()

        user_prompt = f"""Research Theme: {self.contract.get('global_theme', '')}

In Scope:
{chr(10).join('- ' + item for item in self.contract.get('in_scope', [])[:5])}

Out of Scope:
{chr(10).join('- ' + item for item in self.contract.get('out_of_scope', [])[:3])}

Generate search queries now:"""

        try:
            client = LLMClient(timeout=60)
            response = client.call(system_prompt, user_prompt)
            
            # Parse queries (one per line)
            queries = [q.strip() for q in response.strip().split('\n') if q.strip() and len(q.strip()) > 5]
            
            # Filter out queries that are just explanations
            queries = [q for q in queries if not q.startswith(('#', '//', 'Query', 'Search'))]
            
            return queries[:7] if queries else [self.contract.get('global_theme', 'research')]
        
        except Exception as e:
            print(f"  ⚠️  LLM query generation failed: {e}")
            # Fallback: use thematic contract keywords
            return [self.contract.get('global_theme', 'research')]
    
    
    def search_database(self, source: str, queries: List[str]) -> List[PaperCandidate]:
        """
        Search a specific database with multiple queries.
        """
        if source == 'semantic_scholar':
            return self.search_semantic_scholar(queries)
        elif source == 'arxiv':
            return self.search_arxiv(queries)
        elif source == 'dblp':
            return self.search_dblp(queries)
        else:
            print(f"  ⚠️  Unknown source: {source}")
            return []
    
    
    def search_semantic_scholar(self, queries: List[str]) -> List[PaperCandidate]:
        """Search Semantic Scholar API."""
        base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        all_papers = []
        
        for query in queries:
            try:
                params = {
                    'query': query,
                    'limit': min(100, self.max_papers),
                    'fields': 'title,authors,year,venue,citationCount,abstract,isOpenAccess,externalIds,publicationTypes',
                    'minCitationCount': max(0, self.min_citations - 5),  # Slightly lower for search
                    'year': f'{self.min_year}-'
                }
                
                response = requests.get(base_url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    papers_data = data.get('data', [])
                    
                    for item in papers_data:
                        paper = self._parse_semantic_scholar_paper(item)
                        if paper:
                            all_papers.append(paper)
                
                elif response.status_code == 429:
                    print(f"    Rate limited, waiting 60s...")
                    time.sleep(60)
                
                # Be nice to the API
                time.sleep(1)
            
            except Exception as e:
                print(f"    Error with query '{query}': {e}")
        
        return all_papers
    
    
    def _parse_semantic_scholar_paper(self, item: Dict) -> Optional[PaperCandidate]:
        """Parse Semantic Scholar API response into PaperCandidate."""
        try:
            # Extract authors
            authors = [a.get('name', 'Unknown') for a in item.get('authors', [])]
            
            # Extract identifiers
            external_ids = item.get('externalIds', {})
            
            # Determine publication type
            pub_types = item.get('publicationTypes') or []
            if pub_types and 'JournalArticle' in pub_types:
                pub_type = 'journal'
            elif pub_types and 'Conference' in pub_types:
                pub_type = 'conference'
            elif pub_types and 'Review' in pub_types:
                pub_type = 'review'
            else:
                pub_type = 'unknown'
            
            paper = PaperCandidate(
                title=item.get('title', 'Untitled'),
                authors=authors,
                year=item.get('year', 0),
                venue=item.get('venue', 'Unknown'),
                abstract=item.get('abstract') or '',  # Handle None
                doi=external_ids.get('DOI'),
                arxiv_id=external_ids.get('ArXiv'),
                semantic_scholar_id=item.get('paperId'),
                citation_count=item.get('citationCount', 0),
                publication_type=pub_type,
                source='semantic_scholar',
                open_access=item.get('isOpenAccess', False)
            )
            
            # Try to get PDF URL from open access
            if paper.open_access and paper.semantic_scholar_id:
                paper.pdf_url = f"https://api.semanticscholar.org/v1/paper/{paper.semantic_scholar_id}"
            
            return paper
        
        except Exception as e:
            print(f"      Error parsing paper: {e}")
            return None
    
    
    def search_arxiv(self, queries: List[str]) -> List[PaperCandidate]:
        """Search arXiv API."""
        base_url = "http://export.arxiv.org/api/query"
        all_papers = []
        
        for query in queries:
            try:
                params = {
                    'search_query': f'all:{query}',
                    'start': 0,
                    'max_results': min(100, self.max_papers),
                    'sortBy': 'relevance'
                }
                
                response = requests.get(base_url, params=params, timeout=30)
                
                if response.status_code == 200:
                    # Parse XML response
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(response.content)
                    
                    # Namespace handling
                    ns = {'atom': 'http://www.w3.org/2005/Atom'}
                    
                    for entry in root.findall('atom:entry', ns):
                        paper = self._parse_arxiv_entry(entry, ns)
                        if paper:
                            all_papers.append(paper)
                
                # Be nice to the API
                time.sleep(3)
            
            except Exception as e:
                print(f"    Error with query '{query}': {e}")
        
        return all_papers
    
    
    def _parse_arxiv_entry(self, entry, ns) -> Optional[PaperCandidate]:
        """Parse arXiv XML entry into PaperCandidate."""
        try:
            title_elem = entry.find('atom:title', ns)
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else 'Untitled'
            summary_elem = entry.find('atom:summary', ns)
            abstract = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ''
            
            # Extract arXiv ID
            arxiv_id = entry.find('atom:id', ns).text.split('/abs/')[-1]
            
            # Extract authors
            authors = [author.find('atom:name', ns).text 
                      for author in entry.findall('atom:author', ns)]
            
            # Extract year from published date
            published = entry.find('atom:published', ns).text
            year = int(published[:4])
            
            # PDF URL
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            
            paper = PaperCandidate(
                title=title,
                authors=authors,
                year=year,
                venue='arXiv',
                abstract=abstract or '',  # Handle None/empty
                arxiv_id=arxiv_id,
                citation_count=0,  # arXiv doesn't provide citations
                publication_type='preprint',
                source='arxiv',
                pdf_url=pdf_url,
                open_access=True
            )
            
            return paper
        
        except Exception as e:
            print(f"      Error parsing arXiv entry: {e}")
            return None
    
    
    def search_dblp(self, queries: List[str]) -> List[PaperCandidate]:
        """Search DBLP (computer science bibliography)."""
        # DBLP API implementation
        # For now, return empty (can be implemented later)
        print("    DBLP search not yet implemented")
        return []
    
    
    # ========== STAGE 2: SCREENING ==========
    
    def screening_stage(self, papers: List[PaperCandidate]) -> List[PaperCandidate]:
        """
        PRISMA Stage 2: Screen titles and abstracts.
        """
        print("\n" + "="*80)
        print("STAGE 2: SCREENING")
        print("="*80)
        
        print(f"\n[Input]: {len(papers)} records")
        
        # Step 2.1: Remove duplicates
        deduplicated = self.remove_duplicates(papers)
        n_duplicates = len(papers) - len(deduplicated)
        print(f"[Duplicates Removed]: {n_duplicates}")
        self.prisma_log.duplicates_removed = n_duplicates
        self.prisma_log.records_screened = len(deduplicated)
        
        # Step 2.2: Title/Abstract screening
        print(f"\n[Title/Abstract Screening]: {len(deduplicated)} records")
        screened = []
        excluded_abstract = []
        
        for i, paper in enumerate(deduplicated, 1):
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(deduplicated)}")
            
            decision, reason = self.screen_title_abstract(paper)
            
            if decision == "include":
                paper.screening_status = "passed"
                screened.append(paper)
                print(f"  ✓ [{i}] INCLUDED: {paper.title[:60]}...")
            else:
                paper.screening_status = "excluded_abstract"
                paper.exclusion_reason = reason
                paper.exclusion_stage = "screening"
                paper.status = "excluded"
                excluded_abstract.append(paper)
                print(f"  ✗ [{i}] EXCLUDED: {paper.title[:60]}...")
                print(f"      → Reason: {reason}")
        
        print(f"\n[Results]:")
        print(f"  ✓ Passed: {len(screened)}")
        print(f"  ✗ Excluded: {len(excluded_abstract)}")
        
        # Show summary of exclusion reasons
        if excluded_abstract:
            print(f"\n[Exclusion Summary]:")
            for paper in excluded_abstract[:5]:  # Show first 5
                print(f"  • {paper.title[:50]}...")
                print(f"    {paper.exclusion_reason}")
            if len(excluded_abstract) > 5:
                print(f"  ... and {len(excluded_abstract) - 5} more")
        
        self.prisma_log.excluded_abstract = excluded_abstract
        
        return screened
    
    
    def remove_duplicates(self, papers: List[PaperCandidate]) -> List[PaperCandidate]:
        """Remove duplicate papers based on DOI, arXiv ID, or title similarity."""
        seen_dois = set()
        seen_arxiv = set()
        seen_titles = set()
        unique_papers = []
        
        for paper in papers:
            # Check DOI
            if paper.doi and paper.doi in seen_dois:
                continue
            
            # Check arXiv ID
            if paper.arxiv_id and paper.arxiv_id in seen_arxiv:
                continue
            
            # Check title (normalized)
            title_normalized = re.sub(r'[^a-z0-9]', '', paper.title.lower())
            if title_normalized in seen_titles:
                continue
            
            # Add to unique set
            if paper.doi:
                seen_dois.add(paper.doi)
            if paper.arxiv_id:
                seen_arxiv.add(paper.arxiv_id)
            seen_titles.add(title_normalized)
            
            unique_papers.append(paper)
        
        return unique_papers
    
    
    def screen_title_abstract(self, paper: PaperCandidate) -> Tuple[str, str]:
        """
        Screen paper based on title and abstract using LLM.
        Returns: (decision, reason)
        """
        from src.llm_client import LLMClient
        from pathlib import Path
        
        # Load system prompt from file
        prompt_path = Path("prompts/paper_screening.system.txt")
        with open(prompt_path, 'r', encoding='utf-8') as f:
            system_prompt_template = f.read()
        
        # Format the template with contract data
        system_prompt = system_prompt_template.format(
            global_theme=self.contract.get('global_theme', ''),
            in_scope=chr(10).join('- ' + item for item in self.contract.get('in_scope', [])[:5]),
            out_of_scope=chr(10).join('- ' + item for item in self.contract.get('out_of_scope', [])[:5])
        )

        # Handle None or missing abstract
        if paper.abstract and len(paper.abstract) > 300:
            abstract_preview = paper.abstract[:300] + "..."
        elif paper.abstract:
            abstract_preview = paper.abstract
        else:
            abstract_preview = "[No abstract available]"
        
        user_prompt = f"""Title: {paper.title}

Abstract: {abstract_preview}

Venue: {paper.venue}
Year: {paper.year}

Decision:"""

        try:
            client = LLMClient(timeout=30)
            response = client.call(system_prompt, user_prompt).strip()
            
            if response.startswith("INCLUDE") or "include" in response.lower()[:20]:
                return ("include", "")
            else:
                # Extract reason
                reason = response.replace("EXCLUDE:", "").replace("EXCLUDE", "").strip()
                if not reason:
                    reason = "Not relevant to research theme"
                return ("exclude", reason)
        
        except Exception as e:
            # If LLM fails, be conservative and include
            print(f"      ⚠️  Screening failed for '{paper.title[:50]}...': {e}")
            return ("include", "LLM screening unavailable")
    
    
    # ========== STAGE 3: ELIGIBILITY ==========
    
    def eligibility_stage(self, papers: List[PaperCandidate]) -> List[PaperCandidate]:
        """
        PRISMA Stage 3: Assess eligibility with quality criteria.
        """
        print("\n" + "="*80)
        print("STAGE 3: ELIGIBILITY")
        print("="*80)
        
        print(f"\n[Quality Assessment]: {len(papers)} papers")
        
        eligible = []
        excluded_full_text = []
        
        for paper in papers:
            # Check quality criteria
            quality_passed, reason = self.check_quality_criteria(paper)
            
            if not quality_passed:
                paper.exclusion_reason = reason
                paper.exclusion_stage = "eligibility_quality"
                paper.status = "excluded"
                excluded_full_text.append(paper)
                continue
            
            # Check inclusion/exclusion criteria
            criteria_passed, reason = self.check_inclusion_criteria(paper)
            
            if criteria_passed:
                paper.eligibility_status = "eligible"
                paper.status = "approved"  # Ready for download
                eligible.append(paper)
            else:
                paper.exclusion_reason = reason
                paper.exclusion_stage = "eligibility_criteria"
                paper.status = "excluded"
                excluded_full_text.append(paper)
        
        print(f"\n[Results]:")
        print(f"  ✓ Eligible: {len(eligible)}")
        print(f"  ✗ Excluded: {len(excluded_full_text)}")
        
        # Log exclusion reasons
        self.log_exclusion_reasons(excluded_full_text)
        self.prisma_log.excluded_full_text = excluded_full_text
        self.prisma_log.full_text_assessed = len(papers)
        
        return eligible
    
    
    def check_quality_criteria(self, paper: PaperCandidate) -> Tuple[bool, str]:
        """
        Check quality criteria: venue whitelist, citations, year, peer review.
        Returns: (passed, reason)
        """
        # Year filter
        if paper.year < self.min_year:
            return (False, f"Year ({paper.year}) before {self.min_year}")
        
        # Citation filter (with exception for very recent papers)
        current_year = datetime.now().year
        if paper.year < current_year - 1 and paper.citation_count < self.min_citations:
            return (False, f"Insufficient citations ({paper.citation_count} < {self.min_citations})")
        
        # Venue whitelist check
        if self.require_whitelist:
            if not self.venue_whitelist.is_whitelisted(paper.venue):
                # Exception for highly cited arXiv preprints
                if paper.source == 'arxiv' and paper.citation_count >= 50:
                    return (True, "")  # Highly cited preprint
                return (False, f"Venue not whitelisted: {paper.venue}")
        
        # Check for predatory publishers
        if self.venue_whitelist.is_predatory(paper.venue):
            return (False, f"Predatory publisher detected: {paper.venue}")
        
        # Publication type filter
        if paper.publication_type in ['workshop', 'poster', 'abstract']:
            return (False, f"Publication type: {paper.publication_type}")
        
        return (True, "")
    
    
    def check_inclusion_criteria(self, paper: PaperCandidate) -> Tuple[bool, str]:
        """
        Check against thematic contract inclusion/exclusion criteria.
        Returns: (included, reason)
        """
        text = f"{paper.title} {paper.abstract}".lower()
        
        # Check for out-of-scope terms (strict)
        for oos in self.contract.get('out_of_scope', []):
            if len(oos) > 5 and oos.lower() in text:
                return (False, f"Out-of-scope: {oos}")
        
        # Check for in-scope terms (need multiple matches)
        in_scope = self.contract.get('in_scope', [])
        matches = 0
        for term in in_scope:
            if len(term) > 3:
                # Split compound terms and check for keywords
                keywords = [w.lower() for w in term.split() if len(w) > 3]
                if any(kw in text for kw in keywords):
                    matches += 1
        
        # Require at least 2 in-scope matches
        if matches < 2:
            return (False, "Insufficient relevance to research scope")
        
        return (True, "")
    
    
    def log_exclusion_reasons(self, excluded_papers: List[PaperCandidate]):
        """Summarize and log exclusion reasons."""
        reason_counts = {}
        for paper in excluded_papers:
            reason = paper.exclusion_reason[:50]  # Truncate long reasons
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        if reason_counts:
            print(f"\n[Exclusion Reasons]:")
            for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1])[:5]:
                print(f"  • {reason}: {count}")
    
    
    # ========== STAGE 4: INCLUSION ==========
    
    def inclusion_stage(self, papers: List[PaperCandidate]) -> List[PaperCandidate]:
        """
        PRISMA Stage 4: Download approved papers.
        """
        print("\n" + "="*80)
        print("STAGE 4: INCLUSION")
        print("="*80)
        
        print(f"\n[Downloading]: {len(papers)} papers")
        
        included = []
        failed = []
        
        for i, paper in enumerate(papers, 1):
            if paper.status == "approved":
                success = self.download_paper(paper)
                
                if success:
                    paper.status = "included"
                    included.append(paper)
                    print(f"  [{i}/{len(papers)}] ✓ {paper.title[:60]}...")
                else:
                    paper.status = "excluded"
                    paper.exclusion_reason = "PDF download failed"
                    failed.append(paper)
                    print(f"  [{i}/{len(papers)}] ✗ {paper.title[:60]}...")
        
        print(f"\n[Results]:")
        print(f"  ✓ Successfully included: {len(included)}")
        if failed:
            print(f"  ✗ Download failed: {len(failed)}")
        
        self.prisma_log.total_included = len(included)
        self.prisma_log.included_papers = included
        self.prisma_log.failed_downloads = failed
        
        return included
    
    
    def download_paper(self, paper: PaperCandidate) -> bool:
        """
        Download PDF for a paper.
        Returns: success boolean
        """
        if not paper.pdf_url:
            # Try to construct URL
            if paper.arxiv_id:
                paper.pdf_url = f"https://arxiv.org/pdf/{paper.arxiv_id}.pdf"
            elif paper.doi:
                # Try Unpaywall API or Sci-Hub (be careful with legality)
                pass
            else:
                return False
        
        # Double check pdf_url is not None
        if not paper.pdf_url:
            return False
        
        try:
            # Create safe filename
            safe_title = re.sub(r'[^\w\s-]', '', paper.title)[:100]
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            filename = f"{safe_title}_{paper.year}.pdf"
            
            output_path = Path("papers") / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download PDF
            response = requests.get(paper.pdf_url, timeout=60, stream=True)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                paper.pdf_path = str(output_path)
                return True
        
        except Exception as e:
            print(f"      Error downloading: {e}")
        
        return False
    
    
    # ========== PRISMA REPORTING ==========
    
    def save_candidates(self, papers: List[PaperCandidate], output_file: str):
        """Save paper candidates to JSON for review."""
        data = {
            "search_metadata": {
                "theme": self.contract.get('global_theme', ''),
                "search_date": self.prisma_log.search_date,
                "queries_used": self.prisma_log.queries,
                "databases": self.sources,
                "total_identified": self.prisma_log.total_identified,
                "duplicates_removed": self.prisma_log.duplicates_removed,
                "screened": self.prisma_log.records_screened,
                "eligible": len(papers)
            },
            "candidates": [paper.to_dict() for paper in papers]
        }
        
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n✓ Candidates saved: {output_file}")
    
    
    def generate_prisma_report(self) -> Dict:
        """
        Generate comprehensive PRISMA report.
        Returns report dictionary and saves artifacts.
        """
        print("\n" + "="*80)
        print("GENERATING PRISMA REPORT")
        print("="*80)
        
        report = {
            "identification": {
                "total_records": self.prisma_log.total_identified,
                "by_source": self.prisma_log.source_results,
                "search_date": self.prisma_log.search_date,
                "queries": self.prisma_log.queries
            },
            "screening": {
                "duplicates_removed": self.prisma_log.duplicates_removed,
                "records_screened": self.prisma_log.records_screened,
                "excluded_abstract": len(self.prisma_log.excluded_abstract),
                "exclusions_with_reasons": [
                    {
                        "title": paper.title,
                        "reason": paper.exclusion_reason,
                        "venue": paper.venue,
                        "year": paper.year
                    }
                    for paper in self.prisma_log.excluded_abstract
                ]
            },
            "eligibility": {
                "full_text_assessed": self.prisma_log.full_text_assessed,
                "excluded_full_text": len(self.prisma_log.excluded_full_text),
                "exclusions_with_reasons": [
                    {
                        "title": paper.title,
                        "reason": paper.exclusion_reason,
                        "venue": paper.venue,
                        "year": paper.year
                    }
                    for paper in self.prisma_log.excluded_full_text
                ]
            },
            "included": {
                "total_included": self.prisma_log.total_included
            }
        }
        
        # Generate flow diagram and include in report
        flow_diagram = self.generate_prisma_flow_diagram(report)
        report["flow_diagram"] = flow_diagram
        
        # Save detailed report with flow diagram included
        Path("artifacts/prisma").mkdir(parents=True, exist_ok=True)
        with open("artifacts/prisma/prisma_report.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✓ PRISMA report saved: artifacts/prisma/prisma_report.json")
        
        # Save excluded papers log
        self.save_excluded_papers()
        
        return report
    
    
    def generate_prisma_flow_diagram(self, report: Dict) -> str:
        """
        Generate PRISMA flow diagram in Mermaid format.
        Returns the diagram as a string.
        """
        n_identified = report['identification']['total_records']
        n_duplicates = report['screening']['duplicates_removed']
        n_screened = report['screening']['records_screened']
        n_excluded_screening = report['screening']['excluded_abstract']
        n_assessed = report['eligibility']['full_text_assessed']
        n_excluded_eligibility = report['eligibility']['excluded_full_text']
        n_included = report['included']['total_included']
        
        mermaid = f"""# PRISMA Flow Diagram

```mermaid
graph TD
    A[Identification<br/>Records identified: n={n_identified}] --> B[Duplicates removed: n={n_duplicates}]
    B --> C[Records screened<br/>n={n_screened}]
    C --> D[Records excluded<br/>n={n_excluded_screening}]
    C --> E[Full-text assessed<br/>n={n_assessed}]
    E --> F[Records excluded<br/>n={n_excluded_eligibility}]
    E --> G[Studies included<br/>n={n_included}]
    
    style A fill:#e1f5ff
    style C fill:#fff4e1
    style E fill:#ffe1f5
    style G fill:#e1ffe1
    style D fill:#ffe1e1
    style F fill:#ffe1e1
```

## Identification
- **Total records identified**: {n_identified}
- **Sources**: {', '.join(report['identification']['by_source'].keys())}
- **Search date**: {report['identification']['search_date'][:10]}

## Screening
- **Duplicates removed**: {n_duplicates}
- **Records screened**: {n_screened}
- **Excluded at screening**: {n_excluded_screening}

## Eligibility
- **Full-text assessed**: {n_assessed}
- **Excluded at eligibility**: {n_excluded_eligibility}

## Included
- **Studies included in review**: {n_included}
"""
        
        # Still save separate markdown file for convenience
        Path("artifacts/prisma").mkdir(parents=True, exist_ok=True)
        with open("artifacts/prisma/prisma_flow_diagram.md", 'w', encoding='utf-8') as f:
            f.write(mermaid)
        
        print(f"✓ PRISMA flow diagram saved: artifacts/prisma/prisma_flow_diagram.md")
        
        return mermaid
    
    
    def save_excluded_papers(self):
        """Save detailed log of excluded papers with reasons."""
        excluded_data = {
            "excluded_at_screening": [
                {
                    "title": p.title,
                    "venue": p.venue,
                    "year": p.year,
                    "reason": p.exclusion_reason
                }
                for p in self.prisma_log.excluded_abstract
            ],
            "excluded_at_eligibility": [
                {
                    "title": p.title,
                    "venue": p.venue,
                    "year": p.year,
                    "reason": p.exclusion_reason,
                    "citations": p.citation_count
                }
                for p in self.prisma_log.excluded_full_text
            ]
        }
        
        Path("artifacts/prisma").mkdir(parents=True, exist_ok=True)
        with open("artifacts/prisma/excluded_papers.json", 'w', encoding='utf-8') as f:
            json.dump(excluded_data, f, indent=2)
        
        print(f"✓ Excluded papers log saved: artifacts/prisma/excluded_papers.json")
