"""
MAP-Elites grid implementation.

Implements a quality-diversity optimization grid that maintains diverse solutions
across a behavior space.
"""

import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from bioagent.evolution.models import EvolvedCode, GridCell, EvolutionRun


class MAPElitesGrid:
    """
    MAP-Elites grid for quality-diversity optimization.

    Maintains a grid where each cell contains the best solution
    for a specific region of behavior space.
    """

    def __init__(self, resolution: int = 10, dimensions: int = 7):
        """
        Initialize the MAP-Elites grid.

        Args:
            resolution: Number of bins per dimension
            dimensions: Number of behavior dimensions
        """
        self.resolution = resolution
        self.dimensions = dimensions
        self.shape = (resolution,) * dimensions
        self._cells: Dict[Tuple[int, ...], GridCell] = {}

    def insert(self, code: "EvolvedCode") -> bool:
        """
        Insert code into grid if it improves the cell.

        Args:
            code: Evolved code to insert

        Returns:
            True if inserted, False if cell already had better code
        """
        # Compute behavior index
        idx = self._get_index(code.behavior_vector)

        # Check if cell exists and compare fitness
        if idx in self._cells:
            cell = self._cells[idx]
            if cell.code and cell.code.fitness.combined >= code.fitness.combined:
                return False  # Cell already has better solution

        # Create or update cell
        from bioagent.evolution.models import GridCell

        self._cells[idx] = GridCell(behavior_idx=idx, code=code)
        return True

    def get_cell(self, idx: Tuple[int, ...]) -> Optional["GridCell"]:
        """
        Get cell at specific index.

        Args:
            idx: Grid index tuple

        Returns:
            GridCell or None if empty
        """
        return self._cells.get(idx)

    def select_parents(self, count: int = 5) -> List["EvolvedCode"]:
        """
        Select parents for mutation from occupied cells.

        Uses tournament selection preferring high-fitness cells.

        Args:
            count: Number of parents to select

        Returns:
            List of evolved codes
        """
        occupied = [c for c in self._cells.values() if c.is_occupied()]
        if not occupied:
            return []

        # Sort by fitness
        occupied.sort(key=lambda c: c.fitness(), reverse=True)

        # Tournament selection
        parents = []
        for _ in range(count):
            tournament_size = min(3, len(occupied))
            tournament = np.random.choice(
                occupied,
                size=tournament_size,
                replace=False
            )
            winner = max(tournament, key=lambda c: c.fitness())
            parents.append(winner.code)

        return parents

    def get_coverage(self) -> float:
        """
        Get grid coverage ratio.

        Returns:
            Ratio of occupied cells to total cells
        """
        total_cells = self.resolution ** self.dimensions
        return len(self._cells) / total_cells if total_cells > 0 else 0.0

    def get_elites(self) -> List["EvolvedCode"]:
        """
        Get all elite solutions from occupied cells.

        Returns:
            List of evolved codes sorted by fitness
        """
        elites = [c.code for c in self._cells.values() if c.is_occupied()]
        elites.sort(key=lambda c: c.fitness.combined, reverse=True)
        return elites

    def get_best(self) -> Optional["EvolvedCode"]:
        """
        Get the overall best solution.

        Returns:
            Best evolved code or None
        """
        elites = self.get_elites()
        return elites[0] if elites else None

    def clear(self) -> None:
        """Clear all cells."""
        self._cells.clear()

    def size(self) -> int:
        """Get number of occupied cells."""
        return len(self._cells)

    def is_empty(self) -> bool:
        """Check if grid is empty."""
        return len(self._cells) == 0

    def get_statistics(self) -> Dict[str, any]:
        """
        Get grid statistics.

        Returns:
            Dictionary with coverage, size, best fitness
        """
        best = self.get_best()
        return {
            "coverage": self.get_coverage(),
            "occupied_cells": self.size(),
            "total_cells": self.resolution ** self.dimensions,
            "best_fitness": best.fitness.combined if best else 0.0,
        }

    def _get_index(self, behavior_vector: Tuple[float, ...]) -> Tuple[int, ...]:
        """
        Convert behavior vector to grid index.

        Args:
            behavior_vector: Normalized behavior vector

        Returns:
            Tuple of grid indices
        """
        from bioagent.evolution.models import compute_behavior_index
        return compute_behavior_index(behavior_vector, self.resolution)

    def save(self, path: str) -> None:
        """
        Save grid to file.

        Args:
            path: File path to save to
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        # Serialize cells to dict
        cells_data = {}
        for idx, cell in self._cells.items():
            cells_data[str(idx)] = {
                "behavior_idx": idx,
                "code": cell.code.to_dict() if cell.code else None,
            }

        data = {
            "resolution": self.resolution,
            "dimensions": self.dimensions,
            "cells": cells_data,
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> None:
        """
        Load grid from file.

        Args:
            path: File path to load from
        """
        with open(path, "r") as f:
            data = json.load(f)

        self.resolution = data["resolution"]
        self.dimensions = data["dimensions"]

        self._cells.clear()
        from bioagent.evolution.models import GridCell, EvolvedCode

        for idx_str, cell_data in data["cells"].items():
            idx = eval(cell_data["behavior_idx"])
            code = EvolvedCode.from_dict(cell_data["code"]) if cell_data["code"] else None
            self._cells[idx] = GridCell(behavior_idx=idx, code=code)

    def save_pickle(self, path: str) -> None:
        """
        Save grid to pickle file (faster for large grids).

        Args:
            path: File path to save to
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load_pickle(cls, path: str) -> "MAPElitesGrid":
        """
        Load grid from pickle file.

        Args:
            path: File path to load from

        Returns:
            Loaded MAPElitesGrid instance
        """
        with open(path, "rb") as f:
            return pickle.load(f)

    def visualize(self) -> str:
        """
        Generate ASCII visualization of grid.

        Returns:
            ASCII string representation
        """
        # For 2D grids, show grid layout
        if self.dimensions == 2:
            lines = []
            for i in range(self.resolution):
                row = []
                for j in range(self.resolution):
                    idx = (i, j)
                    if idx in self._cells:
                        fitness = self._cells[idx].fitness()
                        if fitness > 0.8:
                            row.append("█")
                        elif fitness > 0.6:
                            row.append("▓")
                        elif fitness > 0.4:
                            row.append("▒")
                        elif fitness > 0.2:
                            row.append("░")
                        else:
                            row.append("·")
                    else:
                        row.append(" ")
                lines.append("".join(row))
            return "\n".join(lines)

        # For higher dimensions, show statistics
        return f"MAP-Elites Grid ({self.dimensions}D, {self.resolution}x{self.resolution}...)\n" \
               f"Coverage: {self.get_coverage()*100:.1f}%\n" \
               f"Occupied: {self.size()}/{self.resolution**self.dimensions}\n"
