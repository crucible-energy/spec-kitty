# Decision Moment `01KYE5YM2CXZYNJ0MF1XY66PD2`

- **Mission:** `global-skill-projection-integrity-01KYE5VF`
- **Origin flow:** `plan`
- **Slot key:** `recovery_granularity`
- **Input key:** `damaged_global_projection`
- **Status:** `resolved`
- **Created:** `2026-07-26T03:02:00.012980+00:00`
- **Resolved:** `2026-07-26T03:02:22.786149+00:00`
- **Resolved by:** `codex`
- **Opened by:** `codex`
- **Other answer:** `false`

## Question

When any managed global skill file is missing or divergent, should recovery patch that file alone or reuse the existing full managed-root synchronization primitive?

## Options

- Patch only the damaged file
- Synchronize the complete managed root

## Final answer

Synchronize the complete managed root

## Rationale

The existing root synchronizer is ownership-safe, canonicalizes all managed files together, preserves unrelated user paths, and avoids leaving a partially repaired package after an interrupted migration.

## Change log

- `2026-07-26T03:02:00.012980+00:00` — opened
- `2026-07-26T03:02:22.786149+00:00` — resolved (final_answer="Synchronize the complete managed root")
