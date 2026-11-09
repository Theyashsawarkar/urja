"""urja (ऊर्जा, "energy"): the battery at a glance, for Vyom.

A charge ring, time to full or empty, how much power it's drawing, the
battery's health and cycle count, the power profile, and (when
`limit_file` is set) a charge-limit reminder: the percentage a watcher of
yours nudges you to unplug at (Vayu's battery-limit-watch.sh).
"""
import collections
import os
import time

from gi.repository import GLib, Gtk, Pango

from vyom import Plugin as Base
from vyom import Hint, ui, util

from . import battery, vim

REFRESH = 2  # seconds between looks at the battery while the card is open

# KEYBINDS (generated from urja/vim.py by scripts/keybinds.py; don't edit by hand)
# keybind: Vyom/battery:normal | p | Switch to the next power profile
# keybind: Vyom/battery:normal | 0 | Turn the charge-limit reminder off
# keybind: Vyom/battery leader:normal | Space y y | Copy a battery summary (87%, charging, 2 h left)
# keybind: Vyom/battery leader:normal | Space o t | Open the battery's details (upower -i) in a terminal
# END KEYBINDS

PROFILES = [("power-saver", "Power saver", "\U000f0f86"), ("balanced", "Balanced", "\U000f04c5"),
            ("performance", "Performance", "\U000f04c4")]
STOPS = [0, 50, 60, 70, 75, 80, 85, 90, 100]   # 0 = reminder off


SAMPLE = 120  # seconds between our own charge samples (the graph's fallback when UPower has none)

# `vyom urja demo`: made-up numbers, for screenshots and trying the card out.
DEMO = {"name": "BAT0", "capacity": 96, "status": "Charging", "cycles": 600, "tech": "Li-ion", "model": "Primary",
        "maker": "Hewlett-Packard", "plugged": True, "full_wh": 29.9, "watts": 18.2, "health": 63, "hours": 0.2}


class Graph(Gtk.DrawingArea):
    """The charge over the last 3 hours as rounded bars, in the ring's colour
    (taken from its CSS class, so a theme's colours apply); steps with no
    data yet are faint stubs."""

    def __init__(self, color):
        super().__init__(hexpand=True, content_height=50)
        self.add_css_class(f"t-{color}")
        self.steps = []
        self.set_draw_func(self.draw)

    def set_points(self, points):
        self.steps = battery.bins(points)
        self.queue_draw()

    def draw(self, _a, cr, w, h):
        c = self.get_color()
        n = len(self.steps) or 36
        gap = 3
        bw = (w - gap * (n - 1)) / n
        for k in range(n):
            p = self.steps[k] if k < len(self.steps) else None
            x = k * (bw + gap)
            if p is None:
                cr.set_source_rgba(1, 1, 1, 0.07)
                ui._round_rect(cr, x, h - 4, bw, 4, 2)
            else:
                bh = max(4, h * p[1] / 100)
                cr.set_source_rgba(c.red, c.green, c.blue, 0.35 + 0.65 * (k + 1) / n)
                ui._round_rect(cr, x, h - bh, bw, bh, min(3, bw / 2))
            cr.fill()


