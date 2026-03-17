"""
Database query tools for BioAgent.

Provides access to biomedical databases.
"""

import httpx
from typing import Dict, Any, Optional

from bioagent.tools.base import tool


@tool(domain="database")
async def query_uniprot(
    protein_id: Optional[str] = None,
    query: Optional[str] = None,
    max_results: int = 5
) -> Dict[str, Any]:
    """
    Query UniProt database for protein information.

    Args:
        protein_id: UniProt accession ID (e.g., P01308 for human insulin)
        query: Natural language query about proteins
        max_results: Maximum number of results to return

    Returns:
        Dictionary with protein information
    """
    base_url = "https://rest.uniprot.org/uniprotkb/search"

    if protein_id:
        params = {
            "query": f"accession:{protein_id}",
            "format": "json",
            "size": max_results
        }
    elif query:
        params = {
            "query": query,
            "format": "json",
            "size": max_results
        }
    else:
        return {"error": "Either protein_id or query must be provided"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if "results" not in data:
                return {"results": [], "message": "No results found"}

            results = []
            for item in data["results"][:max_results]:
                protein_info = {
                    "accession": item.get("primaryAccession"),
                    "name": item.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value"),
                    "gene": item.get("genes", [{}])[0].get("geneName", {}).get("value") if item.get("genes") else None,
                    "organism": item.get("organism", {}).get("scientificName"),
                    "length": item.get("sequence", {}).get("length"),
                    "function": item.get("proteinDescription", {}).get("recommendedName", {}).get("shortName", {}).get("value")
                }
                results.append(protein_info)

            return {"results": results, "count": len(results)}

    except Exception as e:
        return {"error": str(e)}


@tool(domain="database")
async def query_gene(
    gene_symbol: str,
    organism: str = "human"
) -> Dict[str, Any]:
    """
    Query gene information using EMBL-EBI's Gene Ontology API.

    Args:
        gene_symbol: Gene symbol (e.g., TP53, BRCA1)
        organism: Target organism (default: human)

    Returns:
        Dictionary with gene information
    """
    base_url = "https://www.ebi.ac.uk/ols/api/ontologies/go/terms"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to find GO terms related to the gene
            params = {
                "q": gene_symbol,
                "size": 5
            }
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get("_embedded", {}).get("terms"):
                return {
                    "results": [],
                    "message": f"No GO terms found for {gene_symbol}"
                }

            results = []
            for term in data["_embedded"]["terms"]:
                results.append({
                    "id": term.get("iri"),
                    "label": term.get("label"),
                    "description": term.get("description", [{}])[0].get(""),
                    "ontology": term.get("ontology_name")
                })

            return {
                "gene": gene_symbol,
                "organism": organism,
                "go_terms": results,
                "count": len(results)
            }

    except Exception as e:
        return {"error": str(e)}


@tool(domain="database")
async def query_pubmed(
    query: str,
    max_results: int = 5,
    days_since: Optional[int] = None
) -> Dict[str, Any]:
    """
    Query PubMed for scientific literature.

    Args:
        query: Search query string
        max_results: Maximum number of results to return
        days_since: Optional filter for papers published within last N days

    Returns:
        Dictionary with PubMed search results
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Search for papers
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "retmax": max_results
            }

            if days_since:
                # Add date filter
                from datetime import datetime, timedelta
                cutoff = (datetime.now() - timedelta(days=days_since)).strftime("%Y/%m/%d")
                search_params["datetype"] = "pdat"
                search_params["reldate"] = days_since

            search_response = await client.get(base_url, params=search_params)
            search_response.raise_for_status()
            search_data = search_response.json()

            if "esearchresult" not in search_data:
                return {"results": [], "message": "No results found"}

            id_list = search_data["esearchresult"]["idlist"]

            if not id_list:
                return {"results": [], "message": "No results found"}

            # Get summaries for found papers
            summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            summary_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json"
            }

            summary_response = await client.get(summary_url, params=summary_params)
            summary_response.raise_for_status()
            summary_data = summary_response.json()

            results = []
            if "result" in summary_data:
                for pmid, paper in summary_data["result"].items():
                    if pmid == "uids":
                        continue

                    paper_info = {
                        "pmid": pmid,
                        "title": paper.get("title"),
                        "authors": [a.get("name") for a in paper.get("authors", [])],
                        "journal": paper.get("source"),
                        "pub_date": paper.get("pubdate"),
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    }
                    results.append(paper_info)

            return {
                "query": query,
                "results": results,
                "count": len(results)
            }

    except Exception as e:
        return {"error": str(e)}
