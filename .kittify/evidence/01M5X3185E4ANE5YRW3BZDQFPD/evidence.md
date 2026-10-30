{
  "at": "2026-10-26T22:11:28.006724+00:00",
  "source_commit": "e479a6ba12550be91716b263bf7b1393e5c395a2",
  "original_published_head": "628f943a058dd6553db998c13d36ebca0709895f",
  "findings": [
    {
      "root_cause": "Direct status submodule import",
      "fix": "Use existing public status facade, identical helper objects; no exemption."
    },
    {
      "root_cause": "Unnecessary public result record",
      "fix": "Private frozen result type; only consumed preview function remains public. No allowlist entry."
    }
  ],
  "validation": {
    "combined_receipt": "/private/tmp/pdb-mission-control-20261024/governance-recovery/owned-active-resume-corrected-r4-run/receipt.json",
    "owning": "1057passed/3skip/2warnings",
    "mandatory_fast": "2452passed/5skip/2warnings",
    "targeted_docs_architecture": "821passed",
    "late_contract": "4passed, full test_dead_symbol_allowlist_contract module",
    "other": "docs0errors19existingwarnings; canonical2filemypy;3512formatted;changedlint/lock/diff all pass",
    "joined": true,
    "original_failures_retained": true
  },
  "self_review": "Both fixes preserve canonical ownership comparison identity and preview fields. Constructor was never a needed public contract. No guards, dependency semantics, status event, workspace admission or authority changed. Independent original static review remains logic-only; these corrections additionally self-reviewed and validated with exact failed architecture modules.",
  "scope": "Source delivery only; no runtime adoption/PDB implementation/Store/model effects. HELD/v5 unchanged.",
  "cleanup_receipts": [
    "/private/tmp/pdb-mission-control-20261024/governance-recovery/terminal-private-bytecode-closeout-20261026-r7.json",
    "/private/tmp/pdb-mission-control-20261024/governance-recovery/terminal-private-bytecode-closeout-20261026-r8.json"
  ],
  "qualified_runtime_obligation": "No build attempted. Preserve selected runtime newer analysis, advance fence and migration guards; minimal additive AST port only after Source acceptance."
}
