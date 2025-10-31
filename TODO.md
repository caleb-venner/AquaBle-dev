# TODO

## Test in Ingress

- Config and function: ping(status update)
- Button for addon settings page. Incorrect format. Should be: <https://address/hassio/addon/8d20ab73_aquable/config>

## Next

- Deprecate: device-config-modal.ts; functionality refactored to flip-side of device card.
- Fix: light status payload (keyframes); need to refine time-check logic. Placeholders inserted.
  [Lines 202 -> 336](src/aquable/storage/models.py#L204)
- Fix: doser lifetime status payload; currently not correctly integrating to device state.
- Implement: remaining doser payload decode. (0x22 (*today's dose*))
- Improve: Darkmode text contrast. Increase contrast for UI elements overall.

## Soon

- Improve: appearance and UX of device command settings modals.
- Fix: notification popups --> darkmode display.
- If **known device**, should display device card with a disconnected status indicator.
- Schedule overlap/collision detection for LED Auto Mode settings.
- Light/Doser devices --> **'reapply' saved configs** --> sends commands to device. *(Especially applies to recovery from power loss instances).*

## Later

- Test, Decode, Implement full dosing pump mode functionality:
  . Daily, Timer, 24hr, Custom, (Disabled)
- Investigate: manual (single) dose; make-up dose flag; enable? flag; further status request command encoding.
- Investiage: Priming and calibration process for doser.
- New screenshots for sites.

### Nice to have

- Allow users to reverse integrate hassio plugs/switches etc. Can control them from aquable scenes.
  i.e., control co2 solenoid.
- 'Scenes'; Saved (inactive) device settings; better/more descriptive error handling

### Things to think about

- It seems that if the WRGB II Pro is powered off for too long it looses it's programmed memory. Is it viable/possible to check if the device has been powered off for x amount of time, then connect & write settings to device when it comes back online.
- Do we want to 'write'/send saved settings commands to device when connected to?
- Reaching out to the community for BLE logs of various chihiros devices.
- Potentially branch out to other manufacturers? Would also require community help.
