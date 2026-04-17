"""util/cleanup — revert monitor interfaces, flush iptables, restart NM."""

from __future__ import annotations

from wifipi.ifaces import Role, parse_iw_dev
from wifipi.module import Module, RunContext
from wifipi.procutil import run as run_proc


class Cleanup(Module):
    NAME = "util/cleanup"
    CATEGORY = "util"
    DESCRIPTION = "Tear down rogue AP, flush iptables, return adapters to managed."
    REQUIRES_TOOLS = ["iw", "iptables", "airmon-ng"]
    BLOCKING = True

    def run(self, ctx: RunContext) -> int:
        ln = ctx.log_path.open("a")

        def sh(argv: list[str]) -> None:
            ln.write(f"$ {' '.join(argv)}\n")
            ln.flush()
            run_proc(argv, stdout=ln, stderr=ln)

        # kill any rogue AP services we might have launched
        run_proc(["pkill", "-f", "hostapd"], stdout=ln, stderr=ln)
        run_proc(["pkill", "-f", "dnsmasq"], stdout=ln, stderr=ln)

        sh(["iptables", "-t", "nat", "-F", "POSTROUTING"])
        sh(["iptables", "-F", "FORWARD"])
        sh(["sysctl", "-w", "net.ipv4.ip_forward=0"])

        iw = run_proc(["iw", "dev"], capture_output=True, text=True)
        for info in parse_iw_dev(iw.stdout):
            if info.mode == "monitor":
                sh(["airmon-ng", "stop", info.name])

        run_proc(["systemctl", "restart", "NetworkManager"], stdout=ln, stderr=ln)

        ctx.ifaces.clear()
        ln.close()
        print("[*] cleanup done")
        return 0
