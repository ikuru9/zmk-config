# Development

This document describes day-to-day development and local build flow for this repository.

Related references:

- Known non-blocking warning tracker: `docs/known_issues.md`

## Branch Roles

Use the single active development line:

| Branch | Upstream contract |
| --- | --- |
| `main` | ZMK `main` / Zephyr 4.1 |

## CI Workflows

Build and release are matrix-driven via `build.yaml`.

- `.github/workflows/build.yml`: runs the full matrix for relevant pushes/PRs and supports reusable/manual profile-driven builds
- `.github/workflows/release.yml`: builds and publishes firmware release assets using the stable profile
- `.github/workflows/run-tests.yml` and `.github/workflows/test-main.yml`: manually run `tests/west.yml` against ZMK `main` and upload isolated build logs
- `.github/workflows/config-policy-guard.yml`: policy lint plus random matrix sanity builds through `build.yml`

- `.github/workflows/draw-keymaps.yml`: generates keymap drawings and opens a refresh PR
- `.github/workflows/update-changelog.yml`: creates a changelog PR from release metadata

## Recommended Workflow (GitHub Actions)

1. Edit `config/*.keymap`, `config/*.conf`, `build.yaml`, or shield files.
2. Commit and push your branch.
3. Wait for the `Build ZMK firmware` CI workflow. Run the test workflow manually when needed.
4. Download build artifacts from Actions or release assets from Releases.
5. Flash matching firmware files to target devices.

This keeps builds aligned with ZMK `main` in `config/west.yml`.

## External Modules

The active `main` line depends on additional west modules for Raw HID and KeyPeek layer notifications:

- `zmk-raw-hid`
- `zmk-keypeek-layer-notifier`

Run `west update` after manifest changes so the workspace matches `config/west.yml`.

## Configuration Policy (Split Role)

Use this layering to avoid split-side regressions and warning-only misconfigurations:

1. Board/shield role defaults:
   - Put side-specific role and transport defaults in board/shield defconfig files (`Kconfig.defconfig`, `*_defconfig`).
   - Examples: `CONFIG_ZMK_USB`, `CONFIG_ZMK_BLE`, split role flags.
2. Side overlay/conf overrides:
   - Keep side-only overrides in side-specific files (`*_left.conf`, `*_right.conf`) only when needed.
3. User config (`config/*.conf`):
   - Keep this layer side-neutral.
   - Do not set split role or transport ownership here.
4. Shared snippet config (`snippets/common-config/common-config.conf`):
   - Keep this hardware-agnostic.
   - Do not force hardware-specific options globally (for example global `CONFIG_SPI=y`).
5. Shared config references:
   - `snippets/common-config/extra-config.conf` is a commented copy/paste reference.
   - Keep it as reference-only; do not wire it as a global snippet input.

Guardrails:

- `.github/workflows/config-policy-guard.yml` enforces the policy on push/PR.
- The guard runs static policy checks and a lightweight right-side CI build sanity pass.

## Local Build (Docker, CI-like)

One local service is provided in `docker-compose.yml`:

- `zmk-build-stable`: keeps the public service/profile name `stable` while using `zmkfirmware/zmk-build-arm:4.1` for ZMK `main` / Zephyr 4.1.

Use the exact 4.1 image for local builds.

### Prerequisites

- Docker (Docker Desktop or Docker Engine)
- Repository cloned locally

### Short, cross-platform command (recommended)

From repository root:

```bash
# List valid artifact-name values from build.yaml
docker compose run --rm zmk-build-stable --list

# Build selected targets
docker compose run --rm zmk-build-stable --artifact-names totem_left,totem_right,reset_seeeduino_xiao_ble

# Build with wildcard patterns (shell-style)
docker compose run --rm zmk-build-stable --artifact-names "totem_*"
docker compose run --rm zmk-build-stable --artifact-names "*_left,*_right"

# Build in parallel (up to 3 targets at a time)
docker compose run --rm zmk-build-stable --artifact-names "totem_*" --jobs 3

# Build every target in build.yaml
docker compose run --rm zmk-build-stable --all

# Force a clean build for the selected targets
docker compose run --rm zmk-build-stable --artifact-names "totem_*" --pristine

# Refresh west projects, then build the selected targets cleanly
docker compose run --rm zmk-build-stable --artifact-names "totem_*" --update
```

