"""
Mutation strategies for code evolution.

Implements different approaches to generating code variants.
"""

import random
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from bioagent.evolution.models import EvolvedCode, MutationType
    from bioagent.llm import LLMProvider
    from bioagent.observability import Logger


class MutationStrategy(ABC):
    """
    Abstract base class for mutation strategies.
    """

    @abstractmethod
    async def mutate(
        self,
        parent: "EvolvedCode",
        generation: int,
        mutation_rate: float = 0.3
    ) -> "EvolvedCode":
        """
        Generate a mutated variant of parent code.

        Args:
            parent: Parent evolved code
            generation: Current generation number
            mutation_rate: Probability of mutation (not used by all strategies)

        Returns:
            New evolved code with mutation applied
        """
        pass

    @abstractmethod
    def get_type(self) -> "MutationType":
        """Get the mutation type."""
        pass


class AnalyzerMutatorStrategy(MutationStrategy):
    """
    Two-stage mutation strategy:
    1. Analyzer: LLM analyzes code and identifies improvement opportunities
    2. Mutator: LLM generates code based on analyzer recommendations
    """

    def __init__(self, llm_provider: "LLMProvider", logger: "Logger"):
        """
        Initialize the strategy.

        Args:
            llm_provider: LLM provider for code generation
            logger: Logger for recording events
        """
        self.llm = llm_provider
        self.logger = logger

    async def mutate(
        self,
        parent: "EvolvedCode",
        generation: int,
        mutation_rate: float = 0.3
    ) -> "EvolvedCode":
        """
        Apply analyzer-mutator mutation.

        Args:
            parent: Parent evolved code
            generation: Current generation number
            mutation_rate: Mutation probability

        Returns:
            Mutated evolved code
        """
        from bioagent.evolution.models import EvolvedCode, compute_behavior_vector

        # Stage 1: Analyze parent code
        analysis = await self._analyze(parent.code, parent.behavior_desc)

        # Stage 2: Generate mutated code based on analysis
        mutated_code = await self._mutate(parent.code, analysis, mutation_rate)

        # Compute behavior for new code
        behavior_desc = self._extract_behavior_desc(mutated_code, parent.behavior_desc)
        behavior_vector = compute_behavior_vector(mutated_code, behavior_desc)

        # Create evolved code
        return EvolvedCode(
            code=mutated_code,
            generation=generation,
            parent_ids=[parent.id],
            mutation_type=self.get_type(),
            behavior_desc=behavior_desc,
            behavior_vector=behavior_vector,
        )

    async def _analyze(self, code: str, behavior_desc: str) -> str:
        """
        Analyze code and identify improvement opportunities.

        Args:
            code: Source code to analyze
            behavior_desc: Description of expected behavior

        Returns:
            Analysis text with recommendations
        """
        prompt = f"""Analyze the following Python code and identify specific improvement opportunities.

Expected behavior: {behavior_desc}

Code:
```python
{code}
```

Identify:
1. Logic issues or potential bugs
2. Performance optimizations
3. Code structure improvements
4. Missing error handling

Provide specific, actionable recommendations for improvement.
"""

        response = await self.llm.call(
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content or "No specific issues identified."

    async def _mutate(
        self,
        code: str,
        analysis: str,
        mutation_rate: float
    ) -> str:
        """
        Generate mutated code based on analysis.

        Args:
            code: Original code
            analysis: Analysis with recommendations
            mutation_rate: Mutation probability

        Returns:
            Mutated code string
        """
        mutation_level = "minor" if mutation_rate < 0.3 else "major"

        prompt = f"""Improve the following Python code based on the analysis.

Original code:
```python
{code}
```

Analysis:
{analysis}

Generate {mutation_level} improvements (mutation rate: {mutation_rate}).
- Focus on correctness and functionality first
- Then optimize for readability and efficiency
- Keep the function signature and core behavior intact
- Return only the improved code, no explanations

Return the complete, runnable Python code:
"""

        response = await self.llm.call(
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract code from response
        code_match = re.search(r'```python\n(.*?)```', response.content or "", re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        return response.content or code

    def _extract_behavior_desc(
        self,
        mutated_code: str,
        parent_desc: str
    ) -> str:
        """Extract behavior description from mutated code."""
        # For now, keep parent description
        # Could enhance with LLM-based description extraction
        return parent_desc

    def get_type(self) -> "MutationType":
        """Get mutation type."""
        from bioagent.evolution.models import MutationType
        return MutationType.ANALYZER_MUTATOR


class CodeRewriterStrategy(MutationStrategy):
    """
    Direct LLM code rewriting strategy.

    LLM directly rewrites the code with specific mutation guidance.
    """

    def __init__(self, llm_provider: "LLMProvider", logger: "Logger"):
        """
        Initialize the strategy.

        Args:
            llm_provider: LLM provider for code generation
            logger: Logger for recording events
        """
        self.llm = llm_provider
        self.logger = logger

    async def mutate(
        self,
        parent: "EvolvedCode",
        generation: int,
        mutation_rate: float = 0.3
    ) -> "EvolvedCode":
        """
        Apply direct code rewriting mutation.

        Args:
            parent: Parent evolved code
            generation: Current generation number
            mutation_rate: Mutation probability

        Returns:
            Mutated evolved code
        """
        from bioagent.evolution.models import EvolvedCode, compute_behavior_vector

        # Generate mutated code
        mutated_code = await self._rewrite(parent.code, parent.behavior_desc, mutation_rate)

        # Compute behavior for new code
        behavior_desc = parent.behavior_desc
        behavior_vector = compute_behavior_vector(mutated_code, behavior_desc)

        # Create evolved code
        return EvolvedCode(
            code=mutated_code,
            generation=generation,
            parent_ids=[parent.id],
            mutation_type=self.get_type(),
            behavior_desc=behavior_desc,
            behavior_vector=behavior_vector,
        )

    async def _rewrite(
        self,
        code: str,
        behavior_desc: str,
        mutation_rate: float
    ) -> str:
        """
        Rewrite code with mutation guidance.

        Args:
            code: Original code
            behavior_desc: Description of expected behavior
            mutation_rate: Mutation probability

        Returns:
            Rewritten code string
        """
        # Choose rewrite type based on mutation rate
        rewrite_types = [
            "optimize for efficiency",
            "improve readability and documentation",
            "add error handling",
            "refactor structure",
            "optimize imports",
        ]

        if mutation_rate < 0.3:
            rewrite_type = random.choice(rewrite_types[:2])
        else:
            rewrite_type = random.choice(rewrite_types)

        prompt = f"""Rewrite the following Python code to {rewrite_type}.

Expected behavior: {behavior_desc}

Original code:
```python
{code}
```

Apply the following rewrite type: {rewrite_type}

Requirements:
- Maintain the same function signature
- Keep the core functionality intact
- Make only focused improvements related to {rewrite_type}
- Return only the rewritten code, no explanations

Return the complete, runnable Python code:
"""

        response = await self.llm.call(
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract code from response
        code_match = re.search(r'```python\n(.*?)```', response.content or "", re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        return response.content or code

    def get_type(self) -> "MutationType":
        """Get mutation type."""
        from bioagent.evolution.models import MutationType
        return MutationType.CODE_REWRITER


class ParameterTunerStrategy(MutationStrategy):
    """
    Parameter optimization mutation strategy.

    Focuses on tuning hyperparameters and configuration values in code.
    """

    def __init__(self, llm_provider: "LLMProvider", logger: "Logger"):
        """
        Initialize the strategy.

        Args:
            llm_provider: LLM provider for code generation
            logger: Logger for recording events
        """
        self.llm = llm_provider
        self.logger = logger

    async def mutate(
        self,
        parent: "EvolvedCode",
        generation: int,
        mutation_rate: float = 0.3
    ) -> "EvolvedCode":
        """
        Apply parameter tuning mutation.

        Args:
            parent: Parent evolved code
            generation: Current generation number
            mutation_rate: Mutation probability

        Returns:
            Mutated evolved code
        """
        from bioagent.evolution.models import EvolvedCode, compute_behavior_vector

        # Find tunable parameters
        parameters = self._find_parameters(parent.code)

        if not parameters:
            # Fall back to rewriter if no parameters found
            self.logger.warning("No parameters found, falling back to rewriter strategy")
            fallback = CodeRewriterStrategy(self.llm, self.logger)
            return await fallback.mutate(parent, generation, mutation_rate)

        # Tune parameters
        mutated_code = await self._tune_parameters(parent.code, parameters, mutation_rate)

        # Compute behavior for new code
        behavior_desc = parent.behavior_desc
        behavior_vector = compute_behavior_vector(mutated_code, behavior_desc)

        # Create evolved code
        return EvolvedCode(
            code=mutated_code,
            generation=generation,
            parent_ids=[parent.id],
            mutation_type=self.get_type(),
            behavior_desc=behavior_desc,
            behavior_vector=behavior_vector,
        )

    def _find_parameters(self, code: str) -> List[Dict[str, any]]:
        """
        Find tunable parameters in code.

        Args:
            code: Source code

        Returns:
            List of parameter dictionaries
        """
        parameters = []

        # Find numeric constants that look like parameters
        # Pattern: numbers that are part of assignments or function calls
        number_pattern = r'(\w+)\s*=\s*(\d+\.?\d*|\d+\.\d+)'
        for match in re.finditer(number_pattern, code):
            var_name = match.group(1)
            value = match.group(2)

            # Skip common non-tunable variables
            skip_vars = ["result", "output", "data", "temp", "i", "j", "k", "x", "y"]
            if var_name.lower() not in skip_vars:
                parameters.append({
                    "name": var_name,
                    "value": value,
                    "type": "numeric",
                })

        return parameters

    async def _tune_parameters(
        self,
        code: str,
        parameters: List[Dict[str, any]],
        mutation_rate: float
    ) -> str:
        """
        Tune parameters in code.

        Args:
            code: Source code
            parameters: List of tunable parameters
            mutation_rate: Mutation probability

        Returns:
            Code with tuned parameters
        """
        # Select subset of parameters to tune based on mutation rate
        num_to_tune = max(1, int(len(parameters) * mutation_rate))
        params_to_tune = random.sample(parameters, min(num_to_tune, len(parameters)))

        tuned_code = code

        for param in params_to_tune:
            old_value = param["value"]

            # Apply mutation to value
            if "." in old_value:
                # Float value
                old_float = float(old_value)
                adjustment = old_float * random.uniform(-0.2, 0.2)
                new_value = str(max(0, old_float + adjustment))
            else:
                # Integer value
                old_int = int(old_value)
                adjustment = random.randint(-max(1, int(old_int * 0.2)), max(1, int(old_int * 0.2)))
                new_value = str(max(0, old_int + adjustment))

            # Replace in code
            tuned_code = tuned_code.replace(
                f'{param["name"]} = {old_value}',
                f'{param["name"]} = {new_value}'
            )

        return tuned_code

    def get_type(self) -> "MutationType":
        """Get mutation type."""
        from bioagent.evolution.models import MutationType
        return MutationType.PARAMETER_TUNER


def create_strategy(
    strategy_type: str,
    llm_provider: "LLMProvider",
    logger: "Logger"
) -> MutationStrategy:
    """
    Factory function to create mutation strategy.

    Args:
        strategy_type: Type of strategy ("analyzer_mutator", "code_rewriter", "parameter_tuner")
        llm_provider: LLM provider
        logger: Logger

    Returns:
        Mutation strategy instance
    """
    strategies = {
        "analyzer_mutator": AnalyzerMutatorStrategy,
        "code_rewriter": CodeRewriterStrategy,
        "parameter_tuner": ParameterTunerStrategy,
    }

    strategy_class = strategies.get(strategy_type)
    if not strategy_class:
        raise ValueError(f"Unknown strategy type: {strategy_type}")

    return strategy_class(llm_provider, logger)
