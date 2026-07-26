# Decision Moment `01KYE5YMW4WEH1G43A02H50CRT`

- **Mission:** `global-skill-projection-integrity-01KYE5VF`
- **Origin flow:** `plan`
- **Slot key:** `integrity_state_storage`
- **Input key:** `global_projection_health`
- **Status:** `resolved`
- **Created:** `2026-07-26T03:02:00.836175+00:00`
- **Resolved:** `2026-07-26T03:02:23.589130+00:00`
- **Resolved by:** `codex`
- **Opened by:** `codex`
- **Other answer:** `false`

## Question

Should this recovery slice introduce a new global projection manifest or compare the installed tree directly with the canonical registry?

## Options

- Introduce a global projection manifest
- Compare directly with canonical registry

## Final answer

Compare directly with canonical registry

## Rationale

The registry is the existing canonical source. A new manifest would duplicate authority and itself need recovery; direct hash comparison keeps this slice small, deterministic, and self-validating.

## Change log

- `2026-07-26T03:02:00.836175+00:00` — opened
- `2026-07-26T03:02:23.589130+00:00` — resolved (final_answer="Compare directly with canonical registry")
