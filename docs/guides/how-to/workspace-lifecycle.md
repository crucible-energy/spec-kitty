# Organization workspace lifecycle

## Discovery and accounting

`spec-kitty doctor organization-workspaces --root /absolute/local/root` queries the accessible repositories in `crucible-energy` through the configured GitHub CLI credential with bounded pagination, then scans the explicitly supplied local roots and reads each matched store’s registered workspaces. Repeat `--root` for independent clones and other workspace locations. No initialized Spec Kitty project is needed. `--organization` selects a different organization; default scan bounds are depth 6, 10,000 directories and 100,000 directory entries.

The command emits JSON. Each observed workspace is retained with `ownership_unknown`; origin matching is discovery evidence, never owner release or cleanup permission. It includes primary checkouts, independent stores and worktrees outside the scan roots when their Git registry identifies them. No files, refs, Git configuration, ownership leases or workspaces are changed. It does not fetch remote refs or read project file contents.

`local_scan_complete` describes only the bounded local scan. `unmatched_repositories` names accessible repositories without a matched local workspace; missing roots, failed Git inventory and exhausted scan bounds are explicit coverage gaps. The paginated API is an observation interval, not an atomic snapshot. GitHub visibility cannot establish the inventory of repositories the credential cannot access. A zero exit means the configured local scan completed; it does not mean every organization repository exists locally, cleanup is implemented or the mission is complete. Exit 1 reports local gaps and exit 2 reports an invalid/unavailable organization inventory.

Credentials and raw origin URLs are not written to the report. Credential-bearing URLs cannot establish a match. Configure the GitHub credential through its normal credential store, never a command-line secret.

## Retirement remains a separate implementation gate

This first discovery increment performs no retirement. Automatic closeout requires creator workspace and owner lease generations, authenticated delivery/release, participating producer fencing, preservation checks, durable intent/recovery, creator retirement and branch disposition. Unknown or unsupported creators remain explicitly retained. The managed-workspace adapter must use its supported creator archive interface; it cannot fall back to raw Git removal.

The lifecycle belongs in Spec Kitty completion and startup recovery. A turn/session ending is an observation, not proof of mission completion or release. Existing production deployment remains on hold.

The report’s `observation_scope` names normalized configured roots and scan bounds. `local_scan_complete` applies only inside that scope. Known read/traversal failures appear in `coverage_gaps`; accessible repositories without a local match appear in `unmatched_repositories`. Repositories outside authenticated visibility and stores not discoverable through configured roots or their Git registrations remain explicitly unobservable. An empty error list never certifies the whole organization or cleanup eligibility.

## Private durable ledger

The source now provides `spec-kitty workspaces initialize`, `status` and `account`.
These commands operate only on an explicitly selected workspace ledger. They do
not open application data stores, start services or retire workspaces.

Initialize only an owner-admitted, existing empty private directory with
`workspaces initialize --state-dir /absolute/private/ledger`. Its owner and mode
must be the current user and `0700`. Existing contents refuse initialization.
Normal reads never recreate missing history. `workspaces status --state-dir ...`
reports recorded obligations and keeps workflow completion separate from cleanup.
It does not infer that a mission has completed.

`workspaces account --state-dir ... --root /absolute/root` performs a foreground
organization inventory and durably merges its bounded observations. Repeat
`--root` for additional roots. Known coverage gaps and unobservable scope remain
explicit. Missing entries in later/partial scans never erase prior obligations.
This foreground diagnostic is not the bounded automatic-event callback.

Registered creator accounting and retirement use the core protocol under the
creator's authenticated shared hold. Unbound discovery cannot assign a creator
generation. A confirmed retirement settles only that creator's bound generation;
unknown observations and replacement generations remain retained. Retirement is
terminal across event IDs and reuses its original receipt. Recovery receives the
exact retained intent, including source, release, delivery and evidence identity;
unknown effects are inspected rather than blindly retried. Historical observations
and operation receipts remain in the ledger.

