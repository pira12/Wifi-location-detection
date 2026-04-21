"""util/pmf-demo — demonstrate that PMF mitigates deauth.

Bring up a PMF-enabled hostapd on AP_IFACE, wait for the operator to
associate CLIENT, then run aireplay-ng deauth from MON_IFACE and check
airodump's station CSV to see whether CLIENT stayed associated.
"""

from __future__ import annotations

import csv
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from wifipi.module import Module, RunContext
from wifipi.options import OptionSpec
from wifipi.procutil import popen as procutil_popen, run as run_proc, terminate


REPO_ROOT = Path(__file__).resolve().parents[3]
PMF_CONF = REPO_ROOT / "configs" / "hostapd-pmf.conf"


class PmfDemo(Module):
    NAME = "util/pmf-demo"
    CATEGORY = "util"
    DESCRIPTION = ("Demonstrate PMF (802.11w) mitigates deauth: brings up a "
                   "PMF-enabled hostapd and fires a deauth burst against it.")
    OPTIONS = {
        "CLIENT":  OptionSpec(required=True,
                              description="Client MAC (will be watched).",
                              kind="mac"),
        "CHANNEL": OptionSpec(required=False, default="6",
                              description="AP channel.", kind="int"),
    }
    REQUIRES_TOOLS = ["hostapd", "aireplay-ng", "airodump-ng", "iw"]
    BLOCKING = True
    REQUIRES_CONFIRMATION = False   # it's a demo; no targeting external gear
    LOOT_SUBDIR = "attacks"

    def run(self, ctx: RunContext) -> int:
        ap_iface = ctx.options.get("AP_IFACE")
        mon_iface = ctx.options.get("MON_IFACE")
        if not ap_iface or not mon_iface:
            print("[x] need both AP_IFACE (hostapd) and MON_IFACE (deauth + sniff)")
            return 2

        client = ctx.options["CLIENT"].upper()
        channel = str(ctx.options.get("CHANNEL", "6"))

        if not PMF_CONF.is_file():
            print(f"[x] {PMF_CONF} missing")
            return 2

        workdir = ctx.loot_dir
        conf_copy = workdir / "hostapd-pmf.conf"
        # Rewrite interface/channel into the copy so the template stays generic.
        original = PMF_CONF.read_text().splitlines()
        rewritten = []
        for line in original:
            if line.startswith("interface="):
                rewritten.append(f"interface={ap_iface}")
            elif line.startswith("channel="):
                rewritten.append(f"channel={channel}")
            else:
                rewritten.append(line)
        conf_copy.write_text("\n".join(rewritten) + "\n")

        hostapd_log = workdir / "hostapd.log"
        deauth_log = workdir / "deauth.log"
        before_prefix = workdir / "before"
        after_prefix = workdir / "after"
        verdict_path = workdir / "verdict.txt"

        run_proc(["nmcli", "device", "set", ap_iface, "managed", "no"], check=False)
        run_proc(["ip", "link", "set", ap_iface, "up"], check=False)

        hostapd = procutil_popen(["hostapd", str(conf_copy)], log_path=hostapd_log)
        try:
            time.sleep(3)
            if hostapd.poll() is not None:
                print(f"[x] hostapd exited early; see {hostapd_log}")
                return 3

            print(f"[*] PMF AP up: SSID='wifipi-pmf-demo' ch={channel}")
            print(f"[*] Associate {client} to it now, then press Enter.")
            try:
                input()
            except EOFError:
                return 1

            run_proc(["iw", "dev", mon_iface, "set", "channel", channel])

            before_ad = procutil_popen(
                ["airodump-ng", "--output-format", "csv", "-c", channel,
                 "-w", str(before_prefix), mon_iface],
                log_path=workdir / "airodump-before.log",
            )
            time.sleep(10)
            terminate(before_ad)
            before_ts = datetime.now(timezone.utc)

            with deauth_log.open("ab") as fh:
                run_proc(
                    ["aireplay-ng", "--deauth", "20", "-c", client,
                     "-a", _bssid_from_hostapd_log(hostapd_log) or "FF:FF:FF:FF:FF:FF",
                     mon_iface],
                    stdout=fh, stderr=fh, check=False,
                )
            deauth_ts = datetime.now(timezone.utc)

            after_ad = procutil_popen(
                ["airodump-ng", "--output-format", "csv", "-c", channel,
                 "-w", str(after_prefix), mon_iface],
                log_path=workdir / "airodump-after.log",
            )
            time.sleep(10)
            terminate(after_ad)

            verdict = _check_client_stayed(
                Path(str(after_prefix) + "-01.csv"), client, deauth_ts)
            verdict_path.write_text(verdict + "\n")
            print(verdict)
            return 0
        finally:
            terminate(hostapd)


def _bssid_from_hostapd_log(log_path: Path) -> str | None:
    if not log_path.is_file():
        return None
    for line in log_path.read_text(errors="replace").splitlines():
        # hostapd prints `<iface>: interface state ... using address <BSSID>`.
        low = line.lower()
        if "using address" in low:
            # Last colon-separated token.
            token = line.strip().split()[-1]
            if token.count(":") == 5:
                return token.upper()
    return None


def _check_client_stayed(csv_path: Path, client: str, deauth_ts: datetime) -> str:
    if not csv_path.is_file():
        return f"UNKNOWN: no airodump CSV at {csv_path}"
    from wifipi.probes import parse_airodump_csv
    records = parse_airodump_csv(csv_path)
    client_u = client.upper()
    for rec in records:
        if rec.mac == client_u:
            # If airodump saw the client after the deauth burst, the client
            # stayed associated — PMF dropped the spoofed deauth.
            last_seen = _last_seen_from_csv(csv_path, client_u)
            if last_seen and last_seen > deauth_ts:
                return ("PMF mitigation CONFIRMED — client seen at "
                        f"{last_seen.isoformat()} after deauth at "
                        f"{deauth_ts.isoformat()}")
            return ("INCONCLUSIVE — client present in CSV but last-seen "
                    "timestamp not parseable or before deauth")
    return ("UNEXPECTED — client missing from post-deauth airodump "
            "(PMF should have kept them associated)")


def _last_seen_from_csv(csv_path: Path, client: str) -> datetime | None:
    """Parse the Last-time-seen column for `client` from the station table."""
    text = csv_path.read_text(errors="replace").splitlines()
    in_station = False
    for line in text:
        stripped = line.strip()
        if stripped.startswith("Station MAC"):
            in_station = True
            continue
        if not in_station or not stripped:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        if parts[0].upper() == client:
            try:
                return datetime.strptime(parts[2], "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=timezone.utc)
            except ValueError:
                return None
    return None
