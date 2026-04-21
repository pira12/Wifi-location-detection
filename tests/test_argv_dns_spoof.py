from wifipi.modules.attack.dns_spoof import DnsSpoof


def test_dns_spoof_argv():
    m = DnsSpoof()
    argv = m.build_argv({
        "AP_IFACE": "wlan2",
        "SSID": "Free WiFi",
        "CHANNEL": "6",
        "RULES_FILE": "/tmp/rules.txt",
        "UPSTREAM_IFACE": "eth0",
        "_WORKDIR": "/tmp/loot/run",
    })
    assert argv[:3] == ["python3", "-m", "wifipi.modules.attack._dns_spoof_runner"]
    assert "--ap-iface" in argv and "wlan2" in argv
    assert "--ssid" in argv and "Free WiFi" in argv
    assert "--channel" in argv and "6" in argv
    assert "--rules" in argv and "/tmp/rules.txt" in argv
    assert "--upstream" in argv and "eth0" in argv
