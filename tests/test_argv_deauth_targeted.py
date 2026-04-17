from wifipi.modules.attack.deauth_targeted import DeauthTargeted


def test_deauth_targeted_argv():
    m = DeauthTargeted()
    argv = m.build_argv({
        "BSSID": "AA:BB:CC:11:22:33",
        "CLIENT": "DD:EE:FF:44:55:66",
        "CHANNEL": "11",
        "COUNT": "10",
        "MON_IFACE": "wlan1mon",
    })
    assert argv == [
        "aireplay-ng", "--deauth", "10",
        "-a", "AA:BB:CC:11:22:33",
        "-c", "DD:EE:FF:44:55:66",
        "wlan1mon",
    ]
