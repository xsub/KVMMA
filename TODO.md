# Deferred work

## Required before claiming migration readiness

- [ ] Integration tests on real disposable KVM hosts; record independent outcomes.
- [ ] Validate the active expanded guest CPU against destination hypervisor capabilities.
- [ ] Verify destination memory availability and NUMA/hugepage constraints.
- [ ] Verify storage identity, backing chains, secrets, capacity, permissions and locks.
- [ ] Inspect actual destination networking and migration transport.
- [ ] Verify QEMU/libvirt compatibility, firmware, NVRAM and all device backends.
- [ ] Account for observation staleness and concurrent host changes.

## Nice to have

- [ ] Guided migration execution and explicit failure/recovery semantics.
- [ ] Browser/desktop GUI consuming the same report schema.
- [ ] Proposed storage/network mappings and operator-reviewed repairs.
- [ ] Duration/downtime estimates based on measured transfer and dirty-page rates.
- [ ] Batch evacuation and scheduling.
- [ ] Remote CI matrix for supported Python versions after GitHub is connected.
- [ ] Packaging smoke test for pip installation.
- [ ] Choose a project license before public distribution; no license choice inferred.
