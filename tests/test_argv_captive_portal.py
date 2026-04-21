from wifipi.modules.attack.captive_portal import CaptivePortal


def test_captive_portal_argv():
    m = CaptivePortal()
    argv = m.build_argv({
        "AP_IFACE": "wlan2",
        "SSID": "Free WiFi",
        "CHANNEL": "6",
        "PORTAL_TEMPLATE": "/repo/configs/portal/index.html",
        "_WORKDIR": "/tmp/loot/run",
    })
    assert argv[:3] == ["python3", "-m", "wifipi.modules.attack._captive_portal_runner"]
    assert "--ap-iface" in argv and "wlan2" in argv
    assert "--ssid" in argv and "Free WiFi" in argv
    assert "--channel" in argv and "6" in argv
    assert "--template" in argv and "/repo/configs/portal/index.html" in argv
