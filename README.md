# WiFi Pineapple Equivalent on Raspberry Pi

School project for SNE / Applied Security: build a Raspberry Pi setup
that reproduces the core capabilities of a Hak5 WiFi Pineapple, then
demonstrate a deauthentication attack against a device the author owns.

---

## Disclaimer — educational use only

**This repository is published strictly for educational and authorised
defensive-research use.** Every script in `scripts/` performs an
operation that, when used outside a controlled lab and against equipment
the operator does not own, is illegal in most jurisdictions — including
the Netherlands and the rest of the EU.

By using this code you agree that:

1. You will only target wireless equipment that **you own** or that you
   have **explicit, written authorisation** to test.
2. You accept full legal and ethical responsibility for what you do with
   these tools.
3. You will physically isolate your lab so that stray frames do not
   reach networks or devices outside your scope.
4. The authors of this repository accept no liability for misuse.

Relevant Dutch / EU statute (non-exhaustive):

- *Wetboek van Strafrecht* Art. 138ab — computer trespass
- *Wetboek van Strafrecht* Art. 139c / 139d — interception of
  communications
- *Telecommunicatiewet* — wilful radio interference

The legal prohibition is on **unauthorised access regardless of
intent**. "I was just testing" is not a defence if the target was not
yours.

`lab-notes/inventory.md` is a template for recording every BSSID and MAC
in scope. Fill it in before running anything — it is your evidence that
every target was your own device.

---

## Required deliverable

The graded deliverable for this assignment is **the deauth attack only**.
Everything else (handshake capture and offline crack, evil twin, PMF
mitigation demo, airgeddon walkthrough) is optional bonus material kept
in this repo in case you have time.

`TODO.md` walks through the required path; `REPORT.md` has placeholders
for the bonus sections you can delete if you skip them.

---

## Where to start

1. **`TODO.md`** — physical/hardware checklist. Read this first.
2. **`REPORT.md`** — writeup template. Fill in screenshots and
   observations as you go.
3. **`scripts/`** — shell helpers for each step (see reference below).
4. **`configs/`** — `hostapd` / `dnsmasq` configs.
5. **`lab-notes/inventory.md`** — record the MACs/BSSIDs of every
   in-scope device.

---

## File map

