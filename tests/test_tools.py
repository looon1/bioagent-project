#!/usr/bin/env python3
"""
Tests for BioAgent tools.
"""

import pytest
import asyncio
from bioagent.tools.registry import ToolRegistry
from bioagent.tools.core.database import query_uniprot, query_gene, query_pubmed


@pytest.mark.asyncio
async def test_tool_registry():
    """Test tool registry functionality."""
    registry = ToolRegistry()
    registry.register(query_uniprot)
    registry.register(query_gene)
    registry.register(query_pubmed)

    assert len(registry) == 3
    assert "query_uniprot" in registry.list_tool_names()
    assert "query_gene" in registry.list_tool_names()
    assert "query_pubmed" in registry.list_tool_names()


@pytest.mark.asyncio
async def test_uniprot_tool():
    """Test UniProt query tool."""
    registry = ToolRegistry()
    registry.register(query_uniprot)

    result = await registry.execute("query_uniprot", {"query": "insulin"})
    assert isinstance(result, dict)
    assert "results" in result
    assert isinstance(result["results"], list)


@pytest.mark.asyncio
async def test_tool_info():
    """Test tool information."""
    from bioagent.tools.base import get_tool_info

    info = get_tool_info(query_uniprot)
    assert info is not None
    assert info.name == "query_uniprot"
    assert info.domain == "database"
    assert info.description is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
