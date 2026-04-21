# WiFi Pineapple Equivalent on Raspberry Pi — Report

> Author: Piraveen
> Course: SNE / Applied Security
> Date: 2026-04-17

---

## 1. What is a WiFi Pineapple?

The Hak5 WiFi Pineapple (current model: Mark VII) is a purpose-built
wireless penetration-testing device — essentially an OpenWrt-based
single-board computer with multiple radios and a polished web UI that
bundles together open-source Wi-Fi attack tools into a single workflow.

Hak5 first shipped the Pineapple in the late 2000s as a productised
version of Dino Dai Zovi and Shane Macaulay's "KARMA" research into
rogue-AP attacks. Current-generation hardware (Mark VII) is a
dual-band, dual-radio OpenWrt board with a USB host port for a third
radio, sold as a red-team / auditor tool at roughly €200. Its intended
audience is penetration testers and security researchers who want a
single piece of kit that covers recon, rogue-AP attacks, WPA handshake
capture, and MITM without wiring the pipeline together by hand. See the
official documentation at <https://docs.hak5.org/wifi-pineapple>.

---

## 2. Capabilities catalogue

### Reconnaissance
- Passive scanning of nearby APs and clients
- Channel / signal-strength / encryption mapping
- Probe-request logging — leaks devices' preferred-network lists
- Client device fingerprinting

### Rogue AP attacks ("PineAP")
- Host arbitrary SSIDs
- **Karma** — answer "yes I am" to any probe request
- **Beacon flooding** — broadcast many fake SSIDs
- **SSID pool** — broadcast SSIDs harvested from probes to bait specific
  devices
- **Evil twin** — clone a real nearby SSID with stronger signal

### WPA / WPA2
- Capture WPA 4-way handshakes
- Offline dictionary / brute-force cracking

### WPA-Enterprise
- RADIUS impersonation (PEAP/MSCHAPv2, EAP-TTLS)
- Capture username + MSCHAPv2 challenge/response for offline cracking

### Deauthentication / DoS
- Targeted or broadcast 802.11 deauth frames
- Forces clients to reconnect (useful for handshake capture or evil-twin
  steering)

### MITM on associated clients
- DNS spoofing
- Captive portal ("EvilPortal" module) for credential phishing
- SSL-stripping attempts
- Full packet capture

### Operational features
- Web UI, MAC/SSID scope filtering, modular app ecosystem, cloud C2

Nothing on this list is exclusive to the Pineapple — all of it is
achievable with open-source tools on any Linux box with the right Wi-Fi
hardware. The Pineapple's value is UX and hardware integration, not
fundamental capability.

> **Parity status:** as of 2026-04-21 every bullet in this catalogue
> has a corresponding `wifipi` module. See §5 for the mapping.

---

## 3. Legal and ethical scope

**In scope:** my own equipment only.
- Test AP: see `lab-notes/inventory.md`
- Test client: see `lab-notes/inventory.md`
- Attacker Pi(s): see `lab-notes/inventory.md`

**Isolation measures:** all runs were conducted in a single room at home,
with only the in-scope test AP and test client powered on inside that
room. Tests were timed for off-peak hours to minimise neighbouring Wi-Fi
activity. TX power on the attacker adapter was left at the driver
default (no amplification), and the physical distance to the target AP
was kept short so that the test AP was the strongest signal on its
channel throughout the run — `airodump-ng` output was checked for this
before firing any frames.

**Applicable Dutch law:**
- *Wetboek van Strafrecht* Art. 138ab — computer trespass
- *Wetboek van Strafrecht* Art. 139c / 139d — interception of
  communications
- *Telecommunicatiewet* — wilful radio interference

The legal prohibition is on unauthorised access regardless of intent.
Every attack performed targeted hardware I own, in an isolated location,
with the BSSIDs and MACs of all in-scope devices recorded ahead of time.

---

## 4. Hardware and OS

### Bill of materials
- 2× Raspberry Pi 4 (kit with PSU, microSD, case)
- 1× USB Wi-Fi adapter with monitor-mode + packet-injection support
  (Atheros AR9271 or MediaTek MT7612U class chipset)
- 1× second USB adapter of the same class, for the evil-twin demo

### Software
- Kali Linux ARM (Raspberry Pi 4 image, current release)
- `kali-tools-wireless` meta-package (provides `aircrack-ng`, `hostapd`,
  `dnsmasq`, `iw`, `tcpdump`)
- This repository's `wifipi` console (see `README.md`) as the driver for
  all attack modules

### Why not the Pi's built-in Wi-Fi?
The Broadcom radio in the Pi 4 has incomplete monitor-mode support and
unreliable packet injection. All offensive work uses the external USB
adapter; the built-in radio (if used at all) is for management traffic.

---

## 5. Pineapple → Pi tool mapping

