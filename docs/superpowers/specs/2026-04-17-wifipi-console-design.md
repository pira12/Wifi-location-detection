# wifipi — Metasploit-style Console Design

**Date:** 2026-04-17
**Status:** Approved (awaiting spec review)
**Author:** pira

## Problem

The current repo is a pile of numbered shell scripts (`00-prereq-check.sh` …
`11-handshake-dual.sh`) plus a README that maps which script does what. It
works but:

- The user must remember which script to run, in what order, with which
  flags.
- Interface names, BSSIDs, channels, and client MACs get re-typed on every
  script invocation.
- Long-running processes (`airodump-ng`, `hostapd`) leak into shell
  background jobs with no unified management.
- Output artefacts land wherever the user happens to be `cd`'d into.

We want a `msfconsole`-style interactive Python console that replaces the
scripts, organises functionality into discoverable modules, carries state
across commands, runs long tasks as managed background jobs, and drops all
artefacts into one timestamped `loot/` tree.

## Goals

- Single entry point (`sudo ./wifipi`) instead of 12 scripts.
- Persistent session state: set `BSSID`, `CHANNEL`, `CLIENT`, `IFACE` once;
  every module reads them.
- Role-based interface management: `MON_IFACE`, `ATTACK_IFACE`, `AP_IFACE`
  — set the roles once, forget about `-i wlan1mon` forever.
- Background jobs system with always-visible counter and finish
  notifications, so nothing runs unnoticed.
- Consistent `loot/` layout with timestamped per-run directories.
- Keep the school-project safety posture: legal banner at startup, explicit
  pre-attack confirmation, `lab-notes/inventory.md` still read at startup.

## Non-Goals

- Workspaces / multi-engagement state.
- A database of discovered APs beyond the CSV `airodump-ng` already emits.
- Any new attack capability (no PMKID, no WPS, no WPA3 downgrade, no PMF
  bypass). This design makes the existing scripts easier to use; it does
  not add offensive features.
- GUI or web UI — console only.
- Backwards compatibility with the old shell scripts. They move to
  `scripts/legacy/` as reference material; the console is the tool.

## High-level architecture

```
sudo ./wifipi  →  python3 -m wifipi
                  ├─ root check (EUID == 0 or die)
                  ├─ legal banner (press Enter)
                  ├─ load inventory (lab-notes/inventory.md)
                  ├─ discover modules (walk wifipi/modules/)
                  └─ cmd2 REPL
                        ├─ global options store (BSSID, CHANNEL, …)
                        ├─ interface role manager (MON/ATTACK/AP)
                        ├─ job manager (threads + subprocess.Popen)
                        ├─ loot manager (timestamped dirs)
                        └─ current module (or none)
```

External dependencies: `cmd2` (one pip package). Everything else is
stdlib. The console shells out to the same system tools the scripts
already use: `airmon-ng`, `airodump-ng`, `aireplay-ng`, `aircrack-ng`,
`iw`, `hostapd`, `dnsmasq`, `iptables`.

## Repository layout

```
wifipi                        # shell wrapper: exec python3 -m wifipi "$@"
wifipi/
  __init__.py
  __main__.py                 # entry point, root check, legal banner
  console.py                  # cmd2 App: prompt, commands, async alerts
  module.py                   # Module base class + OptionSpec
  options.py                  # global options store + lookup logic
  ifaces.py                   # interface role manager + `iw dev` parsing
  jobs.py                     # JobManager: thread + subprocess lifecycle
  loot.py                     # timestamped dir creation, `loot` command
  procutil.py                 # subprocess wrappers + tool discovery
  inventory.py                # reads lab-notes/inventory.md
  modules/
    __init__.py
    recon/{__init__.py, scan.py, target.py}
    attack/{__init__.py, deauth_targeted.py, deauth_broadcast.py,
            deauth_loop.py, handshake.py, handshake_dual.py,
            evil_twin.py}
    post/{__init__.py, crack.py}
    util/{__init__.py, prereq_check.py, cleanup.py}
configs/                      # unchanged: hostapd/dnsmasq templates
lab-notes/inventory.md        # unchanged
scripts/legacy/               # old bash scripts, preserved for reference
requirements.txt              # cmd2
loot/                         # git-ignored, created at first run
README.md                     # rewritten around the console
TODO.md / REPORT.md           # unchanged aside from command updates
docs/superpowers/specs/       # this file
```

