# Isolated RC7 owned-analysis qualification

This recipe builds a separate source-derived runtime from published
`spec-kitty-cli 4.0.0rc7`, sdist SHA-256
`91e98774b7a69a273f9146656482e1e2bddd274a2178dfc6ac9c1f3bcede0c80`.
It does not replace PATH, a shared environment or installed package files.

The patch admits only planning/analysis on `single_branch` and `lanes`, binds
the actual RC7 `next` currency callback to the existing canonical owned root,
routes both owned recording modes through the same canonical-policy dirty-input
guard, and makes report transactions check their own worktree's Git operations.
Implementation/finalization/merge topology restrictions are unchanged. General
status guards keep their shared-directory default. There are no borrowed
RC6 runtime files or hidden source dependency commits: the complete six-file
delta is `owned-analysis-rc7.patch`, applied without fuzz to the verified archive.

Provide a frozen dependency constraints file from a verified RC7 environment
and a **new** output directory. Preserve the exact constraints and build log:

```sh
sh tools/qualification/build-owned-analysis-rc7.sh "$OUTPUT" "$CONSTRAINTS"
OWNED_ANALYSIS_RC7_PYTHON="$OUTPUT/venv/bin/python" \
  uv run --frozen pytest -q tests/integration/test_owned_analysis_implementation_cli.py \
  -k source_derived_rc7
```

The result reports `4.0.0rc7+crucible.ownedanalysis.2`, an honest local identity.
Its receipts bind the published source, complete patch, constraints, resulting
project metadata, installed dependency versions and executable version. Also
retain the owning Git commit/tree and wheel/install output. Reusing an output
directory refuses; failed output stays recoverable for diagnosis. No cleanup
or runtime activation is automatic.

The test invokes this installed runtime's actual recorder and actual RC7
currency callback against linked Git checkouts. A primary merge marker must
survive; an immediately recorded report must be current and a changed
requirement must make it stale. The main integration tests separately cover
target-operation refusal and primary index/work preservation. Run both; an
older integration `next` is not evidence for the RC7 callback.

Actual project replay remains owner-coordinated and source-bound. This build is
not package-index publication, default-branch adoption, a mission approval,
Store access, or production admission. Retain failed and passing receipts and
close only the build owner's eligible resources after consumer handover.
