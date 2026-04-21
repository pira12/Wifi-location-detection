from wifipi.modules.attack.karma import Karma


def test_karma_argv_defaults():
    m = Karma()
    argv = m.build_argv({
        "AP_IFACE": "wlan2",
        "CHANNEL": "6",
        "UPSTREAM_IFACE": "eth0",
        "_WORKDIR": "/tmp/loot/run",
    })
    assert argv[:3] == ["python3", "-m", "wifipi.modules.attack._karma_runner"]
    assert "--ap-iface" in argv and "wlan2" in argv
    assert "--channel" in argv and "6" in argv
    assert "--upstream" in argv and "eth0" in argv
    assert "--workdir" in argv


def test_karma_requires_ap_iface():
    m = Karma()
    import pytest
    with pytest.raises(RuntimeError):
        m.build_argv({"CHANNEL": "6"})