## Module system

### Base class

```python
class Module:
    NAME: str                   # e.g. "attack/deauth-targeted"
    DESCRIPTION: str
    CATEGORY: str               # "recon" | "attack" | "post" | "util"
    OPTIONS: dict[str, OptionSpec]
    REQUIRES_TOOLS: list[str]   # e.g. ["aireplay-ng", "iw"]
    BLOCKING: bool              # True → foreground, False → background job
    REQUIRES_CONFIRMATION: bool # True → pre-run safety prompt
    LOOT_SUBDIR: str | None     # e.g. "handshakes" — base class creates
                                # loot/<subdir>/<ts>-<name>/ and passes it in

    def build_argv(self, opts: dict) -> list[str]: ...  # pure, testable
    def run(self, opts: dict, ctx: RunContext) -> None: ...
```

`OptionSpec` carries `required: bool`, `default`, `description`, `type`
(string / int / mac / bssid / iface / role / path).

### Option resolution

Two scopes:

- **Global** — on the console, keyed by well-known names (`BSSID`,
  `CHANNEL`, `CLIENT`, `SSID`, `WORDLIST`, `UPSTREAM_IFACE`, plus the
  interface roles `MON_IFACE`, `ATTACK_IFACE`, `AP_IFACE`). Modules never
  take a raw interface name — they always resolve one of the three roles.
- **Local** — on the current module, set via `set KEY VAL`.

When a module resolves an option: local → global → default. `show options`
displays a merged table with a `source` column (`local` / `global` /
`default`) so the origin of every value is visible.

### Built-in commands

| Command | Purpose |
| --- | --- |
| `use <name>` | Select a module (tab-completable). |
| `back` | Leave current module (globals persist). |
| `show modules` | List all loaded modules with category + description. |
| `show options` | Options for the current module + merged source column. |
| `search <kw>` | Filter modules by name or description. |
| `info <name>` | Long description + options + tools required. |
| `set KEY VAL` | Local option on current module. |
| `setg KEY VAL` | Global option. |
| `unset KEY` / `unsetg KEY` | Clear local / global. |
| `run` | Execute current module. Foreground or background per `BLOCKING`. |
| `jobs` | List running/finished background jobs. |
| `kill <id>` | SIGTERM (then SIGKILL after 3s) the named job. |
| `status` | Interface roles + all jobs, full table. |
| `ifaces` | List wireless interfaces from `iw dev` + assigned roles. |
| `iface set <role> <name>` | Assign adapter to role. |
| `iface up <role>` | Bring adapter into the right mode for its role. |
| `iface down <role>` | Revert adapter to managed mode. |
| `iface auto` | Auto-assign for the dual-adapter Pi setup. |
| `loot` | List recent artefacts; `loot <module>` filters; `loot clean` wipes. |
| `inventory` | Print MACs/BSSIDs parsed from `lab-notes/inventory.md`. |
| `exit` / `quit` | Exit with running-jobs guard (see below). |

## Interface role management

Three session-global roles:

- `MON_IFACE` — monitor / capture adapter. Used by scan, target-capture,
  handshake capture, and the deauth modules.
- `ATTACK_IFACE` — injection adapter. Used by `attack/handshake-dual` where
  capture and injection live on separate adapters.
- `AP_IFACE` — rogue-AP adapter. Runs `hostapd` for the evil-twin module.

Modules read their interfaces by role, not by name, so once roles are set
the user never passes `-i wlan1mon` again.

### `iface up mon` behaviour

- Runs `airmon-ng check kill` equivalent (kills NetworkManager /
  wpa_supplicant interference, same as the current `01-monitor-up.sh`).
- Starts monitor mode with `airmon-ng start <iface>` or `iw` fallback.
- Rewrites the role value to the new monitor-mode name (`wlan1` →
  `wlan1mon`), so downstream modules see the correct interface.

### `iface auto`

For the user's two-adapter Raspberry Pi:

