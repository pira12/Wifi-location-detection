from pathlib import Path

from wifipi.inventory import Inventory, parse_inventory

FIXT = Path(__file__).parent / "fixtures"


def test_parses_bssids_and_macs():
    inv = parse_inventory(FIXT / "inventory_populated.md")
    assert "AA:BB:CC:11:22:33" in inv.bssids
    assert "DD:EE:FF:44:55:66" in inv.clients


def test_empty_inventory_has_no_macs():
    inv = parse_inventory(FIXT / "inventory_empty.md")
    assert inv.bssids == []
    assert inv.clients == []


def test_contains_normalises_case():
    inv = parse_inventory(FIXT / "inventory_populated.md")
    assert inv.contains("aa:bb:cc:11:22:33")
    assert inv.contains("AA:BB:CC:11:22:33")
    assert not inv.contains("FF:FF:FF:FF:FF:FF")


def test_missing_file_returns_empty_inventory():
    inv = parse_inventory(Path("/nonexistent/path.md"))
    assert inv.bssids == []
    assert inv.clients == []
