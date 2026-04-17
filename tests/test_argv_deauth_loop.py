from wifipi.modules.attack.deauth_loop import DeauthLoop


def test_deauth_loop_argv_client():
    m = DeauthLoop()
    argv = m.build_argv({
        "BSSID": "AA:BB:CC:11:22:33",
        "CLIENT": "DD:EE:FF:44:55:66",
        "CHANNEL": "11",
        "INTERVAL": "5",
        "BURST": "5",
        "MON_IFACE": "wlan1mon",
    })
    assert argv[:3] == ["python3", "-m", "wifipi.modules.attack._deauth_loop_runner"]
    assert "--client" in argv
    assert "DD:EE:FF:44:55:66" in argv


def test_deauth_loop_argv_broadcast():
    m = DeauthLoop()
    argv = m.build_argv({
        "BSSID": "AA:BB:CC:11:22:33",
        "CHANNEL": "11",
        "INTERVAL": "5",
        "BURST": "5",
        "MON_IFACE": "wlan1mon",
    })
    assert "--client" not in argv