1. Enumerate `iw dev` wireless interfaces.
2. Pick an injection-capable adapter → `MON_IFACE` + `ATTACK_IFACE`,
   put it into monitor mode. Injection capability is inferred from the
   driver / chipset via `iw phy` (e.g., `ath9k_htc` for the Alfa
   AWUS036NHA the project targets). If we can't tell, pick the first
   adapter and print a warning telling the user to verify with
   `sudo aireplay-ng --test wlan1mon` manually.
3. Assign the other adapter → `AP_IFACE`, leave it in managed mode so
   `hostapd` can claim it.
4. Print the chosen assignments so the user confirms visually.

### Single-adapter fallback

If only one wireless adapter is present:

- `MON_IFACE` and `ATTACK_IFACE` point at the same monitor interface.
- `AP_IFACE` is unset. Modules that need a separate AP adapter
  (`attack/evil-twin`) refuse to run with a clear "need a second
  adapter" error.

### Cleanup

`util/cleanup` reverts every assigned role to managed mode, flushes
iptables NAT rules the evil twin added, disables IP forwarding, restarts
NetworkManager, and clears the roles.

## Jobs system

- Each background module's `run` launches a `subprocess.Popen` inside a
  Python thread managed by `JobManager`.
- `run` prints `[+] Job 0 started: recon/scan` and returns to the prompt
  immediately.
- Each job carries: `id`, `module_name`, `started_at`, `pid`,
  `status` (`running` / `finished` / `killed` / `failed`), `log_path`.
- `jobs` lists them in a table. Finished jobs are displayed once (with
  "finished Xs ago") and pruned on the next call.
- `kill <id>` sends `SIGTERM`, waits 3s, then `SIGKILL`.
- On console `exit` with jobs running, prompt: "[k]ill / [d]etach /
  [c]ancel". Detaching leaves processes running (user's explicit choice);
  killing waits for all to terminate before exiting.
- Ctrl-C at the prompt cancels whatever foreground operation is active
  (or prints a "use `kill <id>` or `exit` to stop background jobs"
  hint); it does not kill the console.

### Output streaming

- A job's combined stdout/stderr streams to
  `loot/<subdir>/<timestamp>-<module>/run.log`.
- `job tail <id>` tails a running job's log (non-blocking: prints last
  50 lines, then `-f` style until Ctrl-C returns to prompt).
- Jobs never write directly to the console (would clobber the prompt).
- Exception: `cmd2.async_alert` prints a single line above the prompt
  when a job exits unexpectedly, so crashes don't pass silently.

### Live visibility

Always-on visibility of background work:

- Dynamic prompt segment `[<n>j]` when jobs > 0:
  - `wifipi >` (idle)
  - `wifipi [2j] >` (two jobs)
  - `wifipi (deauth-targeted) [2j] >` (inside a module)
  - The segment turns yellow at `n ≥ 3`.
- `async_alert` line above prompt when a job finishes on its own:
  `[*] Job 1 (recon/scan) finished after 4m 12s  →  loot/scans/...`
- `status` command prints interface roles + all jobs in one table for a
  complete "what's happening right now" view.

## Loot directory

```
loot/
  scans/2026-04-17_18-30-12-recon-scan/
    airodump-01.cap, airodump-01.csv, run.log
  handshakes/2026-04-17_18-35-04-handshake/
    handshake-01.cap, run.log, cracked.txt
  evil-twin/2026-04-17_18-40-00-eviltwin/
    hostapd.log, dnsmasq.log, rogue.pcap, run.log
  crack/2026-04-17_18-55-00-crack/
    cracked.txt, run.log
```

- Base `Module` class builds `loot/<LOOT_SUBDIR>/<timestamp>-<name>/` at
  `run` start and passes the path to the module via `RunContext`.
- `loot` lists the 20 most recent artefact directories across all
  subdirs. `loot <module>` filters to one subdir. `loot clean`
  interactively confirms, then wipes the whole tree.
- `loot/` is added to `.gitignore` so captures never end up in git.

## Safety and legal layer

