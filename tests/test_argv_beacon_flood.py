from wifipi.modules.attack.beacon_flood import BeaconFlood


def test_beacon_flood_argv_defaults():
    m = BeaconFlood()
    argv = m.build_argv({
        "MON_IFACE": "wlan1mon",
        "SSID_LIST": "/repo/configs/ssidlist-top100.txt",
        "PPS": "50",
    })
    # mdk4 <iface> b -f <file> -s <pps>
    assert argv[0] == "mdk4"
    assert argv[1] == "wlan1mon"
    assert argv[2] == "b"
    assert "-f" in argv
    assert "/repo/configs/ssidlist-top100.txt" in argv
    assert "-s" in argv
    assert "50" in argv


def test_beacon_flood_argv_locks_channel():
    m = BeaconFlood()
    argv = m.build_argv({
        "MON_IFACE": "wlan1mon",
        "SSID_LIST": "/tmp/list.txt",
        "CHANNEL": "6",
        "PPS": "50",
    })
    assert "-c" in argv and "6" in argv
