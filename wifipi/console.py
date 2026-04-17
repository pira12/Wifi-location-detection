"""Interactive REPL for wifipi. Built on cmd2."""

from __future__ import annotations

import importlib
import pkgutil
import textwrap
import time
from pathlib import Path
from typing import Any

import cmd2
from cmd2 import ansi

from . import inventory as inventory_mod
from .ifaces import InterfaceManager, Role, parse_iw_dev
from .jobs import JobManager, JobState
from .loot import LootManager
from .module import Module, RunContext
from .options import OptionSpec, OptionStore
from .procutil import missing_tools, run as run_proc


def discover_modules() -> list[type[Module]]:
    """Walk wifipi.modules.*, return every Module subclass."""
    import wifipi.modules as pkg

    found: list[type[Module]] = []
    for _, modname, _ in pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + "."):
        m = importlib.import_module(modname)
        for name in dir(m):
            obj = getattr(m, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, Module)
                and obj is not Module
                and obj.NAME
            ):
                found.append(obj)
    # Deduplicate (a class can be imported into multiple modules).
    by_name: dict[str, type[Module]] = {}
    for cls in found:
        by_name[cls.NAME] = cls
    return sorted(by_name.values(), key=lambda c: c.NAME)


class WifipiApp(cmd2.Cmd):
    intro = ""   # we print our own banner in __main__
    prompt = "wifipi > "

    def __init__(self, repo_root: Path):
        super().__init__(allow_cli_args=False, include_py=False, include_ipy=False)
        self.repo_root = repo_root
        self.loot = LootManager(repo_root / "loot")
        self.ifaces = InterfaceManager()
        self.jobs = JobManager(on_finish=self._on_job_finish)
        self._modules: dict[str, type[Module]] = {
            cls.NAME: cls for cls in discover_modules()
        }
        self._globals = OptionStore(specs={})
        self._current: Module | None = None
        self._store: OptionStore | None = None
        self.inventory = inventory_mod.parse_inventory(repo_root / "lab-notes" / "inventory.md")

        # cmd2 niceties
        self.default_error = "[x] unknown command: {}"
        self.continuation_prompt = "... "

    # --- dynamic prompt -----------------------------------------------
    def _render_prompt(self) -> str:
        parts = ["wifipi"]
        running = self.jobs.running_count()
        if running:
            marker = f"[{running}j]"
            if running >= 3:
                marker = ansi.style(marker, fg=ansi.Fg.YELLOW)
            parts.append(marker)
        if self._current:
            parts.append(f"({self._current.NAME.split('/')[-1]})")
        return " ".join(parts) + " > "

    def postcmd(self, stop: bool, line: str) -> bool:  # type: ignore[override]
        self.prompt = self._render_prompt()
        return stop

    def preloop(self) -> None:
        self.prompt = self._render_prompt()

    def _on_job_finish(self, job) -> None:
        suffix = f"finished after {int(job.elapsed)}s"
        if job.state is JobState.FAILED:
            suffix = f"exited {job.returncode} after {int(job.elapsed)}s"
        elif job.state is JobState.KILLED:
            return  # killed-by-us: no alert needed
        line = ansi.style(
            f"[*] Job {job.id} ({job.name}) {suffix}  ->  {job.log_path.parent}",
            fg=ansi.Fg.CYAN,
        )
        try:
            self.async_alert(line)
        except Exception:
            print(line)

    # --- use / back / show ---------------------------------------------
    def do_use(self, args: cmd2.Statement) -> None:
        """use <module>  -- select a module by name."""
        name = args.arg_list[0] if args.arg_list else ""
        if not name:
            self.perror("usage: use <module>")
            return
        cls = self._modules.get(name)
        if cls is None:
            self.perror(f"no such module: {name}  (try `show modules`)")
            return
        missing = missing_tools(cls.REQUIRES_TOOLS)
        if missing:
            self.perror(f"missing tool(s) for {name}: {', '.join(missing)}")
            return
        self._current = cls()
        self._store = OptionStore(specs=cls.OPTIONS)
        self._store._global = self._globals._global  # share global dict
        self.poutput(f"[*] using {name}")

    def complete_use(self, text, line, begidx, endidx):
        return [n for n in self._modules if n.startswith(text)]

    def do_back(self, _args) -> None:
        """back  -- leave the current module."""
        self._current = None
        self._store = None

    def do_show(self, args: cmd2.Statement) -> None:
        """show modules | show options"""
        what = (args.arg_list[0] if args.arg_list else "").lower()
        if what == "modules":
            self._show_modules()
        elif what == "options":
            self._show_options()
        else:
            self.perror("usage: show modules | show options")

    def _show_modules(self) -> None:
        rows = [
            (cls.NAME, cls.CATEGORY, cls.DESCRIPTION)
            for cls in sorted(self._modules.values(), key=lambda c: c.NAME)
        ]
        if not rows:
            self.poutput("(no modules loaded)")
            return
        width = max(len(r[0]) for r in rows)
        self.poutput(f"{'NAME'.ljust(width)}  CATEGORY  DESCRIPTION")
        for name, cat, desc in rows:
            self.poutput(f"{name.ljust(width)}  {cat.ljust(8)}  {desc}")

    def _show_options(self) -> None:
        if self._current is None or self._store is None:
            self.perror("no module selected (use `use <name>`)")
            return
        resolved = self._store.resolve_all()
        rows = []
        for key, spec in self._current.OPTIONS.items():
            r = resolved[key]
            val = "" if r.value is None else str(r.value)
            req = "yes" if spec.required else "no"
            rows.append((key, val, r.source, req, spec.description))
        if not rows:
            self.poutput("(no options)")
            return
        widths = [max(len(r[i]) for r in rows + [("KEY","VALUE","SOURCE","REQ","DESCRIPTION")]) for i in range(5)]
        hdr = ("KEY", "VALUE", "SOURCE", "REQ", "DESCRIPTION")
        line = "  ".join(h.ljust(w) for h, w in zip(hdr, widths))
        self.poutput(line)
        for r in rows:
            self.poutput("  ".join(s.ljust(w) for s, w in zip(r, widths)))

    def do_search(self, args: cmd2.Statement) -> None:
        """search <keyword>  -- filter modules by name or description."""
        kw = (args.arg_list[0] if args.arg_list else "").lower()
        if not kw:
            self.perror("usage: search <keyword>")
            return
        hits = [
            (c.NAME, c.DESCRIPTION) for c in self._modules.values()
            if kw in c.NAME.lower() or kw in c.DESCRIPTION.lower()
        ]
        if not hits:
            self.poutput("(no matches)")
            return
        for name, desc in sorted(hits):
            self.poutput(f"{name}  —  {desc}")

    def do_info(self, args: cmd2.Statement) -> None:
        """info <module>"""
        name = args.arg_list[0] if args.arg_list else ""
        cls = self._modules.get(name)
        if cls is None:
            self.perror(f"no such module: {name}")
            return
        self.poutput(f"{cls.NAME}  ({cls.CATEGORY})")
        self.poutput("")
        self.poutput(textwrap.fill(cls.DESCRIPTION, width=78))
        self.poutput("")
        self.poutput(f"Blocking:     {cls.BLOCKING}")
        self.poutput(f"Confirmation: {cls.REQUIRES_CONFIRMATION}")
        self.poutput(f"Tools:        {', '.join(cls.REQUIRES_TOOLS) or '-'}")
        self.poutput("Options:")
        for key, spec in cls.OPTIONS.items():
            req = "required" if spec.required else "optional"
            default = f" (default: {spec.default})" if spec.default is not None else ""
            self.poutput(f"  {key}  [{req}{default}]  — {spec.description}")

    # --- set / setg / unset --------------------------------------------
    def do_set(self, args: cmd2.Statement) -> None:
        """set KEY VALUE  -- set option on the current module."""
        if len(args.arg_list) < 2:
            self.perror("usage: set KEY VALUE")
            return
        key, value = args.arg_list[0], " ".join(args.arg_list[1:])
        if self._store is None:
            self.perror("no module selected (use `use <name>`)")
            return
        try:
            self._store.set_local(key, value)
        except KeyError as e:
            self.perror(str(e))

    def do_setg(self, args: cmd2.Statement) -> None:
        """setg KEY VALUE  -- set session-global option."""
        if len(args.arg_list) < 2:
            self.perror("usage: setg KEY VALUE")
            return
        key, value = args.arg_list[0], " ".join(args.arg_list[1:])
        self._globals.set_global(key, value)
        if self._store is not None:
            # Re-share the dict in case someone unset_locally
            self._store._global = self._globals._global

    def do_unset(self, args: cmd2.Statement) -> None:
        """unset KEY"""
        key = args.arg_list[0] if args.arg_list else ""
        if self._store is None:
            self.perror("no module selected")
            return
        self._store.unset_local(key)

    def do_unsetg(self, args: cmd2.Statement) -> None:
        """unsetg KEY"""
        key = args.arg_list[0] if args.arg_list else ""
        self._globals.unset_global(key)

    # --- run ------------------------------------------------------------
    def do_run(self, _args) -> None:
        """run  -- execute the current module."""
        if self._current is None or self._store is None:
            self.perror("no module selected")
            return
        mod = self._current
        missing = self._store.missing_required()
        if missing:
            self.perror(f"missing required options: {', '.join(missing)}")
            return

        opts = {k: r.value for k, r in self._store.resolve_all().items() if r.value is not None}
        for role in Role:
            val = self.ifaces.get(role)
            if val is not None:
                opts[role.value] = val

        if mod.REQUIRES_CONFIRMATION:
            self._confirm_attack(mod, opts)

        loot_dir = self.loot.new_run(mod.LOOT_SUBDIR or mod.CATEGORY, mod.NAME)
        log_path = loot_dir / "run.log"

        ctx = RunContext(
            options=opts,
            loot_dir=loot_dir,
            log_path=log_path,
            ifaces=self.ifaces,
            jobs=self.jobs,
            loot=self.loot,
        )

        if mod.BLOCKING:
            try:
                rc = mod.run(ctx)
            except KeyboardInterrupt:
                self.poutput("\n[*] cancelled")
                return
            if rc == 0:
                self.poutput(f"[+] {mod.NAME} finished  ->  {loot_dir}")
            else:
                self.perror(f"{mod.NAME} exited {rc}  (see {log_path})")
        else:
            # Default OUTPUT_PREFIX to something under the loot dir so captures
            # land alongside the run log.
            if "OUTPUT_PREFIX" in mod.OPTIONS and opts.get("OUTPUT_PREFIX") is None:
                opts["OUTPUT_PREFIX"] = str(loot_dir / "capture")
            opts["_WORKDIR"] = str(loot_dir)
            argv = mod.build_argv(opts)
            job = self.jobs.start(name=mod.NAME, argv=argv, log_path=log_path)
            self.poutput(f"[+] Job {job.id} started: {mod.NAME}  ->  {loot_dir}")

    def _confirm_attack(self, mod: Module, opts: dict) -> None:
        self.pwarning(f"[!] {mod.NAME}")
        for key in ("BSSID", "CLIENT", "SSID", "CHANNEL"):
            if key in opts:
                self.pwarning(f"    {key}={opts[key]}")
        self.pwarning("    Confirm targets are in lab-notes/inventory.md. Firing in 3s...")
        confirm = self._globals.resolve_value("CONFIRM")
        if str(confirm).lower() != "false":
            time.sleep(3)

    # --- iface / ifaces --------------------------------------------------
    def do_ifaces(self, _args) -> None:
        """ifaces  -- list wireless interfaces and role assignments."""
        try:
            out = run_proc(["iw", "dev"], capture_output=True, text=True).stdout
        except FileNotFoundError:
            self.perror("`iw` not installed — install with: apt install iw")
            return
        rows = parse_iw_dev(out)
        roles = {name: role for role, name in self.ifaces.all_assignments().items()}
        hdr = f"{'NAME'.ljust(12)} {'MODE'.ljust(10)} {'PHY'.ljust(8)} ROLE"
        self.poutput(hdr)
        for info in rows:
            role = roles.get(info.name)
            label = role.name if role else "-"
            self.poutput(f"{info.name.ljust(12)} {info.mode.ljust(10)} {info.phy.ljust(8)} {label}")

    def do_iface(self, args: cmd2.Statement) -> None:
        """iface set <role> <name> | up <role> | down <role> | auto"""
        if not args.arg_list:
            self.perror("usage: iface set|up|down|auto ...")
            return
        sub = args.arg_list[0]
        rest = args.arg_list[1:]
        if sub == "set":
            if len(rest) < 2:
                self.perror("usage: iface set <role> <name>")
                return
            try:
                role = Role.from_str(rest[0])
            except ValueError as e:
                self.perror(str(e))
                return
            self.ifaces.assign(role, rest[1])
            self.poutput(f"[*] {role.name} -> {rest[1]}")
        elif sub == "up":
            if not rest:
                self.perror("usage: iface up <role>")
                return
            self._iface_up(Role.from_str(rest[0]))
        elif sub == "down":
            if not rest:
                self.perror("usage: iface down <role>")
                return
            self._iface_down(Role.from_str(rest[0]))
        elif sub == "auto":
            self._iface_auto()
        else:
            self.perror("usage: iface set|up|down|auto ...")

    def _iw_dev(self) -> list:
        out = run_proc(["iw", "dev"], capture_output=True, text=True).stdout
        return parse_iw_dev(out)

    def _iface_up(self, role: Role) -> None:
        name = self.ifaces.get(role)
        if name is None:
            self.perror(f"{role.name} is not assigned (use `iface set {role.name.lower().replace('_iface','')} <name>`)")
            return
        if role is Role.MON:
            before = {i.name for i in self._iw_dev()}
            run_proc(["airmon-ng", "check", "kill"])
            run_proc(["airmon-ng", "start", name])
            after = self._iw_dev()
            # Prefer a newly-appeared monitor interface (airmon-ng renamed).
            new_mons = [i for i in after if i.mode == "monitor" and i.name not in before]
            if new_mons:
                new_name = new_mons[0].name
                if new_name != name:
                    self.ifaces.rename(old=name, new=new_name)
                self.poutput(f"[*] MON_IFACE -> {new_name} (monitor mode)")
                return
            # Otherwise: our interface went into monitor mode in place.
            for info in after:
                if info.name == name and info.mode == "monitor":
                    self.poutput(f"[*] MON_IFACE -> {name} (monitor mode in place)")
                    return
            self.perror(f"couldn't find a monitor-mode interface after airmon-ng start {name}")
        elif role is Role.ATTACK:
            self.ifaces.assign(Role.ATTACK, self.ifaces.get(Role.MON) or name)
            self.poutput(f"[*] ATTACK_IFACE -> {self.ifaces.get(Role.ATTACK)}")
        elif role is Role.AP:
            # Rogue-AP adapter is left in managed mode; hostapd binds it.
            run_proc(["ip", "link", "set", name, "up"])
            self.poutput(f"[*] AP_IFACE -> {name} (managed, ready for hostapd)")

    def _iface_down(self, role: Role) -> None:
        name = self.ifaces.get(role)
        if name is None:
            return
        if role is Role.MON:
            run_proc(["airmon-ng", "stop", name])
        else:
            run_proc(["ip", "link", "set", name, "down"])
        self.ifaces.clear(role)
        self.poutput(f"[*] {role.name} down")

    def _iface_auto(self) -> None:
        ifaces = [i for i in self._iw_dev() if i.name != "wlan0"]
        if not ifaces:
            # Fall back to wlan0 if that's all we have.
            ifaces = self._iw_dev()
        if not ifaces:
            self.perror("no wireless interfaces detected (plug USB adapter?)")
            return
        # Pick the first monitor-capable adapter (heuristic: not built-in wlan0).
        mon = next((i for i in ifaces if i.name != "wlan0"), ifaces[0])
        self.ifaces.assign(Role.MON, mon.name)
        self._iface_up(Role.MON)
        others = [i for i in self._iw_dev() if i.name != self.ifaces.get(Role.MON) and i.name != "wlan0"]
        if others:
            self.ifaces.assign(Role.AP, others[0].name)
            self.poutput(f"[*] AP_IFACE -> {others[0].name}")
            self.ifaces.assign(Role.ATTACK, self.ifaces.get(Role.MON))
        else:
            self.ifaces.assign(Role.ATTACK, self.ifaces.get(Role.MON))
            self.pwarning("[!] only one usable adapter — evil-twin will refuse to run")

    # --- jobs / status ---------------------------------------------------
    def do_jobs(self, _args) -> None:
        """jobs  -- list background jobs."""
        jobs = self.jobs.list()
        if not jobs:
            self.poutput("(no jobs)")
            return
        hdr = f"{'ID':>3}  {'MODULE'.ljust(24)} {'STATE'.ljust(8)} {'ELAPSED'.ljust(8)} PID"
        self.poutput(hdr)
        for j in jobs:
            self.poutput(
                f"{j.id:>3}  {j.name.ljust(24)} {j.state.value.ljust(8)} "
                f"{int(j.elapsed):>4}s    {j.pid}"
            )

    def do_kill(self, args: cmd2.Statement) -> None:
        """kill <id>  -- terminate a background job."""
        if not args.arg_list:
            self.perror("usage: kill <id>")
            return
        try:
            job_id = int(args.arg_list[0])
        except ValueError:
            self.perror("job id must be an integer")
            return
        if self.jobs.kill(job_id):
            self.poutput(f"[*] Job {job_id} killed")
        else:
            self.perror(f"no running job {job_id}")

    def do_status(self, _args) -> None:
        """status  -- interfaces + jobs + roles, all at once."""
        self.poutput("Interface roles:")
        assignments = self.ifaces.all_assignments()
        if not assignments:
            self.poutput("  (none — try `iface auto`)")
        else:
            for role, name in assignments.items():
                self.poutput(f"  {role.name.ljust(14)} {name}")
        self.poutput("")
        self.do_jobs(None)

    # --- loot ----------------------------------------------------------
    def do_loot(self, args: cmd2.Statement) -> None:
        """loot [category] | loot clean"""
        sub = args.arg_list[0] if args.arg_list else ""
        if sub == "clean":
            self.loot.clean()
            self.poutput("[*] loot/ cleaned")
            return
        cat = sub or None
        runs = self.loot.recent(category=cat, limit=20)
        if not runs:
            self.poutput("(no artefacts yet)")
            return
        for r in runs:
            self.poutput(f"  {r.relative_to(self.loot.root)}")

    # --- inventory -----------------------------------------------------
    def do_inventory(self, _args) -> None:
        """inventory  -- show MACs/BSSIDs from lab-notes/inventory.md."""
        inv = self.inventory
        self.poutput("BSSIDs in scope:")
        for m in inv.bssids or ["(none)"]:
            self.poutput(f"  {m}")
        self.poutput("Clients in scope:")
        for m in inv.clients or ["(none)"]:
            self.poutput(f"  {m}")

    # --- exit guard ----------------------------------------------------
    def do_exit(self, _args) -> bool:
        """exit  -- exit with a running-jobs guard."""
        running = self.jobs.running()
        if not running:
            return True
        names = ", ".join(j.name for j in running)
        self.pwarning(f"[!] {len(running)} background jobs still running: {names}")
        choice = input("    [k]ill them and exit, [d]etach (leave running), [c]ancel? ").strip().lower()
        if choice.startswith("k"):
            self.jobs.kill_all()
            return True
        if choice.startswith("d"):
            self.poutput("[*] detaching; jobs continue in the background")
            return True
        self.poutput("[*] cancelled")
        return False

    def do_quit(self, args) -> bool:
        return self.do_exit(args)
