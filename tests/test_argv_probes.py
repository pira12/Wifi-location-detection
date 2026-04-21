from wifipi.modules.recon.probes import Probes


def test_probes_argv_hops_by_default():
    m = Probes()
    argv = m.build_argv({
        "MON_IFACE": "wlan1mon",
        "DURATION": "0",
        "_WORKDIR": "/tmp/loot/run",
    })
    assert argv[:3] == ["python3", "-m", "wifipi.modules.recon._probes_runner"]
    assert "--mon-iface" in argv and "wlan1mon" in argv
    assert "--workdir" in argv
    assert "--channel" not in argv   # hop mode
    assert "--duration" in argv and "0" in argv


def test_probes_argv_locks_channel_if_set():
    m = Probes()
    argv = m.build_argv({
        "MON_IFACE": "wlan1mon",
        "CHANNEL": "6",
        "DURATION": "60",
        "_WORKDIR": "/tmp/loot/run",
    })
    assert "--channel" in argv and "6" in argv
