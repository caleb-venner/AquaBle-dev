# TODO

## Urgent

- Connection issues when ingress UI left open but not focused.
- Are we pinging devices too often? If they are known they should be displayed anyway.
- Too much hot-reloading happening, move towards a more static display.

## Next

- Implement: Remaining **Doser Functions**
  - Test, Decode, Implement full dosing pump mode functionality:
    . Daily, Timer, 24hr, Custom, (Disabled)
  - Investigate: manual (single) dose; make-up dose flag; enable? flag; further status request command encoding.
  - Investiage: Priming and calibration process for doser.
  - New screenshots for sites.
- Schedule overlap/collision detection for LED Auto Mode settings.
- Light/Doser devices --> **'reapply' saved configs** --> sends commands to device. *(Especially applies to recovery from power loss instances).*

## Soon

- 'Scenes'; Saved (inactive) device settings that can be reapplied 'in-bulk'.
- Improve: Darkmode text contrast. Increase contrast for UI elements overall.
- Fix: notification popups --> darkmode display.
- Create new dashboard, home; move overview to devices.
- How do we allow end user creation of this (or more) custom dashboards.
  - We have chihiros devices, hass entities and scripts.
  - yaml config?

## Later

- Fix: light status payload (keyframes); need to refine time-check logic. Placeholders inserted.
  [Lines 202 -> 336](src/aquable/storage/models.py#L204) --> Might be redundant.
- Fix: doser lifetime status payload; currently not correctly integrating to device state.
- Implement: remaining doser payload decode. (0x22 (*today's dose*))

### Things to think about

- It seems that if the WRGB II Pro is powered off for too long it looses it's programmed memory. Is it viable/possible to check if the device has been powered off for x amount of time, then connect & write settings to device when it comes back online.
- Do we want to 'write'/send saved settings commands to device when connected to?
- Reaching out to the community for BLE logs of various chihiros devices.
- Potentially branch out to other manufacturers? Would also require community help.
