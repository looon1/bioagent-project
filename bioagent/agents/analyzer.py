"""
Task complexity analyzer for automatic multi-agent delegation.
"""

from typing import List
from bioagent.config import BioAgentConfig


class TaskComplexityAnalyzer:
    """Analyzes task complexity to determine if multi-agent is needed."""

    def __init__(self, config: BioAgentConfig):
        self.config = config

    def should_use_multi_agent(self, query: str) -> bool:
        """
        Determine if query requires multi-agent based on complexity.

        Returns True if complexity score >= threshold.
        """
        if not self.config.enable_multi_agent:
            return False
        if not self.config.multi_agent_auto_delegate:
            return False

        score = self._calculate_complexity_score(query)
        return score >= self.config.auto_delegate_threshold

    def _calculate_complexity_score(self, query: str) -> float:
        """
        Calculate complexity score based on multiple factors.

        Returns score between 0-1.
        """
        score = 0.0

        # Factor 1: Query length (longer = more complex)
        if len(query) > 200:
            score += 0.3
        elif len(query) > 100:
            score += 0.15

        # Factor 2: Multiple tool domains needed
        domains = self._detect_domains(query)
        if len(domains) >= 3:
            score += 0.5
        elif len(domains) >= 2:
            score += 0.3

        # Factor 3: Complexity keywords
        complexity_keywords = [
            "analyze", "compare", "integrate", "synthesize", "correlate",
            "combine", "multiple", "comprehensive", "then", "after", "and then",
            "分析", "比较", "整合", "综合", "关联",
            "组合", "多个", "综合", "然后", "之后", "接着"
        ]
        query_lower = query.lower()
        keyword_count = sum(1 for kw in complexity_keywords if kw in query_lower)
        if keyword_count >= 3:
            score += 0.4
        elif keyword_count >= 1:
            score += 0.2

        # Cap at 1.0
        return min(score, 1.0)

    def _detect_domains(self, query: str) -> List[str]:
        """Detect which tool domains are needed for the query."""
        query_lower = query.lower()
        domains = []

        # Database domain keywords (English and Chinese)
        db_keywords = [
            "protein", "gene", "uniprot", "pubmed", "literature", "research",
            "蛋白", "基因", "uniprot", "pubmed", "文献", "研究", "蛋白质"
        ]
        if any(kw in query_lower for kw in db_keywords):
            domains.append("database")

        # Analysis domain keywords (English and Chinese)
        analysis_keywords = [
            "analyze", "calculate", "process", "plot", "compute", "python",
            "分析", "计算", "处理", "绘图", "计算", "python"
        ]
        if any(kw in query_lower for kw in analysis_keywords):
            domains.append("analysis")

        # Files domain keywords (English and Chinese)
        file_keywords = [
            "file", "read", "write", "save", "export", "document",
            "文件", "读取", "写入", "保存", "导出", "文档"
        ]
        if any(kw in query_lower for kw in file_keywords):
            domains.append("files")

        return domains
