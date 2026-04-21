"""recon/probes — harvest probe requests on MON_IFACE.

Background runner invokes airodump-ng in CSV+pcap mode; on teardown the
runner parses the CSV and writes summary.txt next to the capture.
"""

from __future__ import annotations

from wifipi.module import Module
from wifipi.options import OptionSpec


class Probes(Module):
    NAME = "recon/probes"
    CATEGORY = "recon"
    DESCRIPTION = (
        "Harvest probe requests: collects airodump CSV + pcap, writes "
        "summary.txt (per-client preferred-network list + vendor)."
    )
    OPTIONS = {
        "CHANNEL":  OptionSpec(required=False, default=None,
                               description="Lock to one channel (else hop).",
                               kind="int"),
        "DURATION": OptionSpec(required=False, default="0",
                               description="Stop after N seconds (0 = run until killed).",
                               kind="int"),
    }
    REQUIRES_TOOLS = ["airodump-ng"]
    BLOCKING = False
    LOOT_SUBDIR = "probes"

    def build_argv(self, opts: dict) -> list[str]:
        iface = opts.get("MON_IFACE")
        if not iface:
            raise RuntimeError("MON_IFACE not set (run `iface auto` first)")
        argv = [
            "python3", "-m", "wifipi.modules.recon._probes_runner",
            "--mon-iface", iface,
            "--workdir", opts.get("_WORKDIR", "/tmp/probes"),
            "--duration", str(opts.get("DURATION", "0")),
        ]
        channel = opts.get("CHANNEL")
        if channel:
            argv += ["--channel", str(channel)]
        return argv
