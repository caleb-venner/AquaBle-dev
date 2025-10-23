# TODO

## General -

### Urgent

- Correctly pass light status payload; need to refine time-check logic. Placeholders inserted.
  [Lines 202 -> 336](src/aquable/storage/models.py#L204)
- Correct doser lifetime status payload; currently not correctly integration to device state.
- Implement remaining doser payload decode. (0x22 (today's dose))

### UI

- When new light automode config is sent and saved --> dynamic reload of device card and settings window.
- Add placeholder text on device cards that have no settings saved.
- Metadata device name not loading on light device card.
- Need to decide when/what triggers a payload status request from devies

### Soon

- Test, Decode, Implement full dosing pump mode functionality:
  . Daily, Timer, 24hr, Custom, (Disabled)
- Investigate: manual (single) dose; make-up dose flag; enable? flag; further status request command encoding.

- **All device types currently store 'channels' for a doser this is blank; all dosers currently treated as 4 channels. Could implement a system whereby dosing heads are treated as channels. This opens up an easy way to implement 2 and 4 channel dosers.**

## Nice to have

- Allow users to reverse integrate hassio plugs/switches etc. Can control them from aquable scenes.
  i.e., control co2 solenoid.
- 'Scenes'; Saved (inactive) device settings; better/more descriptive error handling
- Onboarding process: Load in doser settings from payload decoding. Easier than redoing schedules.
- Look into better logic and decoding for light status payload.

## Things to think about

- Reaching out to the community for BLE logs of various chihiros devices.
- Potentially branch out to other manufacturers?
