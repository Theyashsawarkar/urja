# urja

**urja** (ऊर्जा, "energy") — The battery at a glance. A tool for [Vyom](https://github.com/Theyashsawarkar/vyom), the keyboard-driven panels of [Vayu](https://github.com/Theyashsawarkar/vayu); in Vayu it replaces battery-limit-picker.py.

> Battery at a glance: charge ring, time left, power draw, health and cycles, power profile, a charge-limit reminder.

## Features

- A **charge ring**, time to full or empty, **power draw** in watts, the battery's **health** (of its design capacity) and **cycle count**.
- Works with both kinds of battery driver (energy_* / power_now, or charge_* / current_now).
- The **power profile** (power-profiles-daemon), switched with a click or `P`.
- With `limit_file` set, a **charge-limit reminder** slider: the percentage a watcher of yours nudges you to unplug at.

## Keys

| Key | Action |
|---|---|
| `Left / Right` | Change the charge-limit reminder (on the slider) |
| `P` | Switch the power profile |
| `Esc` | close |

Every Vyom panel also has: `Up`/`Down` (or `Ctrl+K`/`Ctrl+J`) to move, `Page Up`/`Page Down`, `Tab` to switch to the next tool.

## Requirements

- [Vyom](https://github.com/Theyashsawarkar/vyom) 0.2 or newer (Python 3.11+, GTK 4, gtk4-layer-shell, a layer-shell compositor)
- optional: powerprofilesctl (power profile)
- python-cairo (pycairo) for the charge ring (Arch: `python-cairo`)

## Install

```sh
git clone https://github.com/Theyashsawarkar/urja ~/.local/share/vyom/plugins/urja
vyom reload        # or log out and in
vyom urja         # open it (again: close it)
```

Bind it to a key, e.g. in sway:

```
bindsym $mod+<key> exec vyom urja
```

Update: `git -C ~/.local/share/vyom/plugins/urja pull && vyom reload`. `vyom list` shows every installed tool and why one would be skipped.

## Configuration

In `~/.config/vyom/config.toml` (all optional):

```toml
[plugin.urja]
# limit_file: file holding the reminder percentage (Vayu: ~/.local/state/battery-limit/threshold) (default: (unset: no slider))
```

## License

MIT.
