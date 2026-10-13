# Local Validation Evidence Model

Status: Proposed contract, October 12, 2026.

- **Gate specification**: Schema version, source provenance, normalized path rules, module inventory, mode/platform applicability, check IDs, argv, dependency edges, required tools/environment, and finite budgets. Reject duplicate IDs, unknown edges, cycles, unsafe paths, unsupported semantics, and missing bounds.
- **Candidate binding**: Repository/common-directory and index identity, staged tree, HEAD/parent, explicit base, native executable, launcher/source and specification hashes, toolchain identities, dependency lock/observed identities, and relevant environment digest. No credentials or raw environment values in receipts.
- **Run**: Unique owned invocation, candidate binding, selected check IDs and reasons, start/end observations, actual elapsed time, terminal outcome, and private diagnostic references/hashes.
- **Check result**: Actual start/exit or signal, refusal/budget reason, retained log references, produced-byte accounting, and joined ownership disposition. A missing result cannot count as success.
- **Receipt**: Schema version, complete run/check results, final binding recheck, cleanup outcome, and acceptance decision. Accept only complete matching inputs, all required successful checks, and joined cleanup.

Lifecycle: bound → materialized → selected → running → joining → rechecked → accepted or refused. Every started run reaches a terminal retained disposition, including interruption and failed startup. Evidence reuse requires identical relevant bindings and applicable policy; copied or incomplete receipts refuse. Receipts are not reservations and do not grant credentials, canonical admission, or model qualification.
