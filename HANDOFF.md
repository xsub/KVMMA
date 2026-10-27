# Handoff — 2026-10-27

## Objective and scope

Build KVM Migration Assistant for existing libvirt hosts. User requested deeper evidence, narrow MVP, tests between iterations, branch isolation, TODOs and a reusable skill. User selected `/Users/pawel/_DEV/KVMMA` after work began in an empty LinuxWorld folder. All project files and the new Git repository were moved to the selected directory.

## Current state

Branch: `feat/migration-preflight`. CLI MVP implemented with offline XML and live read-only virsh collection. Text/JSON output. No mutation or migration execution. No ready/success verdict; unsupported advertised architecture/machine or non-running VM yields a blocker; unresolved checks require review.

Initial test run failed before implementation; 15 tests then passed on Python 3.14.6. Test data is synthetic. Source commands are tested via mocks; no libvirt client or KVM hosts available locally. The first zipapp smoke test caught an exit-code bug in the generated entry point; fixed with an explicit SystemExit wrapper and a regression test. All 16 tests now pass; zipapp help, offline assessment and missing-virsh handling were checked. No external deployment or real migration has been performed. No GitHub remote was provided at implementation time; user is creating one.

## Implementation map

- `kvm_preflight/core.py`: read-only collector and conservative assessment.
- `kvm_preflight/__main__.py`: CLI, input bounds, JSON/text reports and exit codes.
- `tests/test_preflight.py`: architecture/machine/backend separation, unknowns, host devices, firmware, malformed XML, command safety and CLI contract.
- `scripts/build.py`: zipapp build without third-party runtime dependencies.
- `skills/kvm-migration-validation/SKILL.md`: portable reusable validation procedure.
- `README.md`: operational instructions and primary sources.

## Continue

Read current Git status and file contents before editing: other workers may modify the checkout. Use a distinct branch/worktree for concurrent work; do not reset someone else's changes. Connect only the GitHub repository supplied by the user. Request test host URIs and VM identity to perform real-host validation. Use README acceptance procedure and record observations. Do not advertise deployment or readiness based on fixture tests. TODO.md distinguishes essential validation from optional features.

## Known limitations

Capabilities XML only proves advertised support. CPU compatibility is not established; aliases can resolve differently. Storage path equality and network-name equality prove neither resource identity nor connectivity. Sequential live reads can race state changes. The device review is not exhaustive, so a coverage finding is always emitted. XML parser rejects declarations and bounds offline file reads; virsh subprocess output is captured in memory. Reports expose infrastructure paths; do not commit real host dumps or credentials.

## Skill validation

The reusable skill was reviewed manually for frontmatter, scope and references. The bundled quick_validate.py could not run because PyYAML is absent from both available Python runtimes. No extra dependency was installed. The skill is stored in this repository and is not installed globally.
