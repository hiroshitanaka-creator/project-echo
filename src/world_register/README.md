# world_register

**Status: intentional placeholder — no Python implementation**

This directory is kept in VCS as a namespace anchor for future World Register metadata and signed snapshots
(related to the OpenAI World Register threat model documented in `docs/openai_world_register_threat.md`).

## What this is NOT

- There is no `__init__.py` or importable Python module here.
- No functionality is implemented as of v1.1.0.

## Design decision (v1.1.0)

Implementing a world-register integration layer is out of scope for the current release cycle.
The threat model countermeasures are currently handled by `src/po_echo/gumdrop_defense.py`.

**If you find this directory with no implementation plans on record, treat it as a candidate for removal.**
Remove this directory and update this decision log when the scope is formally closed.
