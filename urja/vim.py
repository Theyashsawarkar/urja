"""urja's vim keys, as data. A card: always NORMAL (nothing to type), and
Vyom's card cursor moves between its controls: j / k from the power
profiles to the reminder slider, h / l move the profile focus or the
slider (a count first: 3l), 0 / $ the slider's ends, Enter picks the
focused profile.

An action "verb:arg" runs Plugin.v_<verb>(count, arg) in urja/__init__.py,
or Vyom's own (moved, nop...).
"""
from vyom.keys import Bind

B = Bind
CARD = True

NORMAL = [
    B("p", "profile", "Switch to the next power profile"),
    B("0", "reminder:off", "Turn the charge-limit reminder off"),
]

LEADER = [
    B(" yy", "copy", "Copy a battery summary (87%, charging, 2 h left)"),
    B(" ot", "upower", "Open the battery's details (upower -i) in a terminal"),
]

SECTIONS = [
    ("battery", "normal", "Keys (it's always in NORMAL mode: there's nothing to type)", NORMAL),
    ("battery leader", "normal", "Leader (Space)", LEADER),
]


def keys(_tab):
    return NORMAL + LEADER
