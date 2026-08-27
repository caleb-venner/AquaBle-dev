# AquaBle Integration Status

## TODO

- [ ] Give feedback / toast notification on push schedule to device
- [ ] Investigate schedule collisions (what occurs when writing a schedule overlapping an existing timeframe)
- [x] Feature: Implement deletion / editing of individual schedule slots in the UI card
- [ ] BUG: When pushing 0;0;0;7 to device (just 7% white light) the schedule saved shows 7;0;0;7 

## Open Requests

*None currently pending.*


## Planned Features

### Doser: Calibration

**Concept:** When silicone tubes wear out, a pump that is supposed to dose 10ml might only dose 9ml. Calibration involves telling the pump to run for a set time, measuring the actual liquid dispensed, and reporting that value back to the pump so it can adjust its flow-rate multiplier. This is currently a feature within the Chihiros app, BLE communications not yet captured or decoded.

### Encoding Details
* **Source:** **Currently Missing.** 
* Neither this codebase nor the upstream `TheMicDiet` repository currently contains the byte encoding for pump calibration.

**How we will get it:**
To implement this correctly, we will need to perform a BLE packet sniff from the official *My Chihiros App*:
1. Start a Bluetooth snoop log on a device.
2. Open the app and run the calibration sequence for a pump head.
3. Looking for commands sent right after the calibration completes (likely an `0xA5` command) containing the user-input volume.

**Logic Flow (Once reversed):**
- Expose an HA Service: `aquable.doser_calibrate_head`. 
- Call it with `head_index: 1` and `actual_volume_dispensed_ml: 9.5`. 
- The service will translate this into the calibration bytes, pushing the new multiplier directly to the device.

---
