"""Manages the `loot/` directory: timestamped per-run subdirs + listing."""

from __future__ import annotations

import shutil
import time
from pathlib import Path


class LootManager:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def new_run(self, category: str, module_name: str) -> Path:
        """loot/<category>/<timestamp>-<module_name>/ — creates + returns it."""
        ts = time.strftime("%Y-%m-%d_%H-%M-%S")
        safe_name = module_name.replace("/", "-")
        run = self.root / category / f"{ts}-{safe_name}"
        run.mkdir(parents=True, exist_ok=True)
        return run

    def recent(self, category: str | None = None, limit: int = 20) -> list[Path]:
        if category:
            base = self.root / category
            candidates = list(base.iterdir()) if base.exists() else []
        else:
            candidates = []
            for sub in self.root.iterdir():
                if sub.is_dir():
                    candidates.extend(sub.iterdir())
        runs = [p for p in candidates if p.is_dir()]
        runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return runs[:limit]

    def clean(self) -> None:
        for child in self.root.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
