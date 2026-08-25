# Eyelash Corne

This document covers the Eyelash Corne boards, keymap, and dongle targets maintained by this repository.

Eyelash Corne is a Corne-derived split keyboard with dedicated left and right boards, nice!view support, and additional matrix positions for encoder and joystick input.

## Reference Material

- Hardware project: <https://github.com/a741725193/zmk-new_corne>
- ZMK documentation: <https://zmk.dev/docs>
- Continuum framework: [Continuum documentation](continuum.md)

## Repository Structure

- `boards/eyelashperipherals/eyelash_corne/`
  - Dedicated left and right board definitions, layouts, and hardware defaults
- `boards/shields/eyelash_corne/`
  - Dongle shield configuration and overlay
- `config/eyelash_corne.keymap`
  - Eyelash Corne keymap wrapper
- `config/eyelash_corne.conf`
  - User-level feature configuration
- `config/eyelash_corne.json`
  - Physical layout data used by keymap-drawer
- `config/continuum/matrix/eyelash_corne36.h`
  - 36-key Continuum position mapping with additional hardware positions
- `config/continuum/matrix/eyelash_corne42.h`
  - 42-key Continuum position mapping used by the current keymap

## Build Targets

| Target | Board | Shields | Snippets |
| --- | --- | --- | --- |
| `eyelash_corne_left` | `eyelash_corne_left//zmk` | `nice_view raw_hid_adapter` | `common-config studio-rpc-usb-uart` |
| `eyelash_corne_right` | `eyelash_corne_right//zmk` | `nice_view` | none |
| `eyelash_corne_left_w_dongle` | `eyelash_corne_left//zmk` | `nice_view` | none |
| `eyelash_corne_dongle` | `nice_nano//zmk` | `eyelash_corne_dongle raw_hid_adapter` | `common-config studio-rpc-usb-uart` |
| `eyelash_corne_zdd_dongle` | `nice_nano//zmk` | `eyelash_corne_dongle raw_hid_adapter zdd_adapter dongle_display` | `common-config studio-rpc-usb-uart` |
| `eyelash_corne_prospector_dongle` | `xiao_ble//zmk` | `eyelash_corne_dongle raw_hid_adapter prospector_adapter` | `common-config studio-rpc-usb-uart prospector-config` |

Shared reset artifacts remain available as `reset_nice_nano_v2` and `reset_seeeduino_xiao_ble`.

## Operating Modes

### Direct Split

Flash `eyelash_corne_left.uf2` and `eyelash_corne_right.uf2`. The left half is the central device and connects directly to the host.

### Dongle Split

Flash `eyelash_corne_left_w_dongle.uf2` to the left half, `eyelash_corne_right.uf2` to the right half, and one of the following dongle artifacts:

- `eyelash_corne_dongle.uf2` for a headless nice!nano dongle
- `eyelash_corne_zdd_dongle.uf2` for ZMK Dongle Display
- `eyelash_corne_prospector_dongle.uf2` for Prospector hardware

In dongle mode the keyboard halves connect to the dongle, and the dongle connects to the host.

## Flashing

1. Put the target board into bootloader mode.
2. Copy the matching `.uf2` artifact to the mounted bootloader drive.
3. Flash both keyboard halves before pairing.
4. When switching between direct and dongle modes, flash the applicable shared reset artifact first if stale bonds prevent reconnection.

Artifact names and board/shield combinations are authoritative in `build.yaml`.
