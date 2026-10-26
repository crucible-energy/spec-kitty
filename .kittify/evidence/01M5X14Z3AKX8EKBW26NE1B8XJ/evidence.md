{
  "at": "2026-10-26T21:42:06.418696+00:00",
  "source_commit": "b220ccb86439c0991ea21c79f7460d6d7e85c492",
  "product_files": {
    "src/runtime/next/discovery.py": "bfd0c0e54c795179883f9bb633ff5117e6468294ea2888e5cc2f98cae0594114",
    "src/runtime/next/runtime_bridge.py": "652f5f711ed2a8bde2b132eb67c27e28ced611894552563b3e1678621cb08434",
    "src/runtime/next/runtime_bridge_decision_mapping.py": "aeb32f9669dfc69d93cee6caa4f3a3b3a0201d6cd3e268063c78659124a4d1ed",
    "src/runtime/next/runtime_bridge_query.py": "adecd9c939582f4d53020789979853b2d19797e7e6a9524b0bcc1e5911c988df",
    "tests/integration/test_owned_active_resume.py": "e9e880a1e344cd970ff2fc379034240c674682c8a700b2e89e50dd8808ee849f",
    "tests/next/test_next_claimable_payload.py": "278f16015de9c2415d39b24a980b5ebead0048561019a51ecff82bfdbdb473ca"
  },
  "owning": "1009passed/3skip/2warnings; original1007pass/3skip/2fail retained",
  "final": "2452pass/5skip baseline;821 targeted doc/architecture pass; docs0errors19existingwarnings; canonical2filemypy clean;3512formatted;changedlint/lock/diff pass",
  "independent_review": "/tmp/pdb-zitadel-full-qualification/issuer-recovery-atomicity/spec-owned-active-resume-r1-source-review.json",
  "review_scope": "All six code/test hashes exact. Final docs add retained failure/green accounting and finalized-board qualifier; changelog added; both pass targeted doc gates. No source semantic delta after review.",
  "self_review": "Canonical actor authority reused, no cache/status adoption or new claims; actual ctx.agent reaches every finalized and pre-persist selection path. No workspace constructor/guard change. Corrupt history refuses; original failed gate retained.",
  "scope": "Source-only selection, no installed runtime or PDB implementation/execution admission; HELD/v5 preserved."
}
