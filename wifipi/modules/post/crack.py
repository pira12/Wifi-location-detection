"""post/crack — offline aircrack-ng against a captured pcap."""

from __future__ import annotations

from pathlib import Path

from wifipi.module import Module, RunContext
from wifipi.options import OptionSpec
from wifipi.procutil import run as run_proc


class Crack(Module):
    NAME = "post/crack"
    CATEGORY = "post"
    DESCRIPTION = "Offline dictionary attack against a WPA handshake pcap."
    OPTIONS = {
        "BSSID":        OptionSpec(required=True,  description="BSSID whose handshake we're cracking.", kind="bssid"),
        "WORDLIST":     OptionSpec(required=True,  description="Path to wordlist.", kind="path"),
        "CAPTURE_FILE": OptionSpec(required=True,  description="Path to .cap with the handshake.", kind="path"),
    }
    REQUIRES_TOOLS = ["aircrack-ng"]
    BLOCKING = True
    LOOT_SUBDIR = "crack"

    def build_argv(self, opts: dict) -> list[str]:
        return [
            "aircrack-ng",
            "-w", opts["WORDLIST"],
            "-b", opts["BSSID"],
            opts["CAPTURE_FILE"],
        ]

    def run(self, ctx: RunContext) -> int:
        wl = Path(ctx.options["WORDLIST"])
        cap = Path(ctx.options["CAPTURE_FILE"])
        if not wl.is_file():
            print(f"[x] wordlist not readable: {wl}  (rockyou is often gzipped — gunzip it)")
            return 2
        if not cap.is_file():
            print(f"[x] capture not readable: {cap}")
            return 2
        argv = self.build_argv(ctx.options)
        # Foreground: let aircrack-ng print progress + "KEY FOUND!" to the user.
        return run_proc(argv).returncode
