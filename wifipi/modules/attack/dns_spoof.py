"""attack/dns-spoof — open rogue AP whose dnsmasq spoofs hostnames."""

from __future__ import annotations

from wifipi.module import Module
from wifipi.options import OptionSpec


class DnsSpoof(Module):
    NAME = "attack/dns-spoof"
    CATEGORY = "attack"
    DESCRIPTION = "Open rogue AP + dnsmasq spoofing A-records from a rules file."
    OPTIONS = {
        "SSID":           OptionSpec(required=True,
                                     description="SSID to broadcast."),
        "CHANNEL":        OptionSpec(required=False, default="6",
                                     description="AP channel.", kind="int"),
        "RULES_FILE":     OptionSpec(required=True,
                                     description="File of 'host ip' pairs "
                                                 "(shell-glob patterns allowed, e.g. *.bank).",
                                     kind="path"),
        "UPSTREAM_IFACE": OptionSpec(required=False, default="eth0",
                                     description="NAT egress interface."),
    }
    REQUIRES_TOOLS = ["hostapd", "dnsmasq", "iptables", "tcpdump"]
    BLOCKING = False
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "attacks"

    def build_argv(self, opts: dict) -> list[str]:
        ap = opts.get("AP_IFACE")
        if not ap:
            raise RuntimeError("AP_IFACE not set — need a rogue-AP adapter")
        return [
            "python3", "-m", "wifipi.modules.attack._dns_spoof_runner",
            "--workdir", opts.get("_WORKDIR", "/tmp/dns-spoof"),
            "--ap-iface", ap,
            "--ssid", opts["SSID"],
            "--channel", str(opts["CHANNEL"]),
            "--rules", opts["RULES_FILE"],
            "--upstream", opts.get("UPSTREAM_IFACE", "eth0"),
        ]
