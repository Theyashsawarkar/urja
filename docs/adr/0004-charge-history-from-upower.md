# 4. The charge graph comes from UPower's history, over D-Bus

**Status:** Accepted  
**Date:** 2026-11-07

## Context

The card shows the charge over the last three hours. UPower already records every battery's charge (`/var/lib/upower/history-charge-*.dat`), but those files are readable by root only. Some batteries (this HP's) also leave `current_now` empty, so there's no power draw to show.

## Decision

urja asks UPower for the history with `org.freedesktop.UPower.Device.GetHistory("charge", 3 h)` on the system bus, which needs no privileges, off the GTK main loop. It also samples the charge itself every two minutes while Vyom runs, and the graph uses both (UPower's history is lost on its restart). When the battery reports no current, the draw and time left are estimated from how fast the charge moved over the last half hour, and marked "about".

## Consequences

- No root, no new dependency (Gio is already there), works without UPower (the graph then starts when Vyom does).
- Estimates are only shown when there's a steady stretch of at least three minutes with the charge moving.