class Plugin(Base):
    name, title, icon, color = "urja", "Battery", "\U000f0079", "green"
    layout = "card"
    width = 520
    modal = True                # vim keys (Vyom 0.7): always NORMAL; the card cursor moves between controls
    start_mode = "normal"
    hints = [Hint("p", "power profile"), Hint("j / k", "move"), Hint("h / l", "change")]

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

    def __init__(self, vyom, conf):
        super().__init__(vyom, conf)
        # Our own charge samples while the daemon runs: the graph's fallback
        # (and gap filler) when UPower keeps no history.
        self.samples = collections.deque(maxlen=battery.HISTORY // SAMPLE + 10)
        self.sample()
        GLib.timeout_add_seconds(SAMPLE, self.sample)
        self.demo = False

    def sample(self):
        i = battery.info()
        if i and i["capacity"] is not None:
            self.samples.append((time.time(), float(i["capacity"]), i["status"] == "Charging"))
        return True

    def opened(self, args):
        super().opened(args)
        self.demo = "demo" in args

    def info(self):
        if self.demo:
            return dict(DEMO)
        i = battery.info()
        if i and not i["watts"]:
            # No current from the battery: work it out from the charge history.
            est = battery.estimate(i, getattr(self, "hist", []) + list(self.samples))
            if est:
                i["watts"], i["hours"], i["estimated"] = est[0], est[1], True
        return i

    def fetch_history(self):
        """UPower's history over D-Bus, off the main loop; the card picks it
        up on its next tick."""
        def got(r):
            if isinstance(r, list):
                self.hist = r
                if getattr(self, "graph", None) is not None:
                    self.graph.set_points(self.history())
        self.background(battery.upower_history, then=got)

    def history(self):
        if self.demo:   # a laptop charging from 40% over the last 3 hours
            now = time.time()
            return [(now - battery.HISTORY + k * 300, 40 + k * 1.6 if k < 36 else 96, True) for k in range(36)]
        return sorted(getattr(self, "hist", []) + list(self.samples))

    def build_card(self):
        i = self.info()
        if not i:
            return ui.vbox(ui.notice("No battery", "This machine has no battery that the kernel reports.", "yellow"),
                           cls="card")
        if not self.demo:
            self.fetch_history()
        self.shown = self.fingerprint(i)
        self.top_holder = Gtk.Box()
        self.top_holder.append(self.build_top(i))
        self.health_holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        h = self.build_health(i)
        if h is not None:
            self.health_holder.append(h)
        self.watch()
        parts = [self.top_holder, self.health_holder]
        if util.have("powerprofilesctl") and util.run("powerprofilesctl get")[0] == 0:
            parts.append(self.profiles())
        if self.limit_file():
            parts.append(self.limit_slider())
        # The keys are in Vyom's footer (a modal card has one).
        return ui.vbox(*parts, spacing=16, cls="card")

    @staticmethod
    def fingerprint(i):
        """What the top of the card shows: redrawn only when one of these changes."""
        return (i["status"], i["capacity"], i["plugged"], round(i["hours"] or 0, 2), round(i["watts"], 1))

    def watch(self):
        """Keep the card true while it's open: plugging the charger in shows in
        REFRESH seconds. Only the ring, headline and graph are redrawn, so the
        reminder slider and the power profile aren't disturbed."""
        if getattr(self, "watch_id", None) is None:
            self.watch_id = GLib.timeout_add_seconds(REFRESH, self.tick)

    def tick(self):
        self.ticks = getattr(self, "ticks", 0) + 1
        if not self.demo and self.ticks % 30 == 0:
            self.fetch_history()
        i = self.info()
        if i and self.fingerprint(i) != self.shown:
            self.shown = self.fingerprint(i)
            old = self.top_holder.get_first_child()
            if old is not None:
                self.top_holder.remove(old)
            self.top_holder.append(self.build_top(i))
        return True

    def closed(self):
        if getattr(self, "watch_id", None) is not None:
            GLib.source_remove(self.watch_id)
            self.watch_id = None

    @staticmethod
    def ring_color(i):
        cap = i["capacity"] or 0
        if i["plugged"] or cap > 30:
            return "green"
        return "yellow" if cap > 15 else "red"

    def build_top(self, i):
        cap = i["capacity"] or 0
        color = self.ring_color(i)
        state = {"Charging": ("\U000f140b", "charging"), "Discharging": ("\U000f0079", "on battery"),
                 "Full": ("\U000f06a5", "full"), "Not charging": ("\U000f06a5", "plugged in")}
        icon, word = state.get(i["status"], ("\U000f0079", (i["status"] or "unknown").lower()))
        if i["status"] == "Discharging" and cap <= 15:
            word = "low"
        center = ui.vbox(ui.label(f"{cap}%", "urja-pct"),
                         ui.hbox(ui.label(icon, "glyph"), ui.label(word), spacing=4, cls=f"t-{color}"), spacing=0)
        center.get_last_child().set_halign(Gtk.Align.CENTER)
        center.get_last_child().add_css_class("urja-state")
        ring = ui.ring(cap / 100, color, 128, 11, center)
        ring.set_valign(Gtk.Align.CENTER)

        # The headline: when it'll be full, or how long it lasts.
        left = battery.fmt_short(i["hours"])
        if i["status"] == "Charging":
            head = f"Full in {left}" if left else "Charging"
        elif i["status"] == "Discharging":
            head = f"{left} left" if left else "On battery"
        elif i["status"] == "Full":
            head = "Fully charged"
        elif i["plugged"]:
            head = "Plugged in, not charging"
        else:
            head = i["status"] or "Battery"
        if i.get("estimated"):
            head = {"Charging": f"Full in about {left}", "Discharging": f"About {left} left"}.get(i["status"], head)
        if i["watts"]:
            w = f"{'about ' if i.get('estimated') else ''}{i['watts']:.1f} W"
            note = f"+{w} into the battery" if i["status"] == "Charging" else f"Using {w}" \
                if i["status"] == "Discharging" else f"{w}"
            if i.get("estimated"):
                note += ", going by the last half hour"
        elif i["status"] == "Discharging":
            note = "Measuring the power draw…"
        else:
            note = "No power flowing in or out"
        graph = self.graph = Graph(color)
        graph.set_points(self.history())
        axis = ui.hbox(ui.label("3 h ago", "urja-axis", xalign=0, hexpand=True), ui.label("now", "urja-axis"))
        right = ui.vbox(ui.label(head, "urja-head", xalign=0, ellipsize=Pango.EllipsizeMode.END),
                        ui.label(note, "urja-note", xalign=0), spacing=2)
        right.append(ui.vbox(graph, axis, spacing=4, cls="urja-graph"))
        right.set_hexpand(True)
        right.set_valign(Gtk.Align.CENTER)
        return ui.hbox(ring, right, spacing=22)

    def build_health(self, i):
        if not i["health"]:
            return None
        word, color, meaning = battery.health_word(i["health"])
        facts = []
        if i.get("full_wh") and i["watts"] and i["status"] == "Discharging":
            facts.append(f"About {battery.fmt_short(i['full_wh'] / i['watts'])} on a full charge")
        if i["cycles"]:
            facts.append(f"{i['cycles']} cycles")
        maker = " ".join(x for x in (i.get("maker"), i.get("model")) if x)
        if maker:
            facts.append(" ".join(x for x in (maker, i.get("tech")) if x))
        note = meaning + (("\n" + " · ".join(facts)) if facts else "")
        return ui.meter("Health", f"{i['health']}% · {word}", i["health"] / 100, color, note)

    def profiles(self):
        """A segmented control, the current profile filled; p cycles."""
        avail = util.run("powerprofilesctl list")[1]
        self.profile_keys = [k for k, _l, _i in PROFILES if f"{k}:" in avail]
        self.profile_holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.show_profile(util.run("powerprofilesctl get")[1])
        head = ui.hbox(ui.label("Power profile", "urja-label", xalign=0), ui.keycap("p"), spacing=8)
        return ui.vbox(head, self.profile_holder, spacing=7)

    def show_profile(self, cur):
        old = self.profile_holder.get_first_child()
        if old is not None:
            self.profile_holder.remove(old)
        opts = [(k, f"{i}  {l}") for k, l, i in PROFILES if k in self.profile_keys]
        seg = ui.segmented(opts, cur, self.set_profile)
        seg.add_css_class("urja-profiles")
        seg.add_css_class(f"p-{cur}")
        self.profile_holder.append(seg)

    def set_profile(self, key):
        util.run(["powerprofilesctl", "set", key])
        self.show_profile(util.run("powerprofilesctl get")[1])

    def limit_slider(self):
        cur = self.read_limit()
        head = ui.hbox(ui.label("Remind me to unplug at", "urja-label", xalign=0, hexpand=True),
                       ui.label(f"{cur}%" if cur else "off", "urja-limit"), spacing=8)
        self.limit_label = head.get_last_child()
        (self.limit_label.add_css_class if not cur else self.limit_label.remove_css_class)("off")
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, len(STOPS) - 1, 1)
        scale.set_draw_value(False)
        scale.set_round_digits(0)
        scale.add_css_class("urja-scale")
        idx = min(range(len(STOPS)), key=lambda n: abs(STOPS[n] - cur))   # the nearest stop
        scale.set_value(idx)
        for n, v in enumerate(STOPS):
            scale.add_mark(n, Gtk.PositionType.BOTTOM, "off" if v == 0 else str(v))
        scale.connect("value-changed", self.limit_changed)
        self.scale = scale
        note = ui.label("A reminder, not a hardware cutoff: a nudge to unplug when charging crosses it.", "urja-note",
                        xalign=0, wrap=True)
        return ui.vbox(head, scale, note, spacing=4)

    def limit_changed(self, scale):
        v = STOPS[int(round(scale.get_value()))]
        self.limit_label.set_label(f"{v}%" if v else "off")
        (self.limit_label.add_css_class if not v else self.limit_label.remove_css_class)("off")
        if not self.demo:
            self.write_limit(v)

    # ------------------------------------------------------------ vim keys
    def keys(self, tab):
        return vim.keys(tab)

    def v_profile(self, _n, _a):
        keys = getattr(self, "profile_keys", None)
        if not keys:
            self.set_status("no power profiles here (powerprofilesctl)", "bad")
            return
        cur = util.run("powerprofilesctl get")[1]
        self.set_profile(keys[(keys.index(cur) + 1) % len(keys)] if cur in keys else keys[0])

    def v_reminder(self, _n, _a):
        if not hasattr(self, "scale"):
            self.set_status("no charge-limit reminder here", "bad")
            return
        self.scale.set_value(0)

    def v_copy(self, _n, _a):
        i = self.info()
        if not i or i.get("capacity") is None:
            self.set_status("no battery to copy", "bad")
            return
        bits = [f"{i['capacity']}%", (i.get("status") or "").lower()]
        if i.get("hours"):
            h = i["hours"]
            bits.append((f"{h:.1f} h" if h < 10 else f"{h:.0f} h") + (" to full" if i.get("status") == "Charging"
                                                                      else " left"))
        text = ", ".join(b for b in bits if b)
        util.copy(text)
        self.set_status(f"copied: {text}", "ok")

    def v_upower(self, _n, _a):
        name = (self.info() or {}).get("name") or "BAT0"
        term = os.environ.get("TERMINAL") or next((t for t in ("kitty", "foot", "alacritty") if util.have(t)), "xterm")
        util.spawn([term, "-e", "sh", "-c", f"upower -i $(upower -e | grep -m1 {name} || upower -e | grep -m1 BAT); "
                    "echo; read -r -p 'Enter closes' _"])
        self.close()
