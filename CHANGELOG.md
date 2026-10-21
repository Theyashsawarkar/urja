# Changelog

Newest first. Releases are tags (`vX.Y.Z`).

## v0.1.1 -- 2026-10-21

- Documentation for open source: a logo and banner, a full README (features,
  install, usage, configuration, troubleshooting, the whole Vyom family),
  CONTRIBUTING, SECURITY and CODE_OF_CONDUCT, issue and pull request
  templates, and CI (compiles, checks plugin.toml and that every key is
  documented).

## v0.1.0 -- 2026-10-19

- First release, as its own repository: the battery at a glance. Replaces battery-limit-picker.py in Vayu.
- A **charge ring**, time to full or empty, **power draw** in watts, the battery's **health** (of its design capacity) and **cycle count**.
- Works with both kinds of battery driver (energy_* / power_now, or charge_* / current_now).
- The **power profile** (power-profiles-daemon), switched with a click or `P`.
- With `limit_file` set, a **charge-limit reminder** slider: the percentage a watcher of yours nudges you to unplug at.
