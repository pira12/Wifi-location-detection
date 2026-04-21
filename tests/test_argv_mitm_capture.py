from wifipi.modules.attack.mitm_capture import MitmCapture


def test_mitm_capture_argv_defaults():
    m = MitmCapture()
    argv = m.build_argv({
        "AP_IFACE": "wlan2",
        "OUTPUT_PREFIX": "/tmp/loot/capture",
        "SNAPLEN": "0",
    })
    assert argv[0] == "tcpdump"
    assert "-i" in argv and "wlan2" in argv
    assert "-w" in argv
    assert "/tmp/loot/capture-01.pcap" in argv or "/tmp/loot/capture.pcap" in argv
    assert "-s" in argv and "0" in argv


def test_mitm_capture_argv_with_filter():
    m = MitmCapture()
    argv = m.build_argv({
        "AP_IFACE": "wlan2",
        "OUTPUT_PREFIX": "/tmp/loot/capture",
        "SNAPLEN": "0",
        "FILTER": "port 53",
    })
    # BPF filter goes at the end, as one arg.
    assert "port 53" in argv
