"""urja (ऊर्जा, "energy"): the battery at a glance, for Vyom.

A charge ring, time to full or empty, how much power it's drawing, the
battery's health and cycle count, the power profile, and (when
`limit_file` is set) a charge-limit reminder: the percentage a watcher of
yours nudges you to unplug at (Vayu's battery-limit-watch.sh).
"""
import math
import os

from gi.repository import Gtk

from vyom import Plugin as Base
from vyom import ui, util

from . import battery

# keybind: Vyom/battery | Left / Right | Change the charge-limit reminder (on the slider)
# keybind: Vyom/battery | P | Switch the power profile

PROFILES = [("power-saver", "Power saver", "\U000f0f86"), ("balanced", "Balanced", "\U000f04c5"),
            ("performance", "Performance", "\U000f04c4")]
STOPS = [0, 50, 60, 70, 75, 80, 90, 100]   # 0 = reminder off


class Ring(Gtk.DrawingArea):
    def __init__(self, pct, charging, low):
        super().__init__()
        self.pct, self.charging, self.low = pct, charging, low
        self.set_content_width(132)
        self.set_content_height(132)
        self.set_draw_func(self.draw)

    def draw(self, _a, cr, w, h):
        cx, cy, r = w / 2, h / 2, min(w, h) / 2 - 9
        cr.set_line_width(11)
        cr.set_source_rgba(1, 1, 1, 0.08)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.stroke()
        col = (0.95, 0.55, 0.66) if self.low else (0.65, 0.89, 0.63)
        cr.set_source_rgb(*col)
        cr.set_line_cap(1)
        cr.arc(cx, cy, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * max(0.01, self.pct / 100))
        cr.stroke()


class Plugin(Base):
    name, title, icon, color = "urja", "Battery", "\U000f0079", "green"
    layout = "card"
    width = 520

    def available(self):
        return (bool(battery.batteries()), "no battery")

    def limit_file(self):
        p = self.conf.get("limit_file")
        return os.path.expanduser(p) if p else None

    def read_limit(self):
        f = self.limit_file()
        try:
            raw = open(f).read().strip()
            return int(raw) if raw.isdigit() else 0
        except (OSError, TypeError):
            return 0

    def write_limit(self, pct):
        f = self.limit_file()
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "w") as fh:
            fh.write(str(pct) if pct else "off")
        i = battery.info() or {}
        if pct and i.get("plugged") and (i.get("capacity") or 0) >= pct:
            # Already past it while charging: tell the watcher it was said.
            with open(os.path.join(os.path.dirname(f), ".notified"), "w") as fh:
                fh.write(str(pct))

    def build_card(self):
        i = battery.info()
        if not i:
            return ui.vbox(ui.title("No battery"), cls="card")
        cap = i["capacity"] or 0
        charging = i["status"] in ("Charging", "Full")
        status = {"Charging": "charging", "Discharging": "on battery", "Full": "full",
                  "Not charging": "plugged in"}.get(i["status"], i["status"].lower())
        ring = Ring(cap, charging, cap <= 20 and not i["plugged"])
        overlay = Gtk.Overlay()
        overlay.set_child(ring)
        center = ui.vbox(ui.label(f"{cap}%", "big-number"), ui.label(status, "card-sub"), spacing=0)
        center.set_halign(Gtk.Align.CENTER)
        center.set_valign(Gtk.Align.CENTER)
        overlay.add_overlay(center)
        left = battery.fmt_hours(i["hours"])
        facts = []
        if left:
            facts.append(("To full" if i["status"] == "Charging" else "Left", left))
        if i["watts"]:
            facts.append(("Power", f"{i['watts']:.1f} W {'in' if i['status'] == 'Charging' else 'out'}"))
        if i["health"]:
            facts.append(("Health", f"{i['health']}% of design"))
        if i["cycles"]:
            facts.append(("Cycles", str(i["cycles"])))
        maker = " ".join(x for x in (i.get("maker"), i.get("model")) if x)
        if maker:
            facts.append(("Battery", f"{maker} · {i.get('tech') or ''}".strip(" ·")))
        overlay.set_valign(Gtk.Align.START)
        info = ui.vbox(ui.label("Battery", "card-title", xalign=0), ui.kv(facts, wrap=False), spacing=10)
        info.set_valign(Gtk.Align.CENTER)
        top = ui.hbox(overlay, info, spacing=22)
        parts = [top]
        if util.have("powerprofilesctl") and util.run("powerprofilesctl get")[0] == 0:
            parts.append(self.profiles())
        if self.limit_file():
            parts.append(self.limit_slider())
        esc = ui.hint_label("Esc", "close")
        esc.set_hexpand(True)
        esc.set_halign(Gtk.Align.END)
        foot = ui.hbox(ui.hint_label("P", "power profile"),
                       ui.hint_label("Left/Right", "reminder") if self.limit_file() else None, esc, spacing=16)
        foot.add_css_class("urja-foot")
        parts.append(foot)
        return ui.vbox(*parts, spacing=18, cls="card")

    def profiles(self):
        cur = util.run("powerprofilesctl get")[1]
        avail = util.run("powerprofilesctl list")[1]
        box = Gtk.Box(spacing=8, homogeneous=True)
        self.profile_buttons = {}
        for key, label, icon in PROFILES:
            if f"{key}:" not in avail:
                continue
            b = ui.button(label, lambda k=key: self.set_profile(k), "primary" if key == cur else "", icon)
            self.profile_buttons[key] = b
            box.append(b)
        return ui.vbox(ui.label("Power profile", "kv-key", xalign=0), box, spacing=6)

    def set_profile(self, key):
        util.run(["powerprofilesctl", "set", key])
        for k, b in self.profile_buttons.items():
            (b.add_css_class if k == key else b.remove_css_class)("primary")

    def limit_slider(self):
        cur = self.read_limit()
        head = ui.hbox(ui.label("Remind me to unplug at", "kv-val", xalign=0, hexpand=True),
                       ui.label(f"{cur}%" if cur else "off", "urja-limit"), spacing=8)
        self.limit_label = head.get_last_child()
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, len(STOPS) - 1, 1)
        scale.set_draw_value(False)
        scale.set_round_digits(0)
        idx = STOPS.index(cur) if cur in STOPS else 0
        scale.set_value(idx)
        for n, v in enumerate(STOPS):
            scale.add_mark(n, Gtk.PositionType.BOTTOM, "off" if v == 0 else str(v))
        scale.connect("value-changed", self.limit_changed)
        self.scale = scale
        note = ui.label("A reminder, not a hardware cutoff: a nudge to unplug when charging crosses it.", "card-sub",
                        xalign=0, wrap=True)
        return ui.vbox(head, scale, note, spacing=6)

    def limit_changed(self, scale):
        v = STOPS[int(round(scale.get_value()))]
        self.limit_label.set_label(f"{v}%" if v else "off")
        self.write_limit(v)

    def key(self, name, row, mods):
        if name in ("p", "P") and hasattr(self, "profile_buttons") and self.profile_buttons:
            keys = list(self.profile_buttons)
            cur = util.run("powerprofilesctl get")[1]
            self.set_profile(keys[(keys.index(cur) + 1) % len(keys)] if cur in keys else keys[0])
            return True
        if name in ("Left", "Right") and hasattr(self, "scale"):
            v = self.scale.get_value() + (1 if name == "Right" else -1)
            self.scale.set_value(max(0, min(len(STOPS) - 1, v)))
            return True
        return False
