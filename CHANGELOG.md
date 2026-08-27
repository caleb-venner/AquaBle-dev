# Changelog

All notable changes to AquaBle are documented here.

---

## [v4.0.0] — 2026-08-27

> ⚠️ **Breaking change**: Configuration will need to be re-entered after upgrading. See [README](README.md) for setup instructions.

### Dashboard Cards (New)

Two purpose-built Lovelace cards are now automatically registered on installation — no manual resource setup needed.

**Light Card** (`aquable-light-card`):
- Interactive 24-hour SVG ramp curve visualiser across all active schedules with a live time-of-day marker.
- Add, edit, and delete individual schedule slots directly from the card.
- Per-channel peak brightness sliders (Red, Green, Blue, White), ramp duration, and active weekday selection.
- Instant manual brightness override and mode switcher (Auto, Manual, Off).

**Doser Card** (`aquable-doser-card`):
- 4-head monitoring grid with live progress bars (dosed today vs daily target).
- Per-head active/disabled toggle and quick manual dose buttons.
- Per-head schedule configuration (target volume, run time, weekday filter).

### Architecture
- Stateless functional architecture — Home Assistant is the source of truth for all schedule configuration.
- Real-time channel brightness sensors interpolated locally every second with zero BLE polling overhead.

### Sensors
- **Dosing Pump**: Dosed Today, Target Dose, Schedule Time, Mode, and Lifetime Total per head (1–4).
- **LED Light**: Active Schedules (with full definitions in attributes), Hardware Sync status, and Live Channel Brightness per channel.

### Services / Actions
- `aquable.light_set_auto_schedule` — add or update a schedule slot.
- `aquable.light_delete_auto_schedule` — delete an individual schedule slot from hardware.
- `aquable.light_clear_schedules` — wipe all schedules from device memory.
- `aquable.light_set_manual_mode` — set static channel brightness levels.
- `aquable.light_set_mode` — switch between Auto, Manual, and Off.
- `aquable.doser_set_daily_dose_sequence` — configure a full daily dosing schedule per head.
- `aquable.doser_manual_dose` — trigger an immediate one-shot dose.

### Device Support
- Added `DYNT90` support (Chihiros WRGB II) — thanks to [@dmitry-puchkov](https://github.com/dmitry-puchkov).

---

## [v2.2.6] — Prior Release

See [GitHub Releases](https://github.com/caleb-venner/AquaBle/releases) for earlier version history.
