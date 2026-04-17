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
