# Documentation Rules

This document defines formatting and content rules for repository documentation.

Contribution behavior and review expectations are defined in `CONTRIBUTING.md`. These rules are part of that policy.

## Required Structure for Keyboard Docs

Each keyboard document in `docs/*.md` should include:

- Title (`# Keyboard Name`)
- One-line scope statement describing what the document covers
- `Reference Material` section with canonical upstream links
- `Hardware Overview` section
- `Layout` section
  - Physical layout image
  - Keymap image
- `Firmware Structure` section with repository paths
- `How to Use` section
  - Build steps
  - Flashing steps
- `Status` or `Notes` section for current support level and constraints

## Asset Rules

- Thumbnails or hero images should come from original contributors when available.
- Physical layout images should be generated from physical layout tools.
- Keymap images should be generated from the default keymap using keymap-drawer.
- Store images in `docs/images/` with stable names: `<keyboard>_thumbnail.*`, `<keyboard>_layout.svg`, `<keyboard>_keymap.svg`.
- If an image is not available yet, keep the `Layout` section and state clearly that the asset is pending.

## Formatting Rules

- Use clear Markdown headings with consistent section order.
- Keep technical paths in backticks, for example `config/totem.keymap`.
- Use concise bullets for capabilities and constraints.
- Keep procedural steps as numbered lists.
- Keep wording factual; avoid speculative or promotional text.

## Accuracy Rules

- Do not document unsupported build targets as active support.
- Match shield names, board names, and artifact names to real repository files.
- If support is partial, state exactly what exists and what is missing.
- When adding new keyboard docs, also update README keyboard links if needed.

## Maintenance Rules

- If firmware structure changes, update affected docs in the same change set.
- If keymap or layout images are regenerated, replace the existing files instead of creating duplicates.
- If docs rules change, keep `CONTRIBUTING.md` and this file aligned.