Notes:

- This uses `docker-compose.yml`, `scripts/build_profiles.py`, and `scripts/build_runner.py`.
- Output artifacts are written to `firmware/`.
- Per-target build state is retained under `.build/local/build/`.
- West workspace state and the persistent compiler cache are retained under `.build/local/workspace/`. The cache ignores the image's relative `-specs=picolibc.specs` argument; the pinned image/toolchain keeps that specs file invariant.
- A build command must specify exactly one of `--artifact-names` or `--all`; `--list` needs neither.
- `--artifact-names` accepts exact names and wildcard patterns. An unmatched pattern is an error.
- The first build, a target identity change, a workspace generation change, or `--pristine` runs a pristine configure/build. An unchanged repeat uses `west build -d` against the retained target directory.
- `--update` runs `west update` and `west zephyr-export`, assigns a new workspace generation, and forces each target clean on its next use. A changed `config/west.yml` does the same automatically.
- `--jobs` controls matrix-level parallelism. If omitted, the runner uses at most half the physical cores.
- Ninja jobs are divided across active matrix workers, so nested parallelism remains bounded by the detected physical core count.
- GitHub Actions intentionally invokes `build-one --pristine`; local incremental state does not change CI reproducibility.

### Direct docker run (without compose)

Mount the persistent workspace and set the same compiler cache directory used by Compose:

```bash
docker run --rm -it \
  -v "${PWD}:/workspace" \
  -v "${PWD}/.build/local/workspace:/tmp/zmk-config" \
  -e CCACHE_DIR=/tmp/zmk-config/.ccache \
  -e CCACHE_IGNOREOPTIONS=-specs=picolibc.specs \
  -w /workspace \
  zmkfirmware/zmk-build-arm:4.1 \
  python3 scripts/build_runner.py build-many --profile stable --artifact-names "totem_left,totem_right"

# Parallel example
docker run --rm -it \
  -v "${PWD}:/workspace" \
  -v "${PWD}/.build/local/workspace:/tmp/zmk-config" \
  -e CCACHE_DIR=/tmp/zmk-config/.ccache \
  -e CCACHE_IGNOREOPTIONS=-specs=picolibc.specs \
  -w /workspace \
  zmkfirmware/zmk-build-arm:4.1 \
  python3 scripts/build_runner.py build-many --profile stable --artifact-names "totem_*" --jobs 3
```

### Why not plain CMake?

Use `west build` instead of raw `cmake` for ZMK firmware. `west` handles:

- Zephyr/ZMK workspace initialization
- module resolution from `config/west.yml`
- snippet wiring and board/shield build conventions

The local runner follows the same model as the GitHub workflow and keeps command length short. See the official [ZMK local toolchain guide](https://zmk.dev/docs/development/local-toolchain/build-flash), [Zephyr `west build` guide](https://docs.zephyrproject.org/4.1.0/develop/west/build-flash-debug.html), [`west update` reference](https://docs.zephyrproject.org/latest/develop/west/built-in.html#west-update), and [ccache cache-directory reference](https://ccache.dev/manual/latest.html#config_cache_dir).

## Flashing

For each target device:

1. Connect via USB.
2. Enter bootloader mode (usually double-tap reset).
3. Copy the matching `.uf2` file to the mounted drive.
4. Wait for automatic reboot.

## Quick Troubleshooting

- Unknown `artifact-name`: run `--list` and use an exact name or valid wildcard from `build.yaml`.
- Missing module/build errors: rerun with `--update` to refresh the west workspace.
- `recursive 'source' of 'Kconfig.zephyr' detected`: this usually means a local Zephyr checkout exists under repo `zephyr/`. The local runner now stages only git-visible module files, but cleanup of stale local checkouts still helps (`zephyr/`, `modules/`, `.west/`).
- No `.uf2` output for a target: check for fallback binary output (`.bin`), board type, and build logs.
- Split reconnect problems after flashing: flash reset firmware and re-pair.
