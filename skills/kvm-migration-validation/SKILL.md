---
name: kvm-migration-validation
description: Validate changes to KVMMA preflight checks against raw libvirt XML and real-host migration evidence. Use for changes to collector behavior, compatibility findings or migration-readiness claims.
---

Start from active domain XML, destination capabilities and captured libvirt outcomes, rather than earlier summaries. Read README.md and HANDOFF.md in the KVMMA repository for the CLI contract and current validation evidence.

Keep three outcomes distinct: an advertised capability match, an observed blocker, and an unverified dependency. Never turn absent data into a pass. Match machine lists within the correct guest architecture and KVM backend. Identical disk paths and bridge names do not establish shared storage or equivalent networking. Host CPU model strings do not establish guest CPU compatibility.

For each compatibility change, add a realistic passing observation and a counterexample or unknown case to tests. Run `python3 -m unittest discover -s tests -v`. Exercise the built zipapp when changing CLI or packaging. Do not count mocked virsh calls as host integration tests.

When test hosts are available within the authorized scope, follow README's real-host acceptance procedure. Record versions, inputs, actual migration outcome and guest-service continuity separately from the report. Never perform migration solely because a report contains no blockers. Preserve unknowns for unsupported devices and stale observations.

Update HANDOFF.md with actual evidence, outstanding limitations and next steps. Avoid committing real host dumps, credentials or reports with private infrastructure details. Check current Git status before editing to preserve concurrent work.
