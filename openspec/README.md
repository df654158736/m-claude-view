# OpenSpec

This repository uses an OpenSpec-style workflow for architecture and behavior changes.

## Layout
- `openspec/specs/`: accepted baseline specs.
- `openspec/changes/<change-id>/proposal.md`: why/what.
- `openspec/changes/<change-id>/tasks.md`: implementation checklist.
- `openspec/changes/<change-id>/specs/<capability>/spec.md`: spec deltas with `## ADDED|CHANGED|REMOVED Requirements`.

## Change Status
A change is considered review-ready when:
- `proposal.md` is complete,
- `tasks.md` is actionable,
- at least one spec delta exists.
