"""Battery facts from sysfs, for both kinds of battery driver: energy_*
(µWh) with power_now, or charge_* (µAh) with current_now and voltage_now
(this HP ProBook's battery is the second kind)."""
import glob
import os


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
    else:
        now, full, design = (read(f"{d}/charge_{k}", int) for k in ("now", "full", "full_design"))
        cur = read(f"{d}/current_now", int)                      # µA
        rate = cur
        watts = cur * volt / 1e12 if cur and volt else 0
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