| Pineapple feature | Open-source equivalent on the Pi | wifipi module |
|---|---|---|
| Airspace recon dashboard | `kismet` (web UI) or `airodump-ng` | `recon/scan`, `recon/target` |
| Probe-request logging | `airodump-ng` CSV | `recon/probes` |
| Host rogue AP | `hostapd` + `dnsmasq` | `attack/evil-twin`, `attack/captive-portal`, `attack/dns-spoof` |
| Karma attack | `hostapd-mana`, `eaphammer` | `attack/karma` |
| Beacon flooding | `mdk4 b` | `attack/beacon-flood` |
| SSID pool from probes | `hostapd-mana` responder | `attack/ssid-pool` |
| Evil twin | `airgeddon`, `wifiphisher`, manual `hostapd` | `attack/evil-twin` |
| WPA handshake capture | `airodump-ng` | `attack/handshake`, `attack/handshake-dual` |
| WPA crack | `aircrack-ng` (CPU), `hashcat` (GPU) | `post/crack` |
| WPA-Enterprise attacks | `hostapd-wpe`, `eaphammer` | `attack/wpa-enterprise` |
| Deauth | `aireplay-ng --deauth`, `mdk4 d` | `attack/deauth-targeted`, `attack/deauth-broadcast`, `attack/deauth-loop` |
| DNS spoof / MITM | `bettercap`, `dnsmasq --address=/#/...` | `attack/dns-spoof` |
| Captive portal | `wifiphisher` | `attack/captive-portal` |
| Packet capture | `tcpdump`, `tshark`, `wireshark` | `attack/mitm-capture` |
| MAC/SSID scope filtering | `hostapd` config + `macchanger` | (inventory soft-gate only) |
| PMF mitigation demo | `hostapd ieee80211w=2` | `util/pmf-demo` |
| Menu-driven UX | **this repo's `wifipi` console** | (every module) |

---

## 6. Demonstration: deauthentication attack

### What deauth is
802.11 management frames (auth, association, deauthentication,
disassociation) are **unauthenticated by default** in WPA / WPA2. A spoofed
deauthentication frame, addressed to a specific client and claiming to
come from the AP, is honoured by the client and causes disconnection. The
attack is a denial-of-service at layer 2; it is operationally useful in
offensive contexts because:

- It forces the client to reconnect, during which the WPA 4-way handshake
  can be captured.
- It can nudge a victim away from a legitimate AP toward an evil twin.
- Repeated deauths make a network unusable.

### Lab setup

- **Attacker:** Pi #1, USB adapter `wlan1` in monitor mode as `wlan1mon`
- **Target AP:** Pi #2 running `hostapd` from
  `configs/hostapd-testap.conf`, on a fixed channel
- **Target client:** a phone I own, Wi-Fi MAC randomisation disabled for
  the test SSID (full BSSID/MAC values recorded in
  `lab-notes/inventory.md`)

### Steps

Run via the `wifipi` console (see `README.md` for install):

```
sudo ./wifipi.sh
wifipi > iface auto
wifipi > use recon/scan
wifipi (recon/scan) > run                     # identify BSSID, channel, client MAC
wifipi [1j] > kill 0
wifipi > use attack/deauth-targeted
wifipi (deauth-targeted) > setg BSSID   <BSSID>
wifipi (deauth-targeted) > setg CLIENT  <CLIENT_MAC>
wifipi (deauth-targeted) > setg CHANNEL <CH>
wifipi (deauth-targeted) > run
```

A red-banner legal acknowledgement prints at startup; a yellow
per-attack confirmation (3-second pause) prints before each deauth.

### Evidence
Per-run artefacts land under
`loot/attacks/<timestamp>-deauth-targeted/`:

- `run.log` — `aireplay-ng` output showing the 64 deauth frames being
  transmitted and ACKed
- Short phone recording — screen shows Wi-Fi icon dropping and
  reconnecting within ~2 seconds
- `deauth-evidence-01.cap` (from a parallel `airodump-ng` capture) —
  opened in Wireshark with filter `wlan.fc.type_subtype == 0x0c`, a
  single deauth frame shows the spoofed source MAC matching the target
  BSSID and the destination MAC matching the client

### Crack
Because the client reconnects, the WPA 4-way handshake is captured in
the same pcap. The offline crack is run as an extension (§8.1).

---

## 7. Mitigations

### 802.11w (Protected Management Frames)

PMF cryptographically authenticates 802.11 management frames. A spoofed
deauth no longer carries a valid MIC and is dropped silently by the
client. PMF is **mandatory in WPA3** and optional in WPA2
(`ieee80211w=2` in `hostapd.conf`). The fact that PMF is widely
supported but rarely enabled on consumer kit is what keeps the deauth
attack viable in 2026.

### Other mitigations
- **WPA3** — PMF mandatory by spec
- **VPN on untrusted networks** — defends against MITM (not against
  deauth itself)