```
.
|- README.md
|- TODO.md                       <- what YOU need to do
|- REPORT.md                     <- writeup template
|- scripts/
|   |- lib/common.sh             <- shared shell helpers
|   |- 00-prereq-check.sh        <- verify tools + interfaces
|   |- 01-monitor-up.sh          <- enable monitor mode
|   |- 02-scan.sh                <- general airodump scan
|   |- 03-target-capture.sh      <- airodump locked to one AP
|   |- 04-deauth-targeted.sh     <- deauth ONE client (REQUIRED demo)
|   |- 04-deauth-broadcast.sh    <- deauth ALL clients of an AP
|   |- 05-crack-handshake.sh     <- offline WPA crack with wordlist
|   |- 06-evil-twin-up.sh        <- rogue AP only (manual workflow)
|   |- 07-cleanup.sh             <- tear everything down
|   |- 08-handshake-capture.sh   <- all-in-one: capture + (optional) crack
|   |- 09-deauth-loop.sh         <- continuous deauth (for evil twin pull)
|   `- 10-evil-twin-attack.sh    <- all-in-one evil twin orchestrator
|- configs/
|   |- hostapd-testap.conf       <- legit test AP (Pi #2)
|   |- hostapd-rogue.conf        <- evil-twin AP (Pi #1)
|   `- dnsmasq-rogue.conf        <- DHCP + DNS hijack for the rogue AP
`- lab-notes/
    `- inventory.md              <- record YOUR devices' MACs here
```

---

## Scripts reference

All scripts must be run with `sudo` unless noted. Run them from the
repository root: `sudo ./scripts/<name>.sh ...`.

### Setup

#### `00-prereq-check.sh`
Sanity-checks the Pi before you begin. Verifies that the required tools
(`airmon-ng`, `airodump-ng`, `aireplay-ng`, `aircrack-ng`, `hostapd`,
`dnsmasq`, `iw`, `iptables`) are installed, lists the wireless
interfaces, and prints the command you can run to verify monitor-mode +
packet-injection support on your USB adapter.

```bash
sudo ./scripts/00-prereq-check.sh
```

#### `01-monitor-up.sh`
Kills processes that interfere with monitor mode (NetworkManager,
wpa_supplicant, etc.) and puts the named wireless interface into monitor
mode. Output interface is usually `<name>mon` (e.g. `wlan1` →
`wlan1mon`).

```bash
sudo ./scripts/01-monitor-up.sh wlan1
```

### Reconnaissance

#### `02-scan.sh`
Runs `airodump-ng` on the monitor interface in channel-hopping mode.
Used to discover the BSSID and channel of your test AP and the MAC of
your client device. Ctrl-C to stop.

```bash
sudo ./scripts/02-scan.sh wlan1mon
```

#### `03-target-capture.sh`
Runs `airodump-ng` locked to one AP (specific BSSID + channel) and
writes a pcap (`<prefix>-NN.cap`). Use this in one terminal while you
fire deauth (script 04) in another — the WPA handshake gets captured
when the client reconnects.

```bash
sudo ./scripts/03-target-capture.sh -c 11 -b AA:BB:CC:11:22:33 -i wlan1mon -o capture
```

### The attack (required deliverable)

#### `04-deauth-targeted.sh`
Sends a burst of 802.11 deauthentication frames forged to look like they
came from the AP, addressed to one specific client. The client honours
the spoofed frame and disconnects. **This is the required deliverable.**

Locks the monitor interface to the right channel before firing
(otherwise the frames go out on whichever channel the radio drifted
to).

```bash
sudo ./scripts/04-deauth-targeted.sh \
    -a AA:BB:CC:11:22:33 \
    -c DD:EE:FF:44:55:66 \
    -i wlan1mon \
    -k 11
```

Flags: `-a` AP BSSID, `-c` client MAC, `-i` monitor iface, `-k` channel,
`-n` frame count (default 10).

#### `04-deauth-broadcast.sh`
Same as above but sends the deauth to the broadcast address — kicks
**every** client of that AP. Only run against an AP you own and which
has no other clients you care about.

```bash
sudo ./scripts/04-deauth-broadcast.sh -a AA:BB:CC:11:22:33 -i wlan1mon -n 20
```

### Handshake capture and offline crack

#### `05-crack-handshake.sh`
Pure offline: takes a captured pcap and runs `aircrack-ng` against a
wordlist to recover the WPA passphrase. No wireless involved at this
stage.

```bash
sudo ./scripts/05-crack-handshake.sh \
    -b AA:BB:CC:11:22:33 \
    -w /usr/share/wordlists/rockyou.txt \
    capture-01.cap
```

#### `08-handshake-capture.sh`
All-in-one: locks the channel, starts `airodump-ng` in the background,
fires deauth at the named client, polls the pcap for a 4-way handshake,
re-fires deauth at 30 s if nothing yet, exits when the handshake lands
(or after 60 s). If `-w <wordlist>` is given, runs the offline crack
right after capture.

```bash
sudo ./scripts/08-handshake-capture.sh \
    -a AA:BB:CC:11:22:33 -c DD:EE:FF:44:55:66 -i wlan1mon -k 11 \
    -o handshake \
    -w /usr/share/wordlists/rockyou.txt
```

This bundles scripts 03 + 04 + 05 into one command.

### Evil twin

#### `06-evil-twin-up.sh`
Brings up a rogue AP **only** — `hostapd` on `wlan2` reading
`configs/hostapd-rogue.conf`, `dnsmasq` for DHCP + DNS hijack, and
iptables NAT through the upstream interface. You then run the deauth
loop (script 09) and traffic capture (`tcpdump`) in separate terminals.
Useful for the pedagogically-clear "look at each component" workflow.

```bash
sudo ./scripts/06-evil-twin-up.sh                 # uses defaults
sudo AP_IFACE=wlan2 UPSTREAM_IFACE=eth0 \
    ./scripts/06-evil-twin-up.sh
```

#### `09-deauth-loop.sh`
Continuous deauth in a loop (default: 5 frames every 5 s, Ctrl-C to
stop). The "pull" half of the evil-twin attack — keeps the victim off
the real AP long enough that they roam to your rogue.

```bash
sudo ./scripts/09-deauth-loop.sh \
    -a <REAL_BSSID> -c <PHONE_MAC> -i wlan1mon -k 11
```

Drop `-c` to broadcast-deauth all clients of the real AP.

#### `10-evil-twin-attack.sh`
All-in-one evil-twin orchestrator. Generates the hostapd + dnsmasq
configs on the fly from your CLI flags, brings up the rogue AP, runs the
deauth loop, captures all rogue-side traffic to a pcap, and tears
everything down on Ctrl-C. Saves logs and pcap to a `/tmp/eviltwin.XXXX/`
workdir for the report.

```bash
sudo ./scripts/10-evil-twin-attack.sh \
    -B <REAL_BSSID> -S "<REAL_SSID>" -C <PHONE_MAC> \
    -k 11 -m wlan1mon -a wlan2 \
    -W password123
```

Flags: `-B` real AP BSSID, `-S` real SSID (clone), `-C` victim MAC,
`-k` channel, `-m` monitor iface, `-a` rogue AP iface, `-u` upstream
iface for NAT (default `eth0`), `-W` WPA2 password to mirror the real
AP (omit for an open rogue).

This bundles scripts 06 + 09 + tcpdump into one command.

### Cleanup

#### `07-cleanup.sh`
Stops `hostapd` and `dnsmasq` started by script 06, flushes the iptables
rules added for NAT, disables IP forwarding, takes any monitor
interfaces back down, and restarts NetworkManager. Run after the manual
workflow (script 06). Not needed after script 10 — that one cleans up on
Ctrl-C by itself.

```bash
sudo ./scripts/07-cleanup.sh
```

### Library

#### `lib/common.sh`
Sourced by every script. Provides `info` / `warn` / `die` colour-output
helpers and a `require_root` check. Not run directly.

---

## Configs reference

#### `configs/hostapd-testap.conf`
Config for the **legitimate test AP** that runs on Pi #2 (the network you
attack). WPA2-PSK on channel 6 with `wpa_passphrase=password123` —
deliberately weak so the offline-crack demo finishes in seconds. **Never
reuse this password.** The `ieee80211w` line at the bottom toggles PMF
(802.11w) for the mitigation demo: 0 = off (deauth works), 2 = required
(deauth fails).

#### `configs/hostapd-rogue.conf`
Config for the **rogue AP** used by script 06. Defaults to an open
network on channel 6 with SSID `MyTestNetwork`. Edit before use — at
minimum the SSID must match the real AP you are cloning. WPA2 block is
included as commented-out lines if you want to mirror a WPA2 real AP.
Script 10 ignores this file and generates its own config from CLI flags.

#### `configs/dnsmasq-rogue.conf`
DHCP + DNS hijack config used by script 06. Hands out leases in
`10.0.0.10–10.0.0.100` with the rogue AP itself as gateway and DNS
server. The `address=/#/10.0.0.1` line resolves *every* domain to the
rogue AP — useful for captive-portal demos. Logs queries to
`/var/log/dnsmasq-rogue.log` for evidence collection.

---

## Recommended order

The scripts are numbered for the typical run order:

```
00 (verify) -> 01 (monitor) -> 02 (scan) -> 04 (deauth)            # required demo
                                         \-> 03 + 04 + 05          # handshake + crack (manual)
                                          -> 08                    # handshake + crack (auto)
                                         \-> 06 + 09 + tcpdump     # evil twin (manual)
                                          -> 10                    # evil twin (auto)
                                         \-> 07                    # cleanup after manual flows
```
