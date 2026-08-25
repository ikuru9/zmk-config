#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

fail=0

report_violation() {
  local title="$1"
  local details="$2"
  echo "::error title=${title}::${title}"
  echo "${details}"
  fail=1
}

check_forbidden_in_paths() {
  local title="$1"
  local pattern="$2"
  shift 2
  local paths=("$@")
  local output

  output="$(rg -n --color never "${pattern}" "${paths[@]}" 2>/dev/null || true)"
  if [[ -n "${output}" ]]; then
    report_violation "${title}" "${output}"
  fi
}

check_forbidden_in_globbed_files() {
  local title="$1"
  local pattern="$2"
  local base="$3"
  local glob="$4"
  local output

  output="$(rg -n --color never --glob "${glob}" "${pattern}" "${base}" 2>/dev/null || true)"
  if [[ -n "${output}" ]]; then
    report_violation "${title}" "${output}"
  fi
}

# 1) Shared user config must stay side-neutral.
check_forbidden_in_globbed_files \
  "Role-specific options must not be set in config/*.conf" \
  "^(CONFIG_ZMK_USB|CONFIG_ZMK_BLE|CONFIG_ZMK_SPLIT_ROLE_CENTRAL|CONFIG_ZMK_SPLIT_BLE_ROLE_CENTRAL)=" \
  "config" \
  "*.conf"

# 2) Right shield .conf files should not own USB/BLE role defaults.
check_forbidden_in_paths \
  "Right shield .conf must not set USB/BLE defaults" \
  "^(CONFIG_ZMK_USB|CONFIG_ZMK_BLE)=" \
  "boards/shields/totem/totem_right.conf"

# 3) Eyelash user configs should not force encoder options for both sides.
check_forbidden_in_paths \
  "Eyelash user config must not force EC11 settings" \
  "^(CONFIG_EC11|CONFIG_EC11_TRIGGER_GLOBAL_THREAD)=" \
  "config/eyelash_corne.conf"

# 4) Deprecated ext-power label usage should not be reintroduced.
check_forbidden_in_paths \
  "Deprecated EXT_POWER label must not be used" \
  "label\\s*=\\s*\"EXT_POWER\"\\s*;" \
  "boards"

# 5) Shared common config must not globally force SPI.
check_forbidden_in_paths \
  "Shared common-config must not force CONFIG_SPI=y" \
  "^CONFIG_SPI=y$" \
  "snippets/common-config/common-config.conf"

if [[ "${fail}" -ne 0 ]]; then
  echo "Config policy guard failed."
  exit 1
fi

echo "Config policy guard passed."
