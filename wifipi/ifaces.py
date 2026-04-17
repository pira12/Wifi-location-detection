"""Wireless interface discovery and role assignment.

Parses `iw dev` output and tracks the three session roles:
  MON    — monitor / capture adapter
  ATTACK — packet-injection adapter (can equal MON on single-adapter rigs)
  AP     — rogue-AP adapter (hostapd)
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass


class Role(enum.Enum):
    MON = "MON_IFACE"
    ATTACK = "ATTACK_IFACE"
    AP = "AP_IFACE"

    @classmethod
    def from_str(cls, s: str) -> "Role":
        key = s.strip().lower()
        aliases = {
            "mon": cls.MON, "monitor": cls.MON,
            "attack": cls.ATTACK, "deauth": cls.ATTACK,
            "ap": cls.AP, "rogue": cls.AP,
        }
        if key in aliases:
            return aliases[key]
        raise ValueError(f"unknown role {s!r}; expected mon|attack|ap")


@dataclass(frozen=True)
class InterfaceInfo:
    name: str
    mode: str     # "managed" | "monitor" | "AP" | ...
    phy: str      # e.g. "phy#1"


_PHY_RE = re.compile(r"^(phy#\d+)")
_IFACE_RE = re.compile(r"^\s*Interface\s+(\S+)")
_TYPE_RE = re.compile(r"^\s*type\s+(\S+)")


def parse_iw_dev(text: str) -> list[InterfaceInfo]:
    """Parse the output of `iw dev`. Returns a list of InterfaceInfo."""
    current_phy: str | None = None
    current_name: str | None = None
    current_type: str | None = None
    out: list[InterfaceInfo] = []

    def _flush():
        nonlocal current_name, current_type
        if current_name is not None:
            out.append(InterfaceInfo(
                name=current_name,
                mode=current_type or "unknown",
                phy=current_phy or "",
            ))
        current_name = None
        current_type = None

    for line in text.splitlines():
        if m := _PHY_RE.match(line):
            _flush()
            current_phy = m.group(1)
            continue
        if m := _IFACE_RE.match(line):
            _flush()
            current_name = m.group(1)
            continue
        if m := _TYPE_RE.match(line):
            current_type = m.group(1)
            continue
    _flush()
    return out


class InterfaceManager:
    """Holds the mapping Role → interface name for the session."""

    def __init__(self) -> None:
        self._roles: dict[Role, str] = {}

    def assign(self, role: Role, name: str) -> None:
        self._roles[role] = name

    def get(self, role: Role) -> str | None:
        return self._roles.get(role)

    def all_assignments(self) -> dict[Role, str]:
        return dict(self._roles)

    def clear(self, role: Role | None = None) -> None:
        if role is None:
            self._roles.clear()
        else:
            self._roles.pop(role, None)

    def rename(self, old: str, new: str) -> None:
        """Airmon-ng renamed an interface (wlan1 → wlan1mon). Update any role
        that currently points at `old` to `new`."""
        for role, name in list(self._roles.items()):
            if name == old:
                self._roles[role] = new
