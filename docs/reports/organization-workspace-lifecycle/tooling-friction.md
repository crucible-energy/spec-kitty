# Tooling friction

The independently owned implementation log is [approach.md](approach.md).

- The legacy and canonical task-finalization command names are easy to confuse. The legacy command could not find the feature-owned mission; the canonical mission command resolved it and correctly refused missing machine-readable requirement mappings. Add mappings rather than bypassing the gate.
- A test-only help expectation initially omitted Typer’s required-option marker and range formatting. The documented new option contract was corrected; no existing command contract was weakened.
- Ambient Git environment overrides and broad child enumeration were exposed by independent review and red regressions before publication. Real separate-Git-directory fixtures then exposed trailing-path-whitespace identity collapse. These are discovery correctness failures, not cleanup permissions.
- An optional whole-legacy-doctor strict typing probe retains one existing `Any` return in an untouched sanction-snippet wrapper. The exact base source reproduces it using mypy’s shadow-file facility. New domain/ingress/kernel modules pass configured strict typing; no suppression was added.
- Do not use a full registry-importing CLI from Codex SessionEnd’s maximum-three-second callback. The later event bridge must have a bounded startup path and defer scans/retirement to the lifecycle coordinator.
