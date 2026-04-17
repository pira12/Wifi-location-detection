"""Module base class used by every category under wifipi.modules.*."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .options import OptionSpec

if TYPE_CHECKING:
    from .ifaces import InterfaceManager
    from .jobs import JobManager
    from .loot import LootManager


@dataclass
class RunContext:
    """Everything a module's run() needs that isn't an option value."""
    options: dict[str, Any]                # resolved (key → value)
    loot_dir: Path                         # pre-created, timestamped
    log_path: Path                         # inside loot_dir; "run.log"
    ifaces: "InterfaceManager"
    jobs: "JobManager"
    loot: "LootManager"


class Module:
    """Subclass this. Declare NAME / OPTIONS / BLOCKING and implement run()."""

    NAME: str = ""
    DESCRIPTION: str = ""
    CATEGORY: str = ""                     # "recon" | "attack" | "post" | "util"
    OPTIONS: dict[str, OptionSpec] = {}
    REQUIRES_TOOLS: list[str] = []
    BLOCKING: bool = True
    REQUIRES_CONFIRMATION: bool = False
    LOOT_SUBDIR: str | None = None         # e.g. "handshakes"

    def build_argv(self, opts: dict[str, Any]) -> list[str]:
        """Pure function: options → argv list. Override for background modules
        so that Console can launch them via JobManager without running the
        full run() wrapper.

        Foreground modules usually don't use this; they run several commands
        in sequence inside run() instead.
        """
        raise NotImplementedError

    def run(self, ctx: RunContext) -> int:
        """Blocking entry point for foreground modules. Return 0 on success."""
        raise NotImplementedError
