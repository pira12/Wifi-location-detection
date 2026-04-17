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
these installed manually:

```bash
sudo apt install -y aircrack-ng hostapd dnsmasq iptables tcpdump iw
```

(`aircrack-ng` provides `airmon-ng`, `airodump-ng`, `aireplay-ng`, and
`aircrack-ng` itself.)

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
the tree.

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
