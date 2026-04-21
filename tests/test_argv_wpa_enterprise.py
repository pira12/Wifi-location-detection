from wifipi.modules.attack.wpa_enterprise import WpaEnterprise


def test_wpa_ent_argv():
    m = WpaEnterprise()
    argv = m.build_argv({
        "AP_IFACE": "wlan2",
        "SSID": "CorpWifi",
        "CHANNEL": "6",
        "_WORKDIR": "/tmp/loot/run",
    })
    assert argv[:3] == ["python3", "-m", "wifipi.modules.attack._wpa_ent_runner"]
    assert "--ap-iface" in argv and "wlan2" in argv
    assert "--ssid" in argv and "CorpWifi" in argv
    assert "--channel" in argv and "6" in argv
