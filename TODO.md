# TODO

## General -

### Urgent

- Data types getting convoluted. Status, settings, config, file, memory. Especially doser.
- Still need to nail down metdata + payload --> doser settings modal, overall and head specific.
- Correctly pass light status payload; need to refine time-check logic. Placeholders inserted.
  [Lines 202 -> 336](src/aquable/storage/models.py#L204)
- Correct doser lifetime status payload; currently not correctly integration to device state.
- Implement remaining doser payload decode. (0x22 (today's dose))

### UI

- When new light automode config is sent and saved --> dynamic reload of device card and settings window.
- Add placeholder text on light device cards that have no settings saved.
- Need to decide when/what triggers a payload status request from devies
- Doser Heads not displayed correctly when in dark mode

### Soon

- Should update config API endpoints to be inline with others. [located here](src/aquable/api/routes_configurations.py). Would require refactor --> called, then handle device type.
- Test, Decode, Implement full dosing pump mode functionality:
  . Daily, Timer, 24hr, Custom, (Disabled)
- Investigate: manual (single) dose; make-up dose flag; enable? flag; further status request command encoding.

## Nice to have

- Allow users to reverse integrate hassio plugs/switches etc. Can control them from aquable scenes.
  i.e., control co2 solenoid.
- 'Scenes'; Saved (inactive) device settings; better/more descriptive error handling
- Onboarding process: Load in doser settings from payload decoding. Easier than redoing schedules.
- Look into better logic and decoding for light status payload.

## Things to think about

- Reaching out to the community for BLE logs of various chihiros devices.
- Potentially branch out to other manufacturers? Would also require community help.
