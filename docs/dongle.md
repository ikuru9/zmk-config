# Dongle

This document is the repository-specific technical guide for dongle operation.

## Scope

- This guide describes dongle roles used in this repo.
- Dongle role is fixed by firmware build and cannot be switched at runtime.
- Changing role requires reflashing dongle firmware, and may also require reflashing keyboard firmware.

## Dongle Roles

This repository actively builds the `dongle` role. The `scanner` role below is a planned external track:

- `dongle`
  - Single-keyboard dongle role.
  - The non-display variant is the headless dongle.
  - Display-backed builds such as `zdd` and `prospector` still use the same `dongle` role.
  - Intended for single-keyboard daily use with a fixed pairing set.
- `scanner`
  - Dongle passively scans keyboard status advertisements and renders status UI.
  - It is an observer role, not a BLE input transport path.

## Role Architecture Diagrams

These diagrams are conceptual and describe firmware role topology only.

### `dongle` role (single-keyboard; headless or display-backed)

```text
[Keyboard Left] ----\
                     >==== BLE split link ====> [Keyboard Right]
                                     |
                                     | BLE (input transport)
                                     v
                              [Dongle (role=dongle)]
                                     |
                                     | USB or BLE
                                     v
                                   [Host]
```

### `scanner` role (status observer)

```text
[Keyboard(s)] -- status advertisements --> [Dongle (role=scanner)] --> [Display/UI]
     |
     +-- input path to host is separate (scanner is not input transport)
```

## Dongle Hardware Variants

This repo uses two dongle hardware families:

- ZMK Dongle Display (`zdd`) hardware
- Prospector hardware

Firmware direction in this repo:

- `zdd` hardware uses ZMK Dongle Display firmware family (`dongle`)
- `prospector` hardware uses [`carrefinho/prospector-zmk-module@feat/new-status-screens`](https://github.com/carrefinho/prospector-zmk-module/tree/feat/new-status-screens) with the Operator layout (`dongle`)

## Role Switching Rules

1. Build or download firmware for the target role.
2. Flash the dongle with that role firmware.
3. If required by topology change, flash matching keyboard firmware.
4. Clear stale BLE bonds before pairing again.

Role switching is a reflash workflow, not a runtime toggle.

## Naming Convention

This repository uses a fixed naming policy for dongle targets:

- Single-keyboard dongle role targets:
  - `<keyboard>_<hardware>_<role>`
  - Examples:
    - `totem_zdd_dongle`
    - `totem_prospector_dongle`
- Planned external role targets (`scanner`):
  - `<hardware>_<role>`
  - Example:
    - `prospector_scanner`

Frozen identifiers:

- Hardware IDs: `zdd`, `prospector`
- Role IDs: `dongle`, `scanner`

## Concrete Build Examples

These examples are naming and matrix templates.
Some are planned-only depending on current matrix coverage.

1. `zdd` + `dongle` role (display-backed single-keyboard)
   - `board: nice_nano//zmk`
   - `shield: totem_dongle raw_hid_adapter zdd_adapter dongle_display`
   - `artifact-name: totem_zdd_dongle`
2. `prospector` + `dongle` role (display-backed single-keyboard)
   - `board: xiao_ble//zmk`
   - `shield: totem_dongle prospector_adapter`
   - `artifact-name: totem_prospector_dongle`
3. Planned external `prospector` + `scanner` role
   - `board: xiao_ble//zmk`
   - `shield: prospector_scanner`
   - `artifact-name: prospector_scanner`

## Current Build Coverage

Current state from `build.yaml`:

- Active dongle-related entries:
  - Split targets for Totem and Eyelash Corne.
  - Display-backed ZDD and Prospector dongle targets for Totem and Eyelash Corne.
  - Raw HID remains enabled where listed explicitly; the Totem Prospector target disables it to preserve reliable primary USB keyboard HID enumeration.
  - Shared reset targets: `reset_nice_nano_v2`, `reset_seeeduino_xiao_ble`.
- Scanner integration is a planned external track and is not connected to the current `build.yaml` or Prospector module.

## `scanner` Role: Status Observer Model

### Concept

- Scanner listens for status advertisements from compatible keyboard firmware.
- Scanner does not replace keyboard-to-host input routing.
- Scanner display is independent from host BLE stack quality.
- In this repository, scanner remains a Prospector-only external track.

### Requirements

- Keyboard firmware must enable status advertisement.
  - Scanner firmware integration is Prospector-track and not built from this repository matrix.
- Channel settings must match your intended topology.
  - `CONFIG_PROSPECTOR_CHANNEL` on keyboards
  - `CONFIG_PROSPECTOR_SCANNER_CHANNEL` on scanner
  - `0` means broadcast/accept-all.

## Bond Reset Methods

Use one of these reset methods when reconnect behavior is unstable or after role changes:

- Flash `settings_reset` firmware (if target is available in your build matrix).
- Press a keyboard key mapped to `BT_CLR` (`&bt BT_CLR`) to clear BLE bonds.

## Personal Trade-off Notes

I still think the advantage of dongles is often overrated.

In this repo, dongle mode is mostly a role-based workaround, not a universal upgrade.

### `dongle` role

- Practical for a single-keyboard setup, whether headless or display-backed, when host BLE behavior is inconsistent.
- Main gain is predictable reconnect behavior and stable host pathing.
- Compared to wired master split, benefits are limited and you still carry an extra dependency.

### `scanner` role

- This is still the clearest value case among dongle roles.
- Dedicated status UI offload is useful and can stay independent from host input transport.
- It is still additive hardware, so value depends on whether you actually use status surfaces.

### Bottom line

Most dongle benefits are comparative against weak host BLE stacks, not fundamental transport improvements over wired. For this repo, dongle is best treated as a targeted tool per role: `dongle` for single-keyboard stability and `scanner` for UI/status observability.

## Related References

- [README Dongle section](../README.md#dongle)
- [ZMK Dongle Display](https://github.com/englmaxi/zmk-dongle-display)
- [Prospector ZMK Module (active Operator screen)](https://github.com/carrefinho/prospector-zmk-module/tree/feat/new-status-screens)
- [Prospector Scanner Module (external track)](https://github.com/t-ogura/prospector-zmk-module)
- [zmk-config-prospector](https://github.com/t-ogura/zmk-config-prospector)
