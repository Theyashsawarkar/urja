"""Battery facts from sysfs, for both kinds of battery driver: energy_*
(µWh) with power_now, or charge_* (µAh) with current_now and voltage_now
(this HP ProBook's battery is the second kind)."""
import glob
import os
import time


def read(path, cast=str):
    try:
        with open(path) as f:
            v = f.read().strip()
        return cast(v)
    except (OSError, ValueError):
        return None


def batteries():
    return [d for d in sorted(glob.glob("/sys/class/power_supply/*")) if read(f"{d}/type") == "Battery"]


def plugged():
    for d in glob.glob("/sys/class/power_supply/*"):
        if read(f"{d}/type") in ("Mains", "USB", "USB_C", "USB_PD") and read(f"{d}/online") == "1":
            return True
    return False


def info():
    """A dict about the first battery, or None if there is none."""
    bats = batteries()
    if not bats:
        return None
    d = bats[0]
    i = {"name": os.path.basename(d), "capacity": read(f"{d}/capacity", int), "status": read(f"{d}/status") or "",
         "cycles": read(f"{d}/cycle_count", int), "tech": read(f"{d}/technology"),
         "model": read(f"{d}/model_name"), "maker": read(f"{d}/manufacturer"), "plugged": plugged()}
    volt = read(f"{d}/voltage_now", int)
    if read(f"{d}/energy_now", int) is not None:
        now, full, design = (read(f"{d}/energy_{k}", int) for k in ("now", "full", "full_design"))
        rate = read(f"{d}/power_now", int)                       # µW
        watts = rate / 1e6 if rate else 0
        full_wh = full / 1e6 if full else None
    else:
        now, full, design = (read(f"{d}/charge_{k}", int) for k in ("now", "full", "full_design"))
        cur = read(f"{d}/current_now", int)                      # µA
        rate = cur
        watts = cur * volt / 1e12 if cur and volt else 0
        vdesign = read(f"{d}/voltage_min_design", int) or volt
        full_wh = full * vdesign / 1e12 if full and vdesign else None
    i["full_wh"] = full_wh
    i["watts"] = abs(watts)
    i["health"] = round(full * 100 / design) if full and design else None
    hours = None
    if rate and now is not None and full:
        if i["status"] == "Charging":
            hours = (full - now) / abs(rate)
        elif i["status"] == "Discharging":
            hours = now / abs(rate)
    i["hours"] = hours
    return i


def fmt_hours(h):
    if h is None or h <= 0 or h > 48:
        return ""
    return f"{int(h)} h {int(h % 1 * 60):02d} min"


def fmt_short(h):
    """1.33 -> "1 h 20 min", 0.2 -> "12 min"."""
    if h is None or h <= 0 or h > 48:
        return ""
    hh, mm = int(h), int(round(h % 1 * 60))
    if mm == 60:
        hh, mm = hh + 1, 0
    return f"{hh} h {mm:02d} min" if hh else f"{mm} min"


def health_word(pct):
    """(word, colour, what it means) for the battery's health."""
    if pct is None:
        return "", "gray", ""
    if pct >= 80:
        return "good", "green", "Holds most of the charge it did when new."
    if pct >= 60:
        return "worn", "yellow", f"Holds {pct}% of the charge it did when new."
    return "replace", "red", f"Holds only {pct}% of its first charge: worth replacing soon."


HISTORY = 3 * 3600   # seconds the charge graph shows


def upower_history(seconds=HISTORY):
    """[(unix time, percent, charging)] from UPower's own charge history
    (it keeps one for every battery, readable over D-Bus without root; its
    files in /var/lib/upower are root's). [] when UPower isn't there."""
    try:
        from gi.repository import Gio, GLib
        bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)

        def call(path, iface, method, args, sig):
            return bus.call_sync("org.freedesktop.UPower", path, iface, method, args, GLib.VariantType(sig),
                                 Gio.DBusCallFlags.NONE, 2000, None).unpack()
        paths = call("/org/freedesktop/UPower", "org.freedesktop.UPower", "EnumerateDevices", None, "(ao)")[0]
        for path in paths:
            props = "org.freedesktop.DBus.Properties"
            dev = GLib.Variant("(ss)", ("org.freedesktop.UPower.Device", "Type"))
            if call(path, props, "Get", dev, "(v)")[0] != 2:          # 2: a battery
                continue
            ps = GLib.Variant("(ss)", ("org.freedesktop.UPower.Device", "PowerSupply"))
            if not call(path, props, "Get", ps, "(v)")[0]:          # a mouse's battery, not the laptop's
                continue
            rows = call(path, "org.freedesktop.UPower.Device", "GetHistory",
                        GLib.Variant("(suu)", ("charge", seconds, 400)), "(a(udu))")[0]
            cut = time.time() - seconds
            # UPower writes a point when the charge changes; state 1 is charging.
            return sorted((t, v, st == 1) for t, v, st in rows if t >= cut - 3600)
    except Exception:   # no system bus, no UPower, an old UPower: the graph uses our own samples
        return []
    return []


def bins(points, n=36, seconds=HISTORY, now=None):
    """The last `seconds` in n equal steps: each the charge at its end (the
    last point before it, carried forward: UPower only writes changes), or
    None before anything is known."""
    now = now or time.time()
    pts = sorted(points)
    out, j, last = [], 0, None
    for k in range(n):
        end = now - seconds + (k + 1) * seconds / n
        while j < len(pts) and pts[j][0] <= end:
            last = pts[j]
            j += 1
        out.append(last)
    return out


def estimate(i, points, now=None, window=1800):
    """(watts, hours) from how fast the charge has moved over the last half
    hour, for batteries that don't report a current (some HP firmware leaves
    current_now empty). None when there's too little to go on."""
    now = now or time.time()
    charging = i["status"] == "Charging"
    if i["status"] not in ("Charging", "Discharging") or not i.get("capacity"):
        return None
    pts = [p for p in sorted(points) if p[0] >= now - window]
    # only the stretch since the last change between charging and not
    run = []
    for p in pts:
        if p[2] != charging:
            run = []
        else:
            run.append(p)
    if len(run) < 2 or run[-1][0] - run[0][0] < 180 or run[-1][1] == run[0][1]:
        return None
    rate = abs(run[-1][1] - run[0][1]) / ((run[-1][0] - run[0][0]) / 3600)   # percent per hour
    hours = (100 - i["capacity"]) / rate if charging else i["capacity"] / rate
    watts = rate * i["full_wh"] / 100 if i.get("full_wh") else 0
    return watts, hours
