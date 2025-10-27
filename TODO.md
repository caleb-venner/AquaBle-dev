# TODO

## Urgent

- Improve: Check dynamic loading of device cards for: connection, disconnection, settings modifications, and import config.
- Fix: light status payload (keyframes); need to refine time-check logic. Placeholders inserted.
  [Lines 202 -> 336](src/aquable/storage/models.py#L204)
- Fix: doser lifetime status payload; currently not correctly integrating to device state.
- Implement: remaining doser payload decode. (0x22 (today's dose))

## Soon

- Light device card; auto settings change colours --> green current, blue active, grey disabled.
- Improve: Need to decide when/what triggers a payload status request from devies
- Fix: Doser Heads not displayed correctly when in dark mode

## Later

- Test, Decode, Implement full dosing pump mode functionality:
  . Daily, Timer, 24hr, Custom, (Disabled)
- Investigate: manual (single) dose; make-up dose flag; enable? flag; further status request command encoding.

### Nice to have

- Allow users to reverse integrate hassio plugs/switches etc. Can control them from aquable scenes.
  i.e., control co2 solenoid.
- 'Scenes'; Saved (inactive) device settings; better/more descriptive error handling

### Things to think about

- Reaching out to the community for BLE logs of various chihiros devices.
- Potentially branch out to other manufacturers? Would also require community help.
