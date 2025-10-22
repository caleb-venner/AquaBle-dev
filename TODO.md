# TODO

## General -

- When new light automode config is sent and saved --> dynamic reload of device card and settings window.
- Onboarding process: Load in doser settings from payload decoding. Easier than redoing schedules.
- Need to decide when/what triggers a payload status request from devies
- Test, Decode, Implement full dosing pump mode functionality:
  . Daily, Timer, 24hr, Custom, (Disabled)
- Investigate: manual (single) dose; make-up dose flag; enable? flag; further status request command encoding.
- Add placeholder text on device cards that have no settings saved.
- Handle doser status payload updates --> device state.
- **All device types currently store 'channels' for a doser this is blank; all dosers currently treated as 4 channels. Could implement a system whereby dosing heads are treated as channels. This opens up an easy way to implement 2 and 4 channel dosers.**

## Nice to have

- Allow users to reverse integrate hassio plugs/switches etc. Can control them from aquable scenes.
  i.e., control co2 solenoid.
- 'Scenes'; Saved (inactive) device settings; better/more descriptive error handling

## Things to think about

- Reaching out to the community for BLE logs of various chihiros devices.
- Potentially branch out to other manufacturers?