- Red startup banner summarises the existing `README.md` disclaimer in
  5 lines: "targets must be yours or explicitly authorised; Dutch/EU
  statute applies." Requires pressing Enter to continue. No automatic
  skip.
- Modules with `REQUIRES_CONFIRMATION = True` (every deauth variant,
  evil twin) print a yellow pre-run block showing the exact BSSID /
  CLIENT / CHANNEL / IFACE and wait 3s before firing. This matches the
  existing `warn + sleep 3` pattern.
- `setg CONFIRM false` skips the sleep but still prints the summary.
- `inventory` command prints MACs/BSSIDs recorded in
  `lab-notes/inventory.md` at startup. Informational; no enforcement
  (soft gate only, as decided during brainstorming).

## Module mapping

| Old script | New module | Mode |
| --- | --- | --- |
| `00-prereq-check.sh` | `util/prereq-check` | foreground |
| `01-monitor-up.sh` | folded into `iface up mon` | — |
| `02-scan.sh` | `recon/scan` | background |
| `03-target-capture.sh` | `recon/target` | background |
| `04-deauth-targeted.sh` | `attack/deauth-targeted` | foreground |
| `04-deauth-broadcast.sh` | `attack/deauth-broadcast` | foreground |
| `05-crack-handshake.sh` | `post/crack` | foreground |
| `06-evil-twin-up.sh` | folded into `attack/evil-twin` | — |
| `07-cleanup.sh` | `util/cleanup` | foreground |
| `08-handshake-capture.sh` | `attack/handshake` | foreground (orchestrator) |
| `09-deauth-loop.sh` | `attack/deauth-loop` | background |
| `10-evil-twin-attack.sh` | `attack/evil-twin` | background |
| `11-handshake-dual.sh` | `attack/handshake-dual` | foreground (orchestrator) |

### Module option summary

| Module | Required options | Optional options | Uses role |
| --- | --- | --- | --- |
| `util/prereq-check` | — | — | — |
| `util/cleanup` | — | — | all roles |
| `recon/scan` | — | `CHANNEL` | `MON_IFACE` |
| `recon/target` | `BSSID`, `CHANNEL` | `OUTPUT_PREFIX` | `MON_IFACE` |
| `attack/deauth-targeted` | `BSSID`, `CLIENT`, `CHANNEL` | `COUNT` (10) | `MON_IFACE` |
| `attack/deauth-broadcast` | `BSSID`, `CHANNEL` | `COUNT` (20) | `MON_IFACE` |
| `attack/deauth-loop` | `BSSID`, `CHANNEL` | `CLIENT`, `INTERVAL` (5), `BURST` (5) | `MON_IFACE` |
| `attack/handshake` | `BSSID`, `CLIENT`, `CHANNEL` | `WORDLIST`, `TIMEOUT` (60) | `MON_IFACE` |
| `attack/handshake-dual` | `BSSID`, `CLIENT`, `CHANNEL` | `WORDLIST`, `TIMEOUT` (120) | `MON_IFACE` + `ATTACK_IFACE` |
| `attack/evil-twin` | `BSSID`, `SSID`, `CHANNEL` | `CLIENT`, `WPA_PASSPHRASE`, `UPSTREAM_IFACE` | `MON_IFACE` + `AP_IFACE` |
| `post/crack` | `BSSID`, `WORDLIST`, `CAPTURE_FILE` | — | — |

## Typical session

