"""Parse lab-notes/inventory.md for MACs/BSSIDs the user has scoped.

Purely advisory (soft gate only). The inventory is printed at startup
and available via the `inventory` command; attack modules do not hard-
refuse unrecognised targets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

MAC_RE = re.compile(r"\b([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})\b")


@dataclass
class Inventory:
    bssids: list[str] = field(default_factory=list)
    clients: list[str] = field(default_factory=list)

    def contains(self, mac: str) -> bool:
        needle = mac.upper()
        return needle in (m.upper() for m in self.bssids + self.clients)


def parse_inventory(path: Path) -> Inventory:
    inv = Inventory()
    if not path.exists():
        return inv
    text = path.read_text(encoding="utf-8", errors="replace")
    section = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = stripped[3:].lower()
            if "test ap" in heading or "rogue" in heading:
                section = "ap"
            elif "client" in heading or "victim" in heading:
                section = "client"
            else:
                section = None
            continue
        for mac in MAC_RE.findall(line):
            mac = mac.upper()
            if section == "client":
                inv.clients.append(mac)
            else:
                inv.bssids.append(mac)
    return inv