Strict persistence requires supported descriptor-relative no-follow operations.
Unsupported platforms refuse admission. The caller owns first-directory creation
and durable parent admission. File/parent synchronization failure is not success;
results may remain unconfirmed. This ledger is private local bookkeeping, not a
substitute for authenticated creator release, producer fencing or proof of data
delivery. The original WP02 increment supplied the core only; the explicit
creator and completion/startup commands below now exercise real supported Git
retirement. Global runtime installation and organization adoption remain separate.

Status distinguishes all `unresolved_observations` from genuinely unbound
`unknown_observations`. Known retained work still prevents cleanup completion.
Checking an uninitialized directory refuses without creating ledger/lock files;
explicit initialization remains possible afterward.


## Managed production and automatic closeout

Use the source CLI's `workspaces managed-run` for one **new** creator-owned linked
checkout. It does not adopt an existing worktree or external managed workspace.
Initialize its private ledger first, then run:

```sh
spec-kitty workspaces managed-run --state-dir /absolute/private/ledger \
  --repo-root /absolute/repository --workspace /absolute/new-workspace \
  --branch feature/my-change --repository crucible-energy/example \
  --repository-id 123 -- my-producer its-arguments
```

The producer runs in the new checkout and receives
`SPEC_KITTY_LIFECYCLE_RESULT`, a creator-specific result-file path outside it.
After allocating its PR, the producer writes exactly `{"pr": 123}` as an owned
regular **0600** file at that path. Alternatively, supply an already allocated
`--pr 123` to `managed-run`. The PR number is a delivery hint, never release
permission. Do not write credentials to this result. No shell interprets the
producer argument vector. This foreground profile has a 30-second maximum;
longer/detached/scheduled producers require their own supported ownership and
fencing integration, and are not inferred safe by a parent exiting.

The runner joins the owned producer, records owner release and durably enqueues a
wakeup. Cleanup runs asynchronously: the worker independently verifies the exact
repository, source branch/commit and merged PR against the repository's default
branch, then rechecks creator generation, shared hold, clean state, ignored data,
nested repositories and runtime ownership before guarded removal. Failed or
unconfirmed production remains unreleased. Unmerged work stays retained. Unknown
or unsupported managed creators never fall back to raw removal. Local and remote
branch outcomes are separate; this adapter leaves remote branches retained.

Inspect `workspaces status --state-dir /absolute/private/ledger` for recorded
obligations, `pending_wakeup` and `last_worker_observation`. A blocked creator
remains pending without starving eligible creators. A new event arriving during
a blocked pass is reconsidered; unchanged errors do not trigger a retry loop.
The source result does not certify global cleanup or workflow completion.

At an explicitly integrated startup/completion checkpoint, use
`workspaces resume --state-dir /absolute/private/ledger`. It queues a fresh scan
of registered creator records and starts the same worker. This recovers missed
callbacks or a CLI that exited after durable owner release. For foreground
inspection, `workspaces worker --state-dir /absolute/private/ledger` uses that
same path and exits 2 on blocked outcomes. Recovery inspects an uncertain saved
intent rather than blindly repeating its effect. Preserve private history and
original receipts; missing/corrupt records require explicit recovery.

Installing/trusting startup integration for all organization repos remains a
separate adoption gate. Existing unknown/backlog workspaces stay retained until
their actual creator supplies release, producer fencing and delivery evidence.


## Branch-first landing and bounded failure

Consolidate on an existing concrete feature/integration branch, then advance the
primary branch through its PR workflow. A symbolic alias, revision expression or
primary target is not an eligible local landing target. A newer main commit does
not authorize local primary consolidation.

Canonical branch and bookkeeping writes bind direct-ref identity while Git holds
its native prepared lock. A late alias swap aborts rather than escaping into
primary or replacing the alias. In the supported owned-process profile, inherited
deadlines reserve a bounded cleanup interval for Git's native lock and owned
hook descendants. A refusal is not delivery. Inspect retained outcomes and use
the supported recovery workflow; never remove a native lock to manufacture a
successful retry.