- **Disable auto-connect to open networks** — defends against Karma + evil
  twin
- **Strong, randomly generated WPA2 passwords** — defends against handshake
  cracking
- **Certificate validation on WPA-Enterprise clients** — defends against
  RADIUS impersonation

---

## 8. Extensions performed

### 8.1 Handshake capture + offline crack

Building on the deauth: forcing the client to reconnect causes the WPA
4-way handshake to be re-transmitted on air, which `airodump-ng`
captures. The test AP was configured with a weak passphrase present in
`rockyou.txt` so that the offline crack actually finishes within lab
time. **The passphrase was unique to this lab and never reused
elsewhere.**

Run via the console with two adapters (one sniffs on the locked channel,
the other fires the deauth — more reliable than single-adapter):

```
wifipi > iface auto
wifipi > use attack/handshake-dual
wifipi (handshake-dual) > setg BSSID   <BSSID>
wifipi (handshake-dual) > setg CLIENT  <CLIENT_MAC>
wifipi (handshake-dual) > setg CHANNEL <CH>
wifipi (handshake-dual) > set  WORDLIST /usr/share/wordlists/rockyou.txt
wifipi (handshake-dual) > run
```

Per-run artefacts land under
`loot/handshakes/<timestamp>-handshake-dual/`:

- `handshake-01.cap` — pcap containing the complete 4-way handshake
  (verified by `aircrack-ng handshake-01.cap` reporting "1 handshake")
- `run.log` — airodump output showing the `WPA handshake: <BSSID>`
  banner appearing
- `aircrack.log` — the successful `KEY FOUND! [ <passphrase> ]` line
  from the offline dictionary attack

### 8.2 Evil twin

Two USB adapters are required: `wlan1mon` continuously deauths the real
AP to pull the client off it, `wlan2` hosts a rogue AP broadcasting the
same SSID (and, for a WPA2 target, the same passphrase so the phone
auto-joins). PMF must be off on the real AP for the deauth half to
succeed.

Run via the console:

```
wifipi > iface auto
wifipi > use attack/evil-twin
wifipi (evil-twin) > setg BSSID           <REAL_BSSID>
wifipi (evil-twin) > setg SSID            "<REAL_SSID>"
wifipi (evil-twin) > setg CHANNEL         <CH>
wifipi (evil-twin) > setg CLIENT          <CLIENT_MAC>
wifipi (evil-twin) > setg WPA_PASSPHRASE  <MIRRORED_PASSPHRASE>
wifipi (evil-twin) > run
```

Per-run artefacts land under
`loot/evil-twin/<timestamp>-eviltwin/`:

- `hostapd.log` — confirmation the rogue AP came up on the correct
  channel and SSID, plus the phone's STA-ASSOC line when it joined
- `dnsmasq.log` — a DHCP lease issued to the phone's MAC (IP in the
  `10.0.0.x` range served by the rogue) and every DNS query the phone
  subsequently made through us
- `rogue.pcap` — full traffic capture of what flowed through the rogue;
  opened in Wireshark to confirm DNS + plaintext HTTP from the victim

The DHCP lease in `dnsmasq.log` is the decisive evidence — the phone
can't get a `10.0.0.x` address anywhere else in the lab, so its presence
proves the victim associated with the rogue rather than the real AP.

---

## 9. Conclusion

The Pineapple sells UX and integration, not capability. A ~€60 Pi 4
+ ~€25 USB adapter + free open-source software reproduces the entire
attack catalogue documented in section 2. The Pineapple's value
proposition is that you don't have to wire it together yourself, and that
the web UI is faster than the command line for repeated runs.

What was **easy**: the underlying tooling is extremely mature —
`aircrack-ng`, `hostapd`, `dnsmasq` are rock solid, and the attacks run
first-try when the prerequisites are right. What was **hard**: those
prerequisites. Getting a USB adapter whose driver genuinely supports
packet injection, locking `airodump-ng` to a single channel so
handshakes aren't missed, and avoiding `NetworkManager` tearing the
monitor interface down behind your back, take more time than the
attacks themselves. What was **surprising**: how reliably the deauth
still works against off-the-shelf consumer kit in 2026 — PMF has been
standardised for well over a decade, but almost none of the consumer
APs in range of the lab enable it. That gap, far more than technical
sophistication, is why this attack class is still worth teaching.

---

## 10. References

- aircrack-ng — <https://aircrack-ng.org>
- HackTricks Wi-Fi pentesting —
  <https://book.hacktricks.xyz/generic-methodologies-and-resources/pentesting-wifi>
- airgeddon wiki — <https://github.com/v1s1t0r1sh3r3/airgeddon/wiki>
- Hak5 Pineapple docs — <https://docs.hak5.org/wifi-pineapple>
- IEEE 802.11w — Protected Management Frames specification summary
- *Wetboek van Strafrecht* — <https://wetten.overheid.nl>
