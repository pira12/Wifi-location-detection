from wifipi.modules.attack.ssid_pool import SsidPool


def test_ssid_pool_argv():
    m = SsidPool()
    argv = m.build_argv({
        "AP_IFACE": "wlan2",
        "PROBES_CSV": "/tmp/probes-01.csv",
        "CHANNEL": "6",
        "UPSTREAM_IFACE": "eth0",
        "MAX_SSIDS": "50",
        "_WORKDIR": "/tmp/loot/run",
    })
    assert argv[:3] == ["python3", "-m", "wifipi.modules.attack._ssid_pool_runner"]
    assert "--ap-iface" in argv and "wlan2" in argv
    assert "--probes-csv" in argv and "/tmp/probes-01.csv" in argv
    assert "--channel" in argv and "6" in argv
    assert "--max-ssids" in argv and "50" in argv
