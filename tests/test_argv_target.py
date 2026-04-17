from wifipi.modules.recon.target import Target


def test_target_argv():
    m = Target()
    argv = m.build_argv({
        "BSSID": "AA:BB:CC:11:22:33",
        "CHANNEL": "11",
        "MON_IFACE": "wlan1mon",
        "OUTPUT_PREFIX": "/tmp/cap",
    })
    assert argv == [
        "airodump-ng", "-c", "11", "--bssid", "AA:BB:CC:11:22:33",
        "-w", "/tmp/cap", "wlan1mon",
    ]
