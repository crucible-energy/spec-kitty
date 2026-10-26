---
affected_files: []
cycle_number: 1
mission_slug: organization-workspace-lifecycle-01M5DRAR
reproduction_command:
reviewed_at: '2026-10-24T22:35:47Z'
reviewer_agent: reviewer-renata
wp_id: WP11
---

# WP11 independent review — changes required

Reviewer: Lynn coordinator, independent review of source candidate `5972077575ac50b0be48bb5d5e5a81ef914cbcea`.

P2: The recovery guard rejects a symlink at the objects root but misses nested object-store links. Two disposable real-Git cases—an externally linked pack directory and individually linked pack/index files—both retired their worktree. A local recovery ref does not keep separately owned linked pack storage in custody.

Required repair: refuse nested external object dependencies or prove separately retained custody. Add real directory, packed-file and loose-object regressions, preserve hard links that retain their own inode reference, and refreeze validation before independent re-review. Preserve the prior failed review and its exact source binding.

Authoritative external evidence: `/Users/sam/Documents/Codex/2026-10-15/i/work/lynn-host/lifecycle-wp11-independent-review-r1.json`; raw review log SHA-256 `d08371a2a6768a59f797aa144d1682d6bad5d34b56310c8b97b8cfbd615b023c`. Review fixtures were joined and removed by their owner; no live project resources were changed.
