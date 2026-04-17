from wifipi.modules.post.crack import Crack


def test_crack_argv():
    m = Crack()
    argv = m.build_argv({
        "BSSID": "AA:BB:CC:11:22:33",
        "WORDLIST": "/usr/share/wordlists/rockyou.txt",
        "CAPTURE_FILE": "/tmp/handshake-01.cap",
    })
    assert argv == [
        "aircrack-ng",
        "-w", "/usr/share/wordlists/rockyou.txt",
        "-b", "AA:BB:CC:11:22:33",
        "/tmp/handshake-01.cap",
    ]
