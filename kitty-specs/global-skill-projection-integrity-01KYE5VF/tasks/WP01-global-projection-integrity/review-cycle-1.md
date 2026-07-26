# WP01 Review Cycle 1

**Verdict:** Rejected

## Required corrections

1. `src/specify_cli/runtime/agent_skills.py` returns silently when the canonical
   registry is unavailable. Make this condition observable and prove that it
   cannot leave or write a success lock, as required by C-004 and the global
   projection contract.
2. Replace raw byte equality in the integrity predicate with deterministic
   content hashes for each normalized canonical file and projected counterpart,
   as required by NFR-001 and the contract's integrity rule. Add regression
   coverage for the predicate's divergent-file behavior.

## Review evidence

- Atomic same-directory replacement and explicit retired-name cleanup are sound.
- The focused isolated harness passed before review, but it does not cover the
  two requirements above.
