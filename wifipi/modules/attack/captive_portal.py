"""attack/captive-portal — rogue AP with a credential-phishing web page."""

from __future__ import annotations

from pathlib import Path

from wifipi.module import Module
from wifipi.options import OptionSpec


DEFAULT_TEMPLATE = str(
    Path(__file__).resolve().parents[3] / "configs" / "portal" / "index.html"
)


class CaptivePortal(Module):
    NAME = "attack/captive-portal"
    CATEGORY = "attack"
    DESCRIPTION = "Open rogue AP + catch-all DNS + credential-phishing HTTP portal."
    OPTIONS = {
        "SSID":            OptionSpec(required=True,
                                      description="SSID to broadcast."),
        "CHANNEL":         OptionSpec(required=False, default="6",
                                      description="AP channel.", kind="int"),
        "PORTAL_TEMPLATE": OptionSpec(required=False, default=DEFAULT_TEMPLATE,
                                      description="HTML template to serve on GET /.",
                                      kind="path"),
    }
    REQUIRES_TOOLS = ["hostapd", "dnsmasq"]
    BLOCKING = False
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "attacks"

    def build_argv(self, opts: dict) -> list[str]:
        ap = opts.get("AP_IFACE")
        if not ap:
            raise RuntimeError("AP_IFACE not set — need a rogue-AP adapter")
        return [
            "python3", "-m", "wifipi.modules.attack._captive_portal_runner",
            "--workdir", opts.get("_WORKDIR", "/tmp/captive-portal"),
            "--ap-iface", ap,
            "--ssid", opts["SSID"],
            "--channel", str(opts.get("CHANNEL", "6")),
            "--template", opts.get("PORTAL_TEMPLATE", DEFAULT_TEMPLATE),
        ]
