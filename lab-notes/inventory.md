# Lab inventory — devices in scope

Fill this in **before** running any attack. This is your evidence that
every target was your own device.

---

## Test AP (the one we attack)

- Type: [Pi #2 with hostapd / home router model XYZ]
- SSID:
- BSSID (MAC):
- Channel:
- Encryption: WPA2-PSK   (PMF: off — flipped to required for §7 demo)
- Owner: me

## Test client (the victim)

- Device: [phone make/model]
- MAC address (Wi-Fi):
- Owner: me
- Note: Wi-Fi MAC randomization disabled for this SSID
        (Settings → Wi-Fi → forget network → reconnect with "Use random MAC" off)

## Attacker Pi (Pi #1)

- Hostname:
- Built-in Wi-Fi MAC (wlan0):
- USB adapter model:
- USB adapter chipset:
- USB adapter MAC (wlan1):

## Rogue-AP Pi (Pi #2, if used as AP)

- Hostname:
- USB adapter model:
- USB adapter MAC:

---

## Other SSIDs visible during the lab

If `airodump-ng` shows networks not listed here, they belong to **others**.
Do not target them. If your test AP is not the strongest signal on its
channel, move physically closer to it (or to a more isolated room) before
continuing.

| SSID | BSSID | Channel | Signal | Owner |
|------|-------|---------|--------|-------|
|      |       |         |        |       |
