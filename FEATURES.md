# AquaBle Features & Protocol Encodings

This document serves as a reference to planned feature implementations.

---

## Doser: Calibration

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

## Sensors: Read-only

### Light Devices

**Exposed sensors for each light device:**

- Current Schedule (Danw/Dusk/Ramp/Peak Brightness; etc.)
- Upcoming Schedule(s)
- LED Channel Value Current

### Doser Heads

**Exposed sensors for each individual dose-head on dosing pump device:**

- Configured Schedule
- Dosed Today
- Dosed Lifetime
- Name
