# Sampler Process Ownership Repair

## User Experience Findings

- On macOS, `/proc` does not provide process identity. The sampler now reports that limitation and refuses background startup, while foreground sampling fixtures remain usable.
- A stale PID could previously be signalled when `/proc` was unreadable, when the module name appeared only as a label, or when another sampler invocation owned a different output record. The stop command now requires the known launcher role, canonical argument sequence, and the same absolute output record.
- Diagnostic assertions once expanded ambient environment values. The repaired tests report only booleans and credential names; their evidence stays outside the training corpus.

## Engineering Decisions

- Unknown process identity fails closed. The procfs reader removes exactly one terminal NUL, rejects embedded empty arguments, and accepts only the launcher’s ten-field argv shape with a matching absolute output path. It does not emulate argparse aliases.
- The child environment removes the declared workflow and GitHub token names, including underscore-prefixed and case-varied spellings, before adding the designated child credential. Other environment settings remain available, so this is not universal secret filtering.
- The repair preserves the existing sampler and recapture components. It adds no process broker, service, or dependency.
- Both GX10s remain required Linux/ARM64 GB10 targets for training, evaluation, and serving qualification. Mac checks cover local tooling only. The Aletheia:35B base checkpoint and adapter mapping remain unresolved.

## Known Limitations

- Procfs PID identity has a reuse race and is not kernel-authenticated process ownership. This patch does not qualify the native supervisor or the full local validation gate.
- The Sam-owned Alpaca credential rotation is pending confirmation. Restricted originals and redacted diagnostic copies remain preserved outside source control and training inputs.
- No GX10 model training, paired model evaluation, adapter compatibility, Elastic Fog serving, or performance improvement is established by these changes.

## Validation

- Final sampler suite at `e6d7074e13cc5a0d61a7d29244470543f03aaf19`: 50 passed, 1 skipped, and 93.58% measured statement coverage. The test module loads the sampler by file path, so coverage explicitly targets that loaded module.
- Recapture and sampler component run: 164 passed, 1 skipped. The recapture statement coverage is 96.38%; sampler statement coverage was separately measured at 90.48% before the output-identity additions and 93.58% afterward.
- Ruff lint and formatting, strict mypy, codespell, and `git diff --check` passed on the final source candidate.
- Independent mocked controls cover unknown and unrelated processes, the same and different output records, parser aliases and overrides, changed working directories, procfs termination framing, and embedded empty arguments. No real process was signalled by these controls.
