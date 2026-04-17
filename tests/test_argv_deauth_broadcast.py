from wifipi.modules.attack.deauth_broadcast import DeauthBroadcast


def test_deauth_broadcast_argv():
    m = DeauthBroadcast()
    argv = m.build_argv({
        "BSSID": "AA:BB:CC:11:22:33",
        "CHANNEL": "11",
        "COUNT": "20",
        "MON_IFACE": "wlan1mon",
    })
    assert argv == [
        "aireplay-ng", "--deauth", "20",
        "-a", "AA:BB:CC:11:22:33",
        "wlan1mon",
    ]
