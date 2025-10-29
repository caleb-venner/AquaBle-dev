# TODO

## Urgent

- Fix: light status payload (keyframes); need to refine time-check logic. Placeholders inserted.
  [Lines 202 -> 336](src/aquable/storage/models.py#L204)
- Fix: doser lifetime status payload; currently not correctly integrating to device state.
- Implement: remaining doser payload decode. (0x22 (*today's dose*))
- Improve: Darkmode text contrast. Increase contrast for UI elements overall.

## Soon

- If device is already connected, should not display in scan return.
- If **known device**, should display device card with a disconnected status indicator.
- Implement: Add button within dashboard linking to addon settings page. (Possible?)
- Improve: **Light** device card; **auto settings** change **colours** --> green current, blue active, grey disabled. --> Requires improved command settings logic.
- Improve: Need to decide when/what triggers a payload **status request** from devices.
- Schedule overlap/collision detection for LED Auto Mode settings.
- Light/Doser devices --> **'reapply' saved configs** --> sends commands to device. *(Especially applies to recovery from power loss instances).*

## Later

- Test, Decode, Implement full dosing pump mode functionality:
  . Daily, Timer, 24hr, Custom, (Disabled)
- Investigate: manual (single) dose; make-up dose flag; enable? flag; further status request command encoding.

### Nice to have

- Allow users to reverse integrate hassio plugs/switches etc. Can control them from aquable scenes.
  i.e., control co2 solenoid.
- 'Scenes'; Saved (inactive) device settings; better/more descriptive error handling

### Things to think about

- It seems that if the WRGB II Pro is powered off for too long it looses it's programmed memory. Is it viable/possible to check if the device has been powered off for x amount of time, then connect & write settings to device when it comes back online.
- Do we want to 'write'/send saved settings commands to device when connected to?
- Reaching out to the community for BLE logs of various chihiros devices.
- Potentially branch out to other manufacturers? Would also require community help.
