"""
Hybrid evaluator for evolved code.

Combines functional test execution with LLM-based quality assessment.
"""

import asyncio
import hashlib
import re
import sys
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from bioagent.evolution.models import EvolvedCode, FitnessScore
    from bioagent.llm import LLMProvider
    from bioagent.observability import Logger


class HybridEvaluator:
    """
    Evaluates evolved code using hybrid approach:
    1. Functional tests - Execute test cases
    2. LLM feedback - Assess code quality and style
    """

    def __init__(self, llm_provider: "LLMProvider", logger: "Logger"):
        """
        Initialize the evaluator.

        Args:
            llm_provider: LLM provider for quality assessment
            logger: Logger for recording evaluation events
        """
        self.llm = llm_provider
        self.logger = logger
        self._cache: Dict[str, "FitnessScore"] = {}

    async def evaluate(
        self,
        code: "EvolvedCode",
        test_cases: List[Dict[str, Any]],
        existing_behaviors: Optional[List[str]] = None
    ) -> "FitnessScore":
        """
        Evaluate code using hybrid approach.

        Args:
            code: Evolved code to evaluate
            test_cases: List of test cases to execute
            existing_behaviors: List of existing behavior descriptions for diversity bonus

        Returns:
            Composite fitness score
        """
        # Check cache
        code_hash = self._hash_code(code.code)
        if code_hash in self._cache:
            return self._cache[code_hash]

        self.logger.info(
            "Evaluating evolved code",
            code_id=code.id,
            generation=code.generation,
            code_hash=code_hash[:8],
        )

        # Run functional tests
        functional_score = await self._run_functional_tests(code.code, test_cases)
        code.test_results = functional_score["details"]

        # Get LLM feedback
        llm_score, feedback = await self._get_llm_feedback(code.code, code.behavior_desc)
        code.llm_feedback = feedback

        # Calculate diversity bonus
        diversity_bonus = self._calculate_diversity_bonus(
            code.behavior_desc,
            existing_behaviors or []
        )

        # Create composite score
        from bioagent.evolution.models import FitnessScore

        fitness = FitnessScore(
            functional=functional_score["score"],
            llm_quality=llm_score,
            diversity_bonus=diversity_bonus,
        )

        # Cache and return
        self._cache[code_hash] = fitness
        self.logger.info(
            "Evaluation complete",
            code_id=code.id,
            functional=functional_score["score"],
            llm_quality=llm_score,
            diversity_bonus=diversity_bonus,
            combined=fitness.combined,
        )

        return fitness

    async def _run_functional_tests(
        self,
        code: str,
        test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute functional test cases.

        Args:
            code: Source code to test
            test_cases: List of test case dictionaries

        Returns:
            Dictionary with score and details
        """
        if not test_cases:
            return {"score": 0.5, "details": []}  # Default score if no tests

        results = []
        passed = 0

        for test_case in test_cases:
            try:
                result = await self._execute_test(code, test_case)
                results.append(result)
                if result["passed"]:
                    passed += 1
            except Exception as e:
                self.logger.warning(f"Test execution failed: {e}")
                results.append({
                    "test": test_case,
                    "passed": False,
                    "error": str(e),
                })

        score = passed / len(test_cases) if test_cases else 0.0

        return {
            "score": score,
            "details": results,
            "passed": passed,
            "total": len(test_cases),
        }

    async def _execute_test(
        self,
        code: str,
        test_case: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single test case.

        Args:
            code: Source code
            test_case: Test case with inputs and expected outputs

        Returns:
            Test result dictionary
        """
        # Create namespace for execution
        namespace = {}

        try:
            # Execute the code
            exec(code, namespace)

            # Execute test input
            input_code = test_case.get("input", "")
            expected_output = test_case.get("expected")

            # Capture output
            old_stdout = sys.stdout
            sys.stdout = StringIO()

            # Execute input in namespace
            exec_result = exec(input_code, namespace)

            # Get output
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            # Check result
            if "result" in namespace:
                actual = namespace["result"]
                passed = actual == expected_output
            else:
                passed = str(output).strip() == str(expected_output).strip()

            return {
                "test": test_case,
                "passed": passed,
                "actual": actual if "result" in namespace else output,
                "expected": expected_output,
            }

        except Exception as e:
            return {
                "test": test_case,
                "passed": False,
                "error": str(e),
            }

    async def _get_llm_feedback(
        self,
        code: str,
        behavior_desc: str
    ) -> Tuple[float, str]:
        """
        Get LLM feedback on code quality.

        Args:
            code: Source code to evaluate
            behavior_desc: Description of expected behavior

        Returns:
            Tuple of (score, feedback_text)
        """
        prompt = f"""Evaluate the following Python code for quality, readability, and correctness.

Code Behavior: {behavior_desc}

Code:
```python
{code}
```

Evaluate on the following dimensions (0-1 scale for each):
1. Correctness: Does the code appear to correctly implement the behavior?
2. Readability: Is the code clear, well-structured, and easy to understand?
3. Efficiency: Is the code reasonably efficient for the task?
4. Safety: Does the code follow best practices (e.g., error handling, input validation)?

Provide your evaluation in JSON format:
{{
    "correctness": <float>,
    "readability": <float>,
    "efficiency": <float>,
    "safety": <float>,
    "feedback": "<brief explanation of your assessment>"
}}
"""

        try:
            response = await self.llm.call(
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract JSON from response
            content = response.content or "{}"

            # Try to parse JSON
            try:
                import json
                # Find JSON in response
                json_match = re.search(r'\{[^}]*\}', content)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    data = json.loads(content)

                correctness = data.get("correctness", 0.5)
                readability = data.get("readability", 0.5)
                efficiency = data.get("efficiency", 0.5)
                safety = data.get("safety", 0.5)
                feedback = data.get("feedback", "")

                # Average the scores
                score = (correctness + readability + efficiency + safety) / 4.0
                return min(score, 1.0), feedback

            except (json.JSONDecodeError, KeyError):
                # Fallback: parse numeric values from text
                scores = re.findall(r'\d+\.?\d*', content)
                if scores:
                    return min(float(scores[0]) / 10.0, 1.0), content[:200]
                return 0.5, content[:200]

        except Exception as e:
            self.logger.warning(f"LLM feedback failed: {e}")
            return 0.5, "Could not get LLM feedback"

    def _calculate_diversity_bonus(
        self,
        behavior_desc: str,
        existing_behaviors: List[str]
    ) -> float:
        """
        Calculate diversity bonus for novel behaviors.

        Args:
            behavior_desc: Description of this code's behavior
            existing_behaviors: List of existing behavior descriptions

        Returns:
            Diversity bonus (0-1)
        """
        if not existing_behaviors:
            return 1.0  # First behavior gets max bonus

        # Simple similarity check
        desc_words = set(behavior_desc.lower().split())

        similarities = []
        for existing in existing_behaviors:
            existing_words = set(existing.lower().split())
            intersection = desc_words & existing_words
            union = desc_words | existing_words
            if union:
                similarity = len(intersection) / len(union)
                similarities.append(similarity)

        if not similarities:
            return 1.0

        # Bonus inversely proportional to max similarity
        max_similarity = max(similarities)
        return 1.0 - max_similarity

    def _hash_code(self, code: str) -> str:
        """
        Hash code for caching.

        Args:
            code: Source code

        Returns:
            Hash string
        """
        return hashlib.md5(code.encode()).hexdigest()

    def clear_cache(self) -> None:
        """Clear the evaluation cache."""
        self._cache.clear()
        self.logger.debug("Evaluation cache cleared")

    def cache_size(self) -> int:
        """Get cache size."""
        return len(self._cache)


def create_default_test_cases(tool_name: str) -> List[Dict[str, Any]]:
    """
    Create default test cases for common tool patterns.

    Args:
        tool_name: Name of the tool

    Returns:
        List of test case dictionaries
    """
    # Default test patterns for different tool types
    patterns = {
        "query_uniprot": [
            {"input": 'query_uniprot("TP53")', "expected": {"protein": "TP53"}},
            {"input": 'query_uniprot("INS")', "expected": {"protein": "INS"}},
        ],
        "query_gene": [
            {"input": 'query_gene("TP53")', "expected": {"gene": "TP53"}},
            {"input": 'query_gene("BRCA1")', "expected": {"gene": "BRCA1"}},
        ],
        "analyze_data": [
            {"input": 'analyze_data([1, 2, 3])', "expected": {"mean": 2.0}},
            {"input": 'analyze_data([10, 20, 30])', "expected": {"mean": 20.0}},
        ],
    }

    return patterns.get(tool_name, [
        {"input": "result = execute()", "expected": {"status": "success"}},
    ])
