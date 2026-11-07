# Changelog

Newest first. Releases are tags (`vX.Y.Z`).

## v0.2.0 -- 2026-11-07

- **Time to full or time left is the headline**, next to a bigger charge ring that says its state in words ("charging", "on battery", "low").
- **A charge graph of the last 3 hours**, from UPower's history (no root needed) and urja's own samples.
- **Power draw in watts**, and when the battery doesn't report a current (this HP's doesn't), an estimate from the last half hour, marked "about".
- **Health as a bar with a word**: good (green), worn (yellow) or replace (red), with what that means in plain words, cycles and the battery's make.
- **Power profile as a segmented control**, the current one filled; `P` cycles.
- The **charge reminder shows its value in peach** and has an 85% stop; a value between stops now lands on the nearest one instead of "off".
- `vyom urja demo` shows made-up numbers.
- Needs Vyom 0.6.0.
- Every corner is rounded: the website's callouts.

## v0.1.4 -- 2026-11-04

- **The card stays true while it's open**: plug the charger in and it shows within 2 seconds, without disturbing the reminder slider. It used to show the moment you opened it, until you closed it.
- A logo and a shloka at the top of the README and the website: every Vayu tool has them now.

## v0.1.3 -- 2026-10-21

- Follows the theme: its colours are named (`@accent`, `@crust`...) instead
  of fixed hex codes, so a theme that redefines them (Vyom 0.2.9's `css`,
  e.g. [varna](https://github.com/Theyashsawarkar/varna)) recolours it too.

## v0.1.2 -- 2026-10-21

- A website (GitHub Pages, https://theyashsawarkar.github.io/urja/): the README as a home page, the
  changelog, and architecture decision records (`docs/adr/`), built from these files by
  `scripts/build-site.py`; CI checks the site is up to date.

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
