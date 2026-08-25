# Security Policy

## Supported Versions

This repository is maintained as a rolling ZMK configuration project.
Security fixes are applied to actively maintained targets only.

| Version / Branch | Supported | Notes |
| --- | --- | --- |
| `main` | :white_check_mark: | Primary maintenance branch. Security fixes land here first. |
| Latest GitHub release tag | :white_check_mark: | Backports are provided when practical. |
| Older release tags | :x: | Upgrade to `main` or the latest release. |
| Forks and archived copies | :x: | Not maintained by this repository. |

## Reporting a Vulnerability

Please report vulnerabilities privately through GitHub Security Advisories:

1. Open the repository `Security` tab.
2. Select `Report a vulnerability`.
3. Submit details with reproduction steps and impact.

Do not open public issues for unpatched vulnerabilities.

If GitHub private reporting is unavailable, open a minimal issue requesting a
private contact channel without posting exploit details.

## What to Include

Include as much of the following as possible:

- Affected files and targets (board/shield/keymap/workflow)
- Commit SHA, release tag, or branch
- Reproduction steps or proof of concept
- Expected impact and attack scenario
- Suggested mitigation (if known)

## Response Targets

- Initial acknowledgement: within 3 business days
- Triage decision: within 7 business days
- Status updates: at least once per week while active

If accepted, fixes are developed on `main` and released as part of the next
available release cycle. If declined, a short rationale will be provided.

## Disclosure

Please allow reasonable time for investigation, patching, and validation before
public disclosure.
