from wifipi.modules.recon.scan import Scan


def test_scan_argv_iface_only():
    m = Scan()
    argv = m.build_argv({"MON_IFACE": "wlan1mon"})
    assert argv == ["airodump-ng", "wlan1mon"]


def test_scan_argv_with_channel():
    m = Scan()
    argv = m.build_argv({"MON_IFACE": "wlan1mon", "CHANNEL": "11"})
    assert argv == ["airodump-ng", "-c", "11", "wlan1mon"]
