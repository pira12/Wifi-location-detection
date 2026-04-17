"""Option system for wifipi: per-module specs + global/local resolution.

Resolution order: local (module) → global (session) → spec default.
Globals work even without a spec, because modules are loaded lazily and
the user may set a global before selecting a module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class OptionSpec:
    required: bool = False
    default: Any = None
    description: str = ""
    kind: str = "string"   # "string" | "int" | "mac" | "bssid" | "path" | "role"


@dataclass
class ResolvedOption:
    value: Any
    source: Literal["local", "global", "default"]


class OptionStore:
    def __init__(self, specs: dict[str, OptionSpec]):
        self.specs: dict[str, OptionSpec] = dict(specs)
        self._local: dict[str, Any] = {}
        self._global: dict[str, Any] = {}

    # --- mutation -------------------------------------------------------
    def set_local(self, key: str, value: Any) -> None:
        if key not in self.specs:
            raise KeyError(f"unknown option {key!r} for this module")
        self._local[key] = value

    def set_global(self, key: str, value: Any) -> None:
        self._global[key] = value

    def unset_local(self, key: str) -> None:
        self._local.pop(key, None)

    def unset_global(self, key: str) -> None:
        self._global.pop(key, None)

    def clear_locals(self) -> None:
        self._local.clear()

    # --- resolution -----------------------------------------------------
    def resolve(self, key: str) -> ResolvedOption | None:
        if key in self._local:
            return ResolvedOption(self._local[key], "local")
        if key in self._global:
            return ResolvedOption(self._global[key], "global")
        spec = self.specs.get(key)
        if spec is None or spec.default is None:
            return None
        return ResolvedOption(spec.default, "default")

    def resolve_value(self, key: str) -> Any:
        r = self.resolve(key)
        return r.value if r else None

    def resolve_all(self) -> dict[str, ResolvedOption]:
        """All keys known to the current spec, with their resolved source."""
        out: dict[str, ResolvedOption] = {}
        for key in self.specs:
            r = self.resolve(key)
            if r is not None:
                out[key] = r
            else:
                out[key] = ResolvedOption(None, "default")
        return out

    def missing_required(self) -> list[str]:
        missing = []
        for key, spec in self.specs.items():
            if not spec.required:
                continue
            r = self.resolve(key)
            if r is None or r.value in (None, ""):
                missing.append(key)
        return missing
