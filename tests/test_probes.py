from pathlib import Path

from wifipi.probes import ProbeRecord, load_ouis, parse_airodump_csv, render_summary


FIXTURES = Path(__file__).parent / "fixtures"


def test_load_ouis_parses_tiny_fixture():
    ouis = load_ouis(FIXTURES / "oui_tiny.txt")
    assert ouis["B8:27:EB"] == "Raspberry Pi Foundation"
    assert ouis["A4:77:33"] == "Google, Inc."


def test_load_ouis_normalises_case():
    # Lookup should be case-insensitive — file might use mixed case.
    ouis = load_ouis(FIXTURES / "oui_tiny.txt")
    assert ouis.get("b8:27:eb".upper()) == "Raspberry Pi Foundation"


def test_parse_airodump_csv_returns_station_probes():
    records = parse_airodump_csv(FIXTURES / "airodump.csv")
    by_mac = {r.mac: r for r in records}
    assert "B8:27:EB:11:22:33" in by_mac
    rpi = by_mac["B8:27:EB:11:22:33"]
    assert rpi.probed_ssids == ["Starbucks WiFi", "HomeNet", "eduroam"]
    assert rpi.associated_bssid is None   # "(not associated)" → None
    assert by_mac["A4:77:33:44:55:66"].associated_bssid == "AA:BB:CC:11:22:33"


def test_parse_airodump_csv_drops_empty_probes():
    records = parse_airodump_csv(FIXTURES / "airodump.csv")
    # The DE:AD:BE:EF station has no probed SSIDs — should still appear,
    # with probed_ssids == [].
    by_mac = {r.mac: r for r in records}
    assert by_mac["DE:AD:BE:EF:00:01"].probed_ssids == []


def test_render_summary_formats_columns():
    records = [
        ProbeRecord(mac="B8:27:EB:11:22:33", associated_bssid=None,
                    probed_ssids=["Starbucks WiFi", "HomeNet"]),
        ProbeRecord(mac="A4:77:33:44:55:66",
                    associated_bssid="AA:BB:CC:11:22:33",
                    probed_ssids=["LabTestAP"]),
    ]
    ouis = {"B8:27:EB": "Raspberry Pi Foundation", "A4:77:33": "Google, Inc."}
    text = render_summary(records, ouis)
    assert "Raspberry Pi Foundation" in text
    assert "Starbucks WiFi, HomeNet" in text
    assert "Google, Inc." in text


def test_render_summary_handles_unknown_oui():
    records = [ProbeRecord(mac="DE:AD:BE:EF:00:01",
                           associated_bssid=None, probed_ssids=[])]
    text = render_summary(records, ouis={})
    assert "unknown" in text.lower() or "DE:AD:BE:EF:00:01" in text
