"""
Academic Tools - Investigador académico élite
Busca en arXiv, PubMed, CrossRef, Semantic Scholar y genera citas BibTeX/APA/MLA/Chicago/IEEE.
"""
import json
import re
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

try:
    import feedparser
except ImportError:
    feedparser = None


class AcademicTools:
    """Herramientas para investigación académica profesional."""

    TIMEOUT = 20
    HEADERS = {"User-Agent": "Automyx-Academic/2.5 (mailto:research@nexora.tech)"}

    # ---------- ARXIV ----------
    @staticmethod
    def search_arxiv(query: str, max_results: int = 10) -> Dict[str, Any]:
        """Busca papers en arXiv. Retorna lista con title, authors, abstract, pdf_url, id."""
        if requests is None:
            return {"error": "Falta instalar 'requests' (pip install requests)"}
        try:
            url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending",
            }
            r = requests.get(url, params=params, timeout=AcademicTools.TIMEOUT, headers=AcademicTools.HEADERS)
            r.raise_for_status()
            papers = []
            if feedparser:
                feed = feedparser.parse(r.text)
                for entry in feed.entries:
                    papers.append({
                        "id": entry.get("id", "").split("/")[-1],
                        "title": entry.get("title", "").replace("\n", " ").strip(),
                        "authors": [a.get("name", "") for a in entry.get("authors", [])],
                        "abstract": entry.get("summary", "").replace("\n", " ").strip(),
                        "published": entry.get("published", ""),
                        "pdf_url": next((l["href"] for l in entry.get("links", []) if l.get("type") == "application/pdf"), ""),
                        "categories": [t["term"] for t in entry.get("tags", [])],
                        "source": "arxiv",
                    })
            else:
                # fallback regex parser
                for m in re.finditer(r"<entry>(.*?)</entry>", r.text, re.S):
                    block = m.group(1)
                    title = re.search(r"<title>(.*?)</title>", block, re.S)
                    summary = re.search(r"<summary>(.*?)</summary>", block, re.S)
                    pid = re.search(r"<id>(.*?)</id>", block, re.S)
                    papers.append({
                        "id": (pid.group(1) if pid else "").split("/")[-1],
                        "title": (title.group(1) if title else "").strip(),
                        "abstract": (summary.group(1) if summary else "").strip(),
                        "source": "arxiv",
                    })
            return {"count": len(papers), "papers": papers}
        except Exception as e:
            return {"error": f"Error buscando en arXiv: {e}"}

    # ---------- PUBMED ----------
    @staticmethod
    def search_pubmed(query: str, max_results: int = 10) -> Dict[str, Any]:
        """Busca papers en PubMed (medicina/biología) vía E-utilities."""
        if requests is None:
            return {"error": "Falta instalar 'requests'"}
        try:
            base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
            search_url = f"{base}/esearch.fcgi"
            r = requests.get(search_url, params={
                "db": "pubmed", "term": query, "retmax": max_results, "retmode": "json", "sort": "relevance"
            }, timeout=AcademicTools.TIMEOUT, headers=AcademicTools.HEADERS)
            r.raise_for_status()
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return {"count": 0, "papers": []}

            summary_url = f"{base}/esummary.fcgi"
            s = requests.get(summary_url, params={
                "db": "pubmed", "id": ",".join(ids), "retmode": "json"
            }, timeout=AcademicTools.TIMEOUT, headers=AcademicTools.HEADERS)
            s.raise_for_status()
            data = s.json().get("result", {})

            papers = []
            for pid in ids:
                item = data.get(pid, {})
                if not item:
                    continue
                papers.append({
                    "id": pid,
                    "title": item.get("title", ""),
                    "authors": [a.get("name", "") for a in item.get("authors", [])],
                    "journal": item.get("fulljournalname", ""),
                    "published": item.get("pubdate", ""),
                    "doi": next((a.get("value") for a in item.get("articleids", []) if a.get("idtype") == "doi"), ""),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                    "source": "pubmed",
                })
            return {"count": len(papers), "papers": papers}
        except Exception as e:
            return {"error": f"Error buscando en PubMed: {e}"}

    # ---------- CROSSREF ----------
    @staticmethod
    def search_crossref(query: str, max_results: int = 10) -> Dict[str, Any]:
        """Busca papers en CrossRef (DOI database, cualquier disciplina)."""
        if requests is None:
            return {"error": "Falta instalar 'requests'"}
        try:
            r = requests.get("https://api.crossref.org/works", params={
                "query": query, "rows": max_results, "select": "DOI,title,author,abstract,published,container-title,URL"
            }, timeout=AcademicTools.TIMEOUT, headers=AcademicTools.HEADERS)
            r.raise_for_status()
            items = r.json().get("message", {}).get("items", [])
            papers = []
            for it in items:
                papers.append({
                    "doi": it.get("DOI", ""),
                    "title": (it.get("title", [""]) or [""])[0],
                    "authors": [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in it.get("author", [])],
                    "journal": (it.get("container-title", [""]) or [""])[0],
                    "published": "-".join(str(p) for p in (it.get("published", {}).get("date-parts", [[None]])[0] or [])),
                    "abstract": re.sub(r"<[^>]+>", "", it.get("abstract", "")),
                    "url": it.get("URL", ""),
                    "source": "crossref",
                })
            return {"count": len(papers), "papers": papers}
        except Exception as e:
            return {"error": f"Error buscando en CrossRef: {e}"}

    # ---------- SEMANTIC SCHOLAR ----------
    @staticmethod
    def search_semantic_scholar(query: str, max_results: int = 10) -> Dict[str, Any]:
        """Busca en Semantic Scholar con grafo de citas."""
        if requests is None:
            return {"error": "Falta instalar 'requests'"}
        try:
            r = requests.get("https://api.semanticscholar.org/graph/v1/paper/search", params={
                "query": query, "limit": max_results,
                "fields": "title,authors,abstract,year,citationCount,referenceCount,openAccessPdf,externalIds"
            }, timeout=AcademicTools.TIMEOUT, headers=AcademicTools.HEADERS)
            r.raise_for_status()
            items = r.json().get("data", [])
            papers = []
            for it in items:
                papers.append({
                    "id": it.get("paperId", ""),
                    "title": it.get("title", ""),
                    "authors": [a.get("name", "") for a in it.get("authors", [])],
                    "abstract": it.get("abstract", ""),
                    "year": it.get("year", ""),
                    "citations": it.get("citationCount", 0),
                    "references": it.get("referenceCount", 0),
                    "doi": (it.get("externalIds") or {}).get("DOI", ""),
                    "pdf_url": (it.get("openAccessPdf") or {}).get("url", ""),
                    "source": "semantic_scholar",
                })
            return {"count": len(papers), "papers": papers}
        except Exception as e:
            return {"error": f"Error buscando en Semantic Scholar: {e}"}

    # ---------- ABSTRACT FETCH ----------
    @staticmethod
    def fetch_abstract(paper_id: str, source: str = "arxiv") -> Dict[str, Any]:
        """Obtiene el abstract completo de un paper por ID."""
        source = source.lower()
        if source == "arxiv":
            res = AcademicTools.search_arxiv(f"id:{paper_id}", max_results=1)
        elif source == "pubmed":
            res = AcademicTools.search_pubmed(paper_id, max_results=1)
        elif source == "crossref":
            res = AcademicTools.search_crossref(paper_id, max_results=1)
        else:
            res = AcademicTools.search_semantic_scholar(paper_id, max_results=1)
        if "papers" in res and res["papers"]:
            return res["papers"][0]
        return {"error": f"Paper {paper_id} no encontrado en {source}"}

    # ---------- CITATIONS ----------
    @staticmethod
    def generate_citation(paper: Dict[str, Any], style: str = "apa") -> str:
        """Genera cita en estilos: apa, mla, chicago, ieee, bibtex."""
        style = style.lower()
        authors = paper.get("authors", []) or []
        title = paper.get("title", "Untitled")
        year = paper.get("year") or (paper.get("published", "")[:4] if paper.get("published") else "n.d.")
        journal = paper.get("journal") or paper.get("source", "").title()
        doi = paper.get("doi", "")
        url = paper.get("url") or paper.get("pdf_url", "")

        if style == "apa":
            au = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
            return f"{au} ({year}). {title}. {journal}. {('https://doi.org/' + doi) if doi else url}"
        if style == "mla":
            au = authors[0] if authors else "Anon."
            etal = " et al." if len(authors) > 1 else ""
            return f'{au}{etal}. "{title}." {journal}, {year}. {url}'
        if style == "chicago":
            au = ", ".join(authors[:3])
            return f'{au}. "{title}." {journal} ({year}). {url}'
        if style == "ieee":
            au = ", ".join(authors[:3])
            return f'{au}, "{title}," {journal}, {year}. [Online]. Available: {url}'
        if style == "bibtex":
            key = re.sub(r"\W+", "", (authors[0] if authors else "anon").split()[-1].lower()) + str(year)
            au = " and ".join(authors)
            return (f"@article{{{key},\n"
                    f"  title = {{{title}}},\n"
                    f"  author = {{{au}}},\n"
                    f"  journal = {{{journal}}},\n"
                    f"  year = {{{year}}},\n"
                    f"  doi = {{{doi}}},\n"
                    f"  url = {{{url}}}\n"
                    f"}}")
        return f"Estilo '{style}' no soportado. Usa: apa, mla, chicago, ieee, bibtex."

    # ---------- LITERATURE REVIEW ----------
    @staticmethod
    def generate_literature_review(topic: str, sources: List[str] = None, max_per_source: int = 5) -> Dict[str, Any]:
        """Genera una revisión de literatura combinando múltiples fuentes."""
        sources = sources or ["arxiv", "semantic_scholar", "crossref"]
        all_papers = []
        for s in sources:
            if s == "arxiv":
                r = AcademicTools.search_arxiv(topic, max_per_source)
            elif s == "pubmed":
                r = AcademicTools.search_pubmed(topic, max_per_source)
            elif s == "crossref":
                r = AcademicTools.search_crossref(topic, max_per_source)
            elif s == "semantic_scholar":
                r = AcademicTools.search_semantic_scholar(topic, max_per_source)
            else:
                continue
            if "papers" in r:
                all_papers.extend(r["papers"])

        md = [f"# Revisión de Literatura: {topic}",
              f"\n_Generado por Automyx el {datetime.now().strftime('%Y-%m-%d %H:%M')}._\n",
              f"\n## Resumen Ejecutivo\nSe analizaron {len(all_papers)} publicaciones de las fuentes: {', '.join(sources)}.\n",
              "\n## Papers Relevantes\n"]
        bib = []
        for i, p in enumerate(all_papers, 1):
            md.append(f"### {i}. {p.get('title', 'Sin título')}")
            md.append(f"- **Autores:** {', '.join(p.get('authors', []) or ['N/D'])}")
            md.append(f"- **Año:** {p.get('year') or p.get('published', 'N/D')}")
            md.append(f"- **Fuente:** {p.get('source', 'N/D').title()}")
            if p.get("abstract"):
                md.append(f"- **Abstract:** {p['abstract'][:400]}{'...' if len(p['abstract']) > 400 else ''}")
            md.append(f"- **URL:** {p.get('url') or p.get('pdf_url', 'N/D')}\n")
            bib.append(AcademicTools.generate_citation(p, "bibtex"))

        md.append("\n## Referencias (BibTeX)\n```bibtex\n" + "\n\n".join(bib) + "\n```")
        return {"markdown": "\n".join(md), "papers_count": len(all_papers), "bibtex": "\n\n".join(bib)}
