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
    Query gene information using EMBL-EBI's OLS4 API.

    Args:
        gene_symbol: Gene symbol (e.g., TP53, BRCA1)
        organism: Target organism (default: human)

    Returns:
        Dictionary with gene information including GO terms and descriptions
    """
    base_url = "https://www.ebi.ac.uk/ols4/api/search"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try both GO-specific and general search
            params = {
                "q": gene_symbol,
                "rows": 10
            }
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            results = []

            # Process all ontology results
            for doc in data.get("response", {}).get("docs", []):
                # Check if this document is related to our gene symbol
                label = doc.get("label", "").lower()
                gene_match = gene_symbol.lower() in label

                # Also check related synonyms
                if not gene_match and doc.get("related_synonyms"):
                    gene_match = any(
                        gene_symbol.lower() in syn.lower()
                        for syn in doc.get("related_synonyms", [])
                    )

                if gene_match:
                    # Extract gene information
                    description = doc.get("description", "")
                    if isinstance(description, list) and description:
                        description = description[0] if isinstance(description[0], str) else str(description[0])
                    elif not isinstance(description, str):
                        description = str(description) if description else ""

                    term = {
                        "id": doc.get("obo_id", doc.get("iri", "")),
                        "label": doc.get("label", ""),
                        "description": description,
                        "ontology": doc.get("ontology_name", "")
                    }
                    results.append(term)

            # Remove duplicates based on ID
            unique_results = []
            seen_ids = set()
            for term in results:
                if term["id"] not in seen_ids:
                    seen_ids.add(term["id"])
                    unique_results.append(term)

            
            # Filter to only show GO terms or gene-specific entries
            # Always return all found terms, as they're all relevant to the gene
            filtered_results = unique_results

            return {
                "gene": gene_symbol,
                "organism": organism,
                "go_terms": filtered_results,
                "count": len(filtered_results),
                "message": f"Found {len(filtered_results)} terms for {gene_symbol}" if filtered_results else f"No terms found for {gene_symbol}"
            }

    except Exception as e:
        return {
            "gene": gene_symbol,
            "organism": organism,
            "go_terms": [],
            "count": 0,
            "error": str(e)
        }


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
