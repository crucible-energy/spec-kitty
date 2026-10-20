# Engineering decisions

- Canonical discovery remains the repository-identity authority. An explicit
  ownership claim selects operation custody through the existing checkout
  validator; foreign and nested claims reuse its typed refusals.
- The selected checkout supplies versioned profiles and governance as well as
  records, evidence references and commits. Do not read one branch's profile
  configuration while writing another branch's record.
- Primary and selected checkout protection policies are both checked before
  executor construction. Read-only routing does not require a writable branch.
  Resolve the primary branch without feature bias and decline operator/mission
  bypasses for this PR-only authoring flow. Other policy callers retain their
  existing default behavior.
- The existing close contract carries the absolute owned path with shell
  quoting. Its internal payload slot is excluded from both public JSON shapes.
  Completion repeats ownership and protection checks; no new protected-branch
  capability or override is introduced.
- Capture the opening branch in the append-only started event and revalidate
  it before agent completion writes. Changing an untracked record's checkout
  to another feature branch cannot transfer custody. Older records without
  this optional field and historical doctor-sweep closure retain their paths.
- Explicit completion discovers canonical identity from the supplied owned
  checkout, so the generated instruction also works outside a repository.
- Non-Git legacy callers retain their established context-resolution errors.
  New Git-backed records carry branch custody; the executor's public method
  signatures and doctor-sweep recording surface are unchanged.
- Keep Python CLI/ownership glue in its existing layer. Preserve the sibling
  native Zig validation work without rewriting it or attributing this routing
  behavior to it.
