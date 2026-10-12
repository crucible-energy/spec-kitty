# Native Local Validation Research

Status: Source-grounded planning, October 12, 2026; executable qualification pending.

## Selection

Decision: Extract the existing router and module inventory into one local JSON authority, and migrate current consumers. `scripts/ci/gate_selection.py` presently parses `.github/workflows/ci-router.yml`; `local_gate_parity.py` delegates to that parser and previews HEAD-relative changes. It neither validates staged contents nor executes checks. Merely deleting YAML would break these consumers. Reject a separately maintained routing map.

## Native Process Reuse

Decision: Reuse the reviewed Temet Darwin process foundation at `7d99ede611abbbfbda4503471fa71b417a6ef177`, with provenance and separately tested streaming adaptation. Its actual source supports Darwin, captures bounded buffers, and refuses unsupported platforms. General validation and Linux/Windows ownership are additional qualification, not implied by the existing helper. A scoped Kaizen file inventory did not identify a qualified generic replacement; no claim about exhaustive ecosystem search is made.

## Qualification And Publication

Decision: Preserve existing validator commands and requirements while changing execution ownership. `ci-quality.yml` separately runs Ruff lint/format, wheel build, clean install, and lock checks. `release.yml` requires exact-revision qualification before packaging/publication; `docs-pages.yml` includes configuration probing, build, and deployment. Extract their actual command and platform contracts; do not replace release proof with a hook-only success or silently lose docs publication.

## Tool Identity And Diagnostics

Decision: Bind executable, launcher, and source alongside staged tree, specification, compiler, dependencies, and environment. Separate bounded display excerpts from retained raw diagnostic streams. A quota breach is an explicit refusal with produced logs preserved. These incorporate the independent owner's post-spec review without creating a new approval step.

## Dependencies And Review

No package installation, upgrade, or new registry dependency is chosen here. Reuse frozen existing dependencies and the installed Zig 0.16 toolchain after identity verification. If implementation discovers a dependency change, apply the owning supply-chain procedure and record adversarial findings before readiness. Independent plan review is requested from the existing workflow owner; no unperformed squad pass is claimed. Platform, budget, and publication proof remain pending implementation.
