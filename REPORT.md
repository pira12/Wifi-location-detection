# WiFi Pineapple Equivalent on Raspberry Pi — Report

> Author: <your name>
> Course: SNE / Applied Security
> Date:

---

## 1. What is a WiFi Pineapple?

The Hak5 WiFi Pineapple (current model: Mark VII) is a purpose-built
wireless penetration-testing device — essentially an OpenWrt-based
single-board computer with multiple radios and a polished web UI that
bundles together open-source Wi-Fi attack tools into a single workflow.

[TODO: short paragraph on history, intended audience, hardware specs.
Cite Hak5 docs.]

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

---

## 3. Legal and ethical scope

**In scope:** my own equipment only.
- Test AP: see `lab-notes/inventory.md`
- Test client: see `lab-notes/inventory.md`
- Attacker Pi(s): see `lab-notes/inventory.md`

**Isolation measures:** [TODO: describe room, antenna choice, time of day,
any RF-shielding precautions]

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
- 1× USB Wi-Fi adapter — model: **[TODO]**, chipset: **[TODO]**
- (optional) 2nd USB adapter for evil-twin demo

### Software
- Kali Linux ARM — release: **[TODO]**
- `kali-tools-wireless` meta-package
- `airgeddon` (cloned from upstream) — used as a Pineapple-UX comparison

### Why not the Pi's built-in Wi-Fi?
The Broadcom radio in the Pi 4 has incomplete monitor-mode support and
unreliable packet injection. All offensive work uses the external USB
adapter; the built-in radio (if used at all) is for management traffic.

---

## 5. Pineapple → Pi tool mapping

| Pineapple feature | Open-source equivalent on the Pi |
|---|---|
| Airspace recon dashboard | `kismet` (web UI) or `airodump-ng` |
| Host rogue AP | `hostapd` + `dnsmasq` |
| Karma attack | `hostapd-mana`, `eaphammer` |
| Beacon flooding | `mdk4 b` |
| Evil twin | `airgeddon`, `wifiphisher`, manual `hostapd` |
| WPA handshake capture | `airodump-ng` |
| WPA crack | `aircrack-ng` (CPU), `hashcat` (GPU) |
| WPA-Enterprise attacks | `hostapd-wpe`, `eaphammer` |
| Deauth | `aireplay-ng --deauth`, `mdk4 d` |
| DNS spoof / MITM | `bettercap`, `dnsmasq --address=/#/...` |
| Captive portal | `wifiphisher` |
| Packet capture | `tcpdump`, `tshark`, `wireshark` |
| MAC/SSID scope filtering | `hostapd` config + `macchanger` |
| Menu-driven UX | **`airgeddon`** (closest analogue) |

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
[TODO: diagram or photo]

- **Attacker:** Pi #1, USB adapter `wlan1` in monitor mode as `wlan1mon`
- **Target AP:** Pi #2 running `hostapd` (config:
  `configs/hostapd-testap.conf`)
- **Target client:** my [phone model], MAC `[TODO]`

### Steps
```
sudo ./scripts/01-monitor-up.sh wlan1
sudo ./scripts/02-scan.sh wlan1mon              # identify BSSID, channel, client MAC
sudo ./scripts/03-target-capture.sh \
    -c <CH> -b <BSSID> -i wlan1mon -o capture   # leave running in terminal A
sudo ./scripts/04-deauth-targeted.sh \
    -a <BSSID> -c <CLIENT_MAC> -i wlan1mon      # in terminal B
```

### Evidence
- [TODO: screenshot of `airodump-ng` showing `WPA handshake: <BSSID>`]
- [TODO: screenshot of phone losing Wi-Fi]
- [TODO: Wireshark screenshot — filter `wlan.fc.type_subtype == 0x0c`,
  show one deauth frame and call out the spoofed source MAC]

### Crack
```
sudo ./scripts/05-crack-handshake.sh \
    -b <BSSID> -w /usr/share/wordlists/rockyou.txt capture-01.cap
```
- [TODO: screenshot of `KEY FOUND! [ password123 ]`]

---

## 7. Mitigation: 802.11w (Protected Management Frames)

Re-ran the same attack with `ieee80211w=2` set in
`configs/hostapd-testap.conf`. PMF cryptographically authenticates
management frames; the spoofed deauth no longer carries a valid MIC and
the client ignores it.

- [TODO: screenshot of attack failing — client stays connected]

PMF is **mandatory in WPA3** and optional in WPA2. The fact that it works
on consumer kit but is rarely enabled is what keeps this attack viable in
2026.

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

[TODO: keep the sections you actually did, delete the rest.]

### 8.1 Evil twin
[TODO: steps + screenshots — see Phase 8 in TODO.md]

### 8.2 airgeddon walkthrough
[TODO: 2–3 menu screenshots; one paragraph comparing the experience to
the manual workflow]

---

## 9. Conclusion

The Pineapple sells UX and integration, not capability. A ~€60 Pi 4
+ ~€25 USB adapter + free open-source software reproduces the entire
attack catalogue documented in section 2. The Pineapple's value
proposition is that you don't have to wire it together yourself, and that
the web UI is faster than the command line for repeated runs.

[TODO: one paragraph reflecting on what was easy / hard / surprising
during the build]

---

## 10. References

- aircrack-ng — <https://aircrack-ng.org>
- HackTricks Wi-Fi pentesting —
  <https://book.hacktricks.xyz/generic-methodologies-and-resources/pentesting-wifi>
- airgeddon wiki — <https://github.com/v1s1t0r1sh3r3/airgeddon/wiki>
- Hak5 Pineapple docs — <https://docs.hak5.org/wifi-pineapple>
- IEEE 802.11w — Protected Management Frames specification summary
- *Wetboek van Strafrecht* — <https://wetten.overheid.nl>
