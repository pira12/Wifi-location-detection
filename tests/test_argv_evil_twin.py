from wifipi.modules.attack.evil_twin import EvilTwin


def test_evil_twin_argv():
    m = EvilTwin()
    argv = m.build_argv({
        "BSSID": "AA:BB:CC:11:22:33",
        "SSID": "MyTestNetwork",
        "CHANNEL": "11",
        "CLIENT": "DD:EE:FF:44:55:66",
        "WPA_PASSPHRASE": "password123",
        "UPSTREAM_IFACE": "eth0",
        "MON_IFACE": "wlan1mon",
        "AP_IFACE": "wlan2",
        "_WORKDIR": "/tmp/loot/run",
    })
    assert argv[:3] == ["python3", "-m", "wifipi.modules.attack._evil_twin_runner"]
    assert "--ssid" in argv and "MyTestNetwork" in argv
    assert "--client" in argv
    assert "--wpa-pass" in argv
