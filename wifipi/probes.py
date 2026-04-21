"""Parser for airodump-ng --output-format csv output.

Airodump's CSV has two sections in one file:

  <BSSID table header>
  <BSSID rows>
  <blank line>
  <Station table header>
  <Station rows with `Probed ESSIDs` as comma-separated field>

We only consume the station table here. Shared by recon/probes and
attack/ssid-pool.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


STATION_HEADER_START = "Station MAC"
NOT_ASSOCIATED = "(not associated)"


@dataclass
class ProbeRecord:
    mac: str
    associated_bssid: str | None
    probed_ssids: list[str] = field(default_factory=list)


def load_ouis(path: Path) -> dict[str, str]:
    """Parse an `OUI  Vendor` file into a lookup dict (uppercase keys)."""
    ouis: dict[str, str] = {}
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Split on whitespace, first token = OUI, rest = vendor.
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        ouis[parts[0].upper()] = parts[1].strip()
    return ouis


def parse_airodump_csv(path: Path) -> list[ProbeRecord]:
    """Return every station row as a ProbeRecord. Empty probed_ssids if
    the station hasn't actively probed anything yet."""
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()

    in_station_section = False
    records: list[ProbeRecord] = []
    for line in lines:
        stripped = line.strip()
        if not in_station_section:
            if stripped.startswith(STATION_HEADER_START):
                in_station_section = True
            continue
        if not stripped:
            continue
        # Station rows are comma-delimited:
        # MAC, first_seen, last_seen, power, packets, BSSID, probed...
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 6:
            continue
        mac = parts[0]
        if len(mac) != 17 or mac.count(":") != 5:
            continue
        bssid_field = parts[5]
        if bssid_field.startswith(NOT_ASSOCIATED):
            associated = None
        else:
            associated = bssid_field
        probed_raw = parts[6:] if len(parts) > 6 else []
        probed = [p for p in probed_raw if p]
        records.append(ProbeRecord(mac=mac.upper(),
                                   associated_bssid=associated,
                                   probed_ssids=probed))
    return records


def _vendor_for(mac: str, ouis: dict[str, str]) -> str:
    oui = mac.upper()[:8]  # "AA:BB:CC"
    return ouis.get(oui, "unknown")


def render_summary(records: list[ProbeRecord], ouis: dict[str, str]) -> str:
    """Produce a human-readable summary table. Columns: MAC, Vendor, Probed."""
    rows = []
    for rec in records:
        vendor = _vendor_for(rec.mac, ouis)
        probed = ", ".join(rec.probed_ssids) if rec.probed_ssids else "(no probes)"
        rows.append((rec.mac, vendor, probed))

    mac_w = max((len(r[0]) for r in rows), default=17)
    vendor_w = max((len(r[1]) for r in rows), default=7)
    header = f"{'Client MAC'.ljust(mac_w)}  {'Vendor'.ljust(vendor_w)}  Probed SSIDs"
    body = [header, "-" * len(header)]
    for mac, vendor, probed in rows:
        body.append(f"{mac.ljust(mac_w)}  {vendor.ljust(vendor_w)}  {probed}")
    return "\n".join(body) + "\n"
