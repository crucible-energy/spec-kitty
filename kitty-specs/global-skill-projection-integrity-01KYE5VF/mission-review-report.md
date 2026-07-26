---
verdict: fail
mode: post-merge
reviewed_at: 2026-07-26T03:40:15.761070+00:00
findings: 1
gates_recorded:
  - id: gate_1
    name: wp_lane_check
    command: spec-kitty review (internal gate 1)
    exit_code: 0
    result: pass
  - id: gate_2
    name: dead_code_scan
    command: spec-kitty review (internal gate 2)
    exit_code: 0
    result: pass
  - id: gate_3
    name: ble001_audit
    command: spec-kitty review (internal gate 3)
    exit_code: 0
    result: pass
issue_matrix_present: false
mission_exception_present: false
---

## Findings

- **issue_matrix_violation** `MISSION_REVIEW_ISSUE_MATRIX_MISSING`: issue-matrix.md is required in post-merge mode
