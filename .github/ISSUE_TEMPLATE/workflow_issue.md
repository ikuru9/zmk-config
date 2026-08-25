---
name: Workflow issue
about: Report failures or regressions in GitHub Actions workflows
title: "[CI] "
labels: ci, workflow, triage
assignees: ""
---

## Workflow file

Which workflow failed?

Example: `.github/workflows/build.yml`

## Workflow run URL

Paste the GitHub Actions run link.

## Failing job and step

Identify the failing job and step name.

## Trigger type

- [ ] `push`
- [ ] `pull_request`
- [ ] `workflow_dispatch`
- [ ] `schedule`
- [ ] `release`
- [ ] Other (describe below)

If `Other`, describe the trigger event:

## Expected behavior

Describe what you expected the workflow to do.

## Actual behavior

Describe what failed and how it failed.

## Reproduction steps

1.
2.
3.

## Relevant logs or errors

```text
Paste key log lines or error messages.
```

## Repository state

- Commit SHA:
- Branch:
- Build target(s) affected (if known):
- Related changed file paths:

## Additional context

Add any related PR, issue, or release context.
