# 3. Read the battery from sysfs

**Status:** Accepted  
**Date:** 2026-10-19

## Context

UPower adds a daemon dependency; the kernel already exposes everything needed.

## Decision

urja reads `/sys/class/power_supply/*` directly, handling both kinds of driver (energy_* / power_now and charge_* / current_now). The power profile comes from powerprofilesctl.

## Consequences

- No extra daemon.
- No battery means the panel says so.
