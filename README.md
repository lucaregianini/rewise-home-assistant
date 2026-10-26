# Rewise for Home Assistant

Control your Rewise Air A2 air conditioners and learned remotes directly over your home network.

<!-- Add a real Home Assistant screenshot after the first device validation. -->

Version 0.9.1 is the first prerelease, awaiting testing on a real Air A2. The Rewise app screen described below must be included in your installed app version.

## What you need

A Rewise Air A2 set up in the Rewise app, Home Assistant 2025.1 or later, and HACS. Home Assistant and Rewise Air must be able to reach each other on your network. Local tests currently use Home Assistant 2026.10.4; the minimum version has not been tested separately.

## Install

1. Open HACS → ⋮ → Custom repositories.
2. Add `https://github.com/lucaregianini/rewise-home-assistant`, category **Integration**.
3. Find **Rewise**, download it, and restart Home Assistant. Enable prerelease versions in HACS if necessary to select 0.9.1.

## Add your Rewise Air

1. In Home Assistant, open Settings → Devices & services. Your Air A2 appears under **Discovered**.
2. Select Configure.
3. In the Rewise app, open your Air A2 → Settings → Home Assistant → **Copy Code**.
4. Paste the code into Home Assistant.

If discovery is unavailable, select Add integration → Rewise and enter the Air A2's IP address or hostname and connection code. Use a bare address, without `http://` or a path.

## What you get

- Main air conditioner: power, auto/cool/heat/dry/fan modes, target temperature (17–30 °C), and fan speed.
- Room temperature and humidity sensors.
- AC extras supported by your selected profile: switches for retained state, buttons for one-shot toggles.
- A climate entity for each additional AC configured in the app.
- Buttons for learned TVs, lights, and other remotes associated with this Air A2.
- Firmware and Wi-Fi signal diagnostics, disabled by default.

## Good to know

IR is one-way. Home Assistant shows what Rewise Air last sent or heard from the remote. Supported original-remote presses are polled within 30 seconds; reception depends on the configured protocol and whether Rewise Air hears the remote.

The second AC's state is assumed: Home Assistant remembers its last successful command across restarts, but cannot detect changes made with that AC's physical remote.

Everything stays on your network. Commands are serialized at least 1.1 seconds apart. A busy response is retried once after 1.2 seconds. A change of main AC profile reloads the integration to update its extra controls.

## After a factory reset or new buttons

After resetting and setting up the same Air A2 again, copy a new code. Home Assistant asks you to reauthenticate when the old password stops working.

After adding, removing, or renaming learned buttons or another AC in the app, use **Reconfigure** on the Rewise integration and paste a fresh code. The code is a snapshot, not a live sync of your app configuration. Reconfiguration removes controls that are no longer present and preserves your custom names for retained entities.

## Troubleshooting

**Not discovered:** mDNS may be blocked across VLANs or guest networks. Allow the discovery traffic or use manual setup, and allow Home Assistant to reach the Air A2 on TCP port 80.

**Invalid code:** copy the complete `RWHA1.` code again. Do not paste only the shortened preview shown on screen.

**Wrong device:** use the code from the Air A2 you are configuring.

**Cannot connect:** check power, network routing, and the address. Your phone's ability to use cloud control does not establish that Home Assistant can reach the Air A2 locally.

**Busy:** wait a moment. Learning or another controller may be using the transmitter.

**Unavailable temperature or humidity:** the device may not have a sensor reading yet. Null readings remain unknown rather than being shown as zero.

## Privacy

No cloud service is used by this integration. The connection code contains the device password; compression is not encryption. Treat it like a password. Anyone on your Wi-Fi with it can control this Air A2. Local HTTP traffic is not encrypted, so use a trusted network.

Home Assistant stores the code in its configuration. Keep configuration files and backups private. Diagnostics omit the encoded code and redact its password, username, learned IR payloads, and sensitive network fields. Never include a real code in an issue or log.

## Support

[support@rewisehome.com](mailto:support@rewisehome.com) · [Report an integration issue](https://github.com/lucaregianini/rewise-home-assistant/issues)
