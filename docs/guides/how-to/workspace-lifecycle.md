# Organization workspace lifecycle

## Discovery and accounting

`spec-kitty doctor organization-workspaces --root /absolute/local/root` queries the accessible repositories in `crucible-energy` through the configured GitHub CLI credential with bounded pagination, then scans the explicitly supplied local roots and reads each matched store’s registered workspaces. Repeat `--root` for independent clones and other workspace locations. No initialized Spec Kitty project is needed. `--organization` selects a different organization; default scan bounds are depth 6, 10,000 directories and 100,000 directory entries.

The command emits JSON. Each observed workspace is retained with `ownership_unknown`; origin matching is discovery evidence, never owner release or cleanup permission. It includes primary checkouts, independent stores and worktrees outside the scan roots when their Git registry identifies them. No files, refs, Git configuration, ownership leases or workspaces are changed. It does not fetch remote refs or read project file contents.

`local_scan_complete` describes only the bounded local scan. `unmatched_repositories` names accessible repositories without a matched local workspace; missing roots, failed Git inventory and exhausted scan bounds are explicit coverage gaps. The paginated API is an observation interval, not an atomic snapshot. GitHub visibility cannot establish the inventory of repositories the credential cannot access. A zero exit means the configured local scan completed; it does not mean every organization repository exists locally, cleanup is implemented or the mission is complete. Exit 1 reports local gaps and exit 2 reports an invalid/unavailable organization inventory.

Credentials and raw origin URLs are not written to the report. Credential-bearing URLs cannot establish a match. Configure the GitHub credential through its normal credential store, never a command-line secret.

## Retirement remains a separate implementation gate

This first discovery increment performs no retirement. Automatic closeout requires creator workspace and owner lease generations, authenticated delivery/release, participating producer fencing, preservation checks, durable intent/recovery, creator retirement and branch disposition. Unknown or unsupported creators remain explicitly retained. The managed-workspace adapter must use its supported creator archive interface; it cannot fall back to raw Git removal.

The lifecycle belongs in Spec Kitty completion and startup recovery. A turn/session ending is an observation, not proof of mission completion or release. Existing production deployment remains on hold.