```
$ sudo ./wifipi

 ╔════════════════════════════════════════════════════════════════╗
 ║ wifipi — WiFi Pineapple Equivalent on Raspberry Pi             ║
 ║ For authorised lab use only. Targets must be YOUR devices      ║
 ║ (see lab-notes/inventory.md). Dutch/EU law applies.            ║
 ║ Press Enter to acknowledge.                                    ║
 ╚════════════════════════════════════════════════════════════════╝
 [loaded 12 modules; inventory: 2 BSSIDs, 3 clients]

wifipi > iface auto
[*] wlan1 → MON_IFACE (monitor mode: wlan1mon)  [injection-capable]
[*] wlan2 → AP_IFACE

wifipi > use recon/scan
wifipi (recon/scan) > run
[+] Job 0 started: recon/scan → loot/scans/2026-04-17_18-30-12-recon-scan/

wifipi [1j] (recon/scan) > back
wifipi [1j] > use attack/deauth-targeted
wifipi [1j] (deauth-targeted) > setg BSSID AA:BB:CC:11:22:33
wifipi [1j] (deauth-targeted) > setg CLIENT DD:EE:FF:44:55:66
wifipi [1j] (deauth-targeted) > setg CHANNEL 11
wifipi [1j] (deauth-targeted) > show options
  KEY      VALUE                SOURCE    REQUIRED
  BSSID    AA:BB:CC:11:22:33    global    yes
  CLIENT   DD:EE:FF:44:55:66    global    yes
  CHANNEL  11                   global    yes
  COUNT    10                   default   no

wifipi [1j] (deauth-targeted) > run
[!] Targeted deauth
    BSSID=AA:BB:CC:11:22:33 CLIENT=DD:EE:FF:44:55:66 CH=11 via wlan1mon
    Confirm both MACs are in lab-notes/inventory.md. Firing in 3s...
[*] aireplay-ng → deauth x10 sent

wifipi [1j] (deauth-targeted) > kill 0
[*] Job 0 (recon/scan) killed

wifipi > exit
```

## Error handling

| Failure | Behaviour |
| --- | --- |
| Missing external tool at `use` | `[x] missing tool: aireplay-ng — install with apt install aircrack-ng`. Module refuses to load; REPL stays open. |
| Missing interface role at `run` | `[x] MON_IFACE not set. Run `iface auto` or `iface set mon <name>`.` |
| Required option missing at `run` | `[x] missing options: BSSID, CLIENT. See `show options`.` |
| Subprocess non-zero exit | `[x] airodump-ng exited 1 (see loot/.../run.log)` — no Python traceback. |
| Console started as non-root | `[x] wifipi must run as root (sudo ./wifipi).` and exits. |
| Ctrl-C at prompt | Cancels current foreground operation; returns to prompt. Background jobs untouched. |
| Ctrl-C during foreground `run` | Same as above: terminates the child subprocess, returns to prompt. |
| Exit with jobs running | Prompt: `[k]ill / [d]etach / [c]ancel`. |

## Testing

`pytest` + `pytest-mock`. We can't simulate a real wireless adapter, so
testing targets the logic that doesn't touch hardware:

- **Option resolution** — local → global → default precedence, with
  `required` validation reporting the right missing keys.
- **Module discovery** — every file under `wifipi/modules/` imports
  cleanly and registers a `Module` subclass. Catches broken modules at
  CI time instead of at the REPL.
- **`iw dev` parsing** — fixtures of real `iw dev` output for 0-, 1-,
  and 2-adapter cases drive `ifaces.parse_iw_dev`.
- **Inventory parser** — markdown fixture → extracted MACs/BSSIDs.
- **Job lifecycle** — dummy `sleep` subprocess exercises start /
  finish-alert / kill / detach paths.
- **`build_argv`** per module — every module has a pure function that
  converts options to an argv list. Unit-tested without firing frames.

The "does it actually kick my phone off wifi" verification stays
manual — same as the current scripts — and is the subject of the
`REPORT.md` write-up.

## Risks

- **cmd2 API drift.** Pin the version in `requirements.txt` (cmd2 ~= 2.4
  at time of writing).
- **Python versions.** Kali ships Python 3.11+ — design targets 3.10 as
  floor. No 3.12-only syntax.
- **airmon-ng rename behaviour.** Newer `airmon-ng` sometimes keeps the
  original name (`wlan1`) instead of creating `wlan1mon`. `iface up mon`
  must re-read `iw dev` after the call to find the actual monitor
  interface name rather than assuming `<name>mon`.
- **Background subprocesses outliving the console.** Covered by the
  exit guard plus a `finally:` cleanup on SIGTERM/SIGHUP to the console
  itself.
- **Inventory is advisory only.** The soft-gate decision during
  brainstorming means a user can deauth anything. The legal banner +
  the pre-run summary are the only safeguards. This is an explicit
  trade-off (usability over enforcement).

## Open questions

None at design time. Ambiguities that come up during implementation go
into the plan as TODOs.
