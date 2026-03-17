"""
Checkpoint manager for evolution runs.

Provides state persistence and resume capabilities.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from bioagent.observability import Logger


class CheckpointManager:
    """
    Manages evolution run checkpoints.

    Saves and loads evolution state for resuming interrupted runs.
    """

    def __init__(self, evolution_dir: str, logger: Logger):
        """
        Initialize the checkpoint manager.

        Args:
            evolution_dir: Directory for storing checkpoints
            logger: Logger for recording events
        """
        self.evolution_dir = Path(evolution_dir)
        self.evolution_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self.checkpoints_dir = self.evolution_dir / "checkpoints"
        self.checkpoints_dir.mkdir(exist_ok=True)

    def save_checkpoint(
        self,
        run_id: str,
        generation: int,
        grid_data: Dict,
        run_data: Dict
    ) -> str:
        """
        Save checkpoint for current evolution state.

        Args:
            run_id: Evolution run ID
            generation: Current generation number
            grid_data: Grid state data
            run_data: Evolution run data

        Returns:
            Checkpoint file path
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        checkpoint_name = f"{run_id}_gen{generation}_{timestamp}"
        checkpoint_path = self.checkpoints_dir / f"{checkpoint_name}.json"

        checkpoint_data = {
            "run_id": run_id,
            "generation": generation,
            "timestamp": datetime.utcnow().isoformat(),
            "grid": grid_data,
            "run": run_data,
        }

        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint_data, f, indent=2)

        self.logger.info(
            "Checkpoint saved",
            checkpoint=str(checkpoint_path),
            generation=generation,
        )

        # Clean up old checkpoints
        self._cleanup_old_checkpoints(run_id)

        return str(checkpoint_path)

    def load_checkpoint(
        self,
        checkpoint_path: str
    ) -> Optional[Dict]:
        """
        Load checkpoint from file.

        Args:
            checkpoint_path: Path to checkpoint file

        Returns:
            Checkpoint data or None if not found
        """
        path = Path(checkpoint_path)

        if not path.exists():
            # Try relative to checkpoints dir
            path = self.checkpoints_dir / checkpoint_path

        if not path.exists():
            self.logger.warning(f"Checkpoint not found: {checkpoint_path}")
            return None

        try:
            with open(path, "r") as f:
                data = json.load(f)

            self.logger.info(
                "Checkpoint loaded",
                checkpoint=str(path),
                generation=data.get("generation"),
            )

            return data

        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            return None

    def load_latest_checkpoint(self, run_id: str) -> Optional[Dict]:
        """
        Load the most recent checkpoint for a run.

        Args:
            run_id: Evolution run ID

        Returns:
            Checkpoint data or None if not found
        """
        checkpoints = self.list_checkpoints(run_id)

        if not checkpoints:
            return None

        # Sort by timestamp, get latest
        checkpoints.sort(key=lambda x: x["timestamp"], reverse=True)
        latest = checkpoints[0]

        return self.load_checkpoint(latest["path"])

    def list_checkpoints(self, run_id: Optional[str] = None) -> List[Dict]:
        """
        List available checkpoints.

        Args:
            run_id: Optional filter by specific run ID

        Returns:
            List of checkpoint information dictionaries
        """
        checkpoints = []

        for checkpoint_file in self.checkpoints_dir.glob("*.json"):
            try:
                with open(checkpoint_file, "r") as f:
                    data = json.load(f)

                checkpoint_info = {
                    "path": str(checkpoint_file),
                    "run_id": data.get("run_id"),
                    "generation": data.get("generation"),
                    "timestamp": data.get("timestamp"),
                    "size": checkpoint_file.stat().st_size,
                }

                if run_id is None or checkpoint_info["run_id"] == run_id:
                    checkpoints.append(checkpoint_info)

            except Exception as e:
                self.logger.warning(f"Failed to read checkpoint {checkpoint_file}: {e}")

        return checkpoints

    def delete_checkpoint(self, checkpoint_path: str) -> bool:
        """
        Delete a checkpoint file.

        Args:
            checkpoint_path: Path to checkpoint file

        Returns:
            True if deleted, False otherwise
        """
        path = Path(checkpoint_path)

        if not path.exists():
            path = self.checkpoints_dir / checkpoint_path

        if path.exists():
            try:
                path.unlink()
                self.logger.info(f"Checkpoint deleted: {path}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to delete checkpoint {path}: {e}")
                return False

        return False

    def delete_run_checkpoints(self, run_id: str) -> int:
        """
        Delete all checkpoints for a specific run.

        Args:
            run_id: Evolution run ID

        Returns:
            Number of checkpoints deleted
        """
        checkpoints = self.list_checkpoints(run_id)
        deleted = 0

        for checkpoint in checkpoints:
            if self.delete_checkpoint(checkpoint["path"]):
                deleted += 1

        self.logger.info(
            f"Deleted {deleted} checkpoints for run {run_id}"
        )

        return deleted

    def cleanup(
        self,
        max_checkpoints: int = 10,
        older_than_days: Optional[int] = None
    ) -> int:
        """
        Clean up old checkpoints.

        Args:
            max_checkpoints: Maximum checkpoints to keep per run
            older_than_days: Delete checkpoints older than this many days

        Returns:
            Number of checkpoints deleted
        """
        deleted = 0

        # Group checkpoints by run ID
        run_checkpoints: Dict[str, List[Dict]] = {}
        for checkpoint in self.list_checkpoints():
            run_id = checkpoint["run_id"]
            if run_id not in run_checkpoints:
                run_checkpoints[run_id] = []
            run_checkpoints[run_id].append(checkpoint)

        # Clean up per run
        for run_id, checkpoints in run_checkpoints.items():
            # Sort by timestamp
            checkpoints.sort(key=lambda x: x["timestamp"], reverse=True)

            # Delete excess checkpoints
            if len(checkpoints) > max_checkpoints:
                for checkpoint in checkpoints[max_checkpoints:]:
                    if self.delete_checkpoint(checkpoint["path"]):
                        deleted += 1

            # Delete old checkpoints
            if older_than_days is not None:
                cutoff = datetime.utcnow().timestamp() - (older_than_days * 24 * 3600)
                for checkpoint in checkpoints[max_checkpoints:]:
                    timestamp = datetime.fromisoformat(checkpoint["timestamp"]).timestamp()
                    if timestamp < cutoff:
                        if self.delete_checkpoint(checkpoint["path"]):
                            deleted += 1

        if deleted > 0:
            self.logger.info(f"Cleaned up {deleted} old checkpoints")

        return deleted

    def _cleanup_old_checkpoints(self, run_id: str, max_keep: int = 10) -> None:
        """
        Clean up old checkpoints for a specific run.

        Args:
            run_id: Evolution run ID
            max_keep: Maximum checkpoints to keep
        """
        checkpoints = self.list_checkpoints(run_id)
        checkpoints.sort(key=lambda x: x["timestamp"], reverse=True)

        # Delete excess checkpoints
        for checkpoint in checkpoints[max_keep:]:
            try:
                Path(checkpoint["path"]).unlink()
            except Exception:
                pass

    def get_checkpoint_dir(self) -> Path:
        """Get the checkpoints directory path."""
        return self.checkpoints_dir

    def get_storage_info(self) -> Dict[str, any]:
        """
        Get storage information.

        Returns:
            Dictionary with storage statistics
        """
        total_size = sum(
            f.stat().st_size
            for f in self.checkpoints_dir.glob("*.json")
            if f.is_file()
        )

        return {
            "directory": str(self.checkpoints_dir),
            "checkpoint_count": len(list(self.checkpoints_dir.glob("*.json"))),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
        }
