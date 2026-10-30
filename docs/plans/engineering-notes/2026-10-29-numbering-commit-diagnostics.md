---
title: Numbering commit diagnostics
description: Preserve mandatory-hook refusal details during mission-number assignment.
doc_status: active
updated: 2026-10-29
---

# Numbering commit diagnostics

Mission-number assignment commits only the mission's `meta.json` in a detached
temporary checkout. Its normal mandatory hooks still run. When Git refuses that
commit, `CalledProcessError` retains stdout and stderr, but its ordinary message
does not display either stream. The consolidation traceback therefore hid the
formatter failure that stopped a useful integration.

The commit site now adds both captured streams as an exception note and re-raises
the original exception. Its type, return code, command and captured bytes remain
available to existing rollback and recovery. The commit arguments, path scope,
mandatory hooks, branch-advance boundary and temporary-checkout cleanup are
unchanged. No refusal is converted into success.

The native regression runs real Git and real hooks. It checks multiline Unicode
diagnostics in Rich's exception renderer, a hook that writes only to stdout
(which Git redirects into its stderr), unchanged staged and unstaged unrelated
work, ignored and untracked evidence, and the original failed-commit state. The
success control checks a meta-only commit, one actual hook invocation and an
idempotent second assignment without another commit hook.

The triggering Subsequent investigation used one separately authorized exact-blob
fixture. Under its captured current environment, the scratch checkout had no
local formatter dependencies, and `bun biome` tried to run `biome.json`. The
same hook passed with the project's supported `BIOME_BINARY` pointing to the
verified, existing read-only formatter. The original invocation's environment
was not recorded; the controlled fixture does not reconstruct it. The actual
owner subsequently qualified that provider in normal consolidation: numbering
passed, then a separate content-attribution guard refused and rolled back.

The attribution refusal remains an independent finish obligation. In particular,
the official release includes dependent-authorship protection from upstream
issue #5968 that is absent from the older integration base of this diagnostic
candidate. This narrow change neither disables that protection nor qualifies
this candidate as a replacement for the official consolidation runtime. Current
claim provenance, rewritten-dependency and canceled/removed-content checks must
be retained and qualified before any complete consolidation-runtime intake.
