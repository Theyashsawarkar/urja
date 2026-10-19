# Changelog

Newest first. Releases are tags (`vX.Y.Z`).

## v0.1.0 -- 2026-10-19

- First release, as its own repository: the battery at a glance. Replaces battery-limit-picker.py in Vayu.
- A **charge ring**, time to full or empty, **power draw** in watts, the battery's **health** (of its design capacity) and **cycle count**.
- Works with both kinds of battery driver (energy_* / power_now, or charge_* / current_now).
- The **power profile** (power-profiles-daemon), switched with a click or `P`.
- With `limit_file` set, a **charge-limit reminder** slider: the percentage a watcher of yours nudges you to unplug at.
