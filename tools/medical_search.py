"""
Medical information search tool using DuckDuckGo.

Could use PubMed API here but DDG is good enough for a demo and requires no API key.
The domain filtering is the important part — without it, you get WebMD forums and
Reddit threads, which are not great for clinical decision support.

PubMed API option for future: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

# domains that are generally reliable for medical information
# WHO and CDC are authoritative for guidelines
# NIH / PubMed for research
# Mayo / Healthline / MedlinePlus for patient-readable clinical summaries
TRUSTED_DOMAINS = {
    "nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "mayoclinic.org",
    "medlineplus.gov",
    "webmd.com",
    "healthline.com",
    "who.int",
    "cdc.gov",
    "uptodate.com",
    "medscape.com",
    "aafp.org",
    "jamanetwork.com",
    "nejm.org",
    "bmj.com",
    "thelancet.com",
}


def _is_trusted(url: str) -> bool:
    try:
        domain = urlparse(url).netloc.lower().lstrip("www.")
        return any(domain == d or domain.endswith("." + d) for d in TRUSTED_DOMAINS)
    except Exception:
        return False


def search_medical_info(query: str, max_results: int = 5) -> str:
    """
    Search DuckDuckGo for medical information and filter to trusted domains.
    Returns a formatted string with titles, URLs, and snippets.
    """
    try:
        medical_query = f"{query} site:nih.gov OR site:mayoclinic.org OR site:medlineplus.gov OR site:cdc.gov OR site:who.int"

        results = []
        with DDGS() as ddgs:
            raw = list(ddgs.text(medical_query, max_results=max_results * 2))

        for r in raw:
            url = r.get("href", "")
            if _is_trusted(url):
                results.append(r)
            if len(results) >= max_results:
                break

        # if domain-filtered results are sparse, fall back to unfiltered but note it
        if len(results) < 2:
            logger.warning(f"Few trusted results for: {query!r}. Falling back to general results.")
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No search results found for: {query}"

        formatted = []
        for i, r in enumerate(results[:max_results], 1):
            title = r.get("title", "No title")
            url = r.get("href", "")
            body = r.get("body", "")
            # truncate long snippets — model context budget matters
            snippet = body[:400] + "..." if len(body) > 400 else body
            formatted.append(f"[{i}] {title}\nURL: {url}\nSummary: {snippet}")

        return "\n\n".join(formatted)

    except Exception as e:
        logger.error(f"Search failed for {query!r}: {e}")
        return f"Search unavailable: {str(e)}"
