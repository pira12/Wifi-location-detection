# WiFi Pineapple Equivalent on Raspberry Pi

School project for SNE / Applied Security: build a Raspberry Pi setup that
does what a Hak5 WiFi Pineapple does, then demonstrate a deauthentication
attack against your own device.

**Required deliverable: the deauth attack only.** Everything else
(handshake crack, evil twin, PMF mitigation demo, airgeddon) is bonus
material kept in this repo in case you have time. `TODO.md` walks you
through the required path; `REPORT.md` has placeholders for the bonus
sections you can delete if you skip them.

## Where to start

1. **`TODO.md`** — your physical/hardware checklist. Read this first.
2. **`REPORT.md`** — the writeup template. Fill in screenshots and
   observations as you go.
3. **`scripts/`** — shell helpers for each step of the demo.
4. **`configs/`** — `hostapd` / `dnsmasq` configs for the rogue AP and
   the test AP.
5. **`lab-notes/inventory.md`** — record the MACs and BSSIDs of every
   device you own that's involved in the lab. This is your scope evidence.

## File map

```
.
|- README.md
|- TODO.md                       <- what YOU need to do
|- REPORT.md                     <- writeup template
|- scripts/
|   |- lib/common.sh
|   |- 00-prereq-check.sh
|   |- 01-monitor-up.sh
|   |- 02-scan.sh
|   |- 03-target-capture.sh
|   |- 04-deauth-targeted.sh
|   |- 04-deauth-broadcast.sh
|   |- 05-crack-handshake.sh
|   |- 06-evil-twin-up.sh
|   `- 07-cleanup.sh
|- configs/
|   |- hostapd-testap.conf       <- legit test AP (Pi #2)
|   |- hostapd-rogue.conf        <- evil-twin AP (Pi #1)
|   `- dnsmasq-rogue.conf
`- lab-notes/
    `- inventory.md              <- record YOUR devices' MACs here
```

## Scope

Only attack hardware you own. See `REPORT.md` section 3 for the legal
framing and `lab-notes/inventory.md` for the device list.
