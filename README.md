# KVM Migration Assistant (KVMMA)

A lightweight CLI for inspecting libvirt virtual machines, identifying live migration blockers, and reporting checks that need operator review.

## MVP

Read-only inspection of a KVM domain and destination host capabilities. Checks advertised KVM architecture and machine support and source runtime state; flags CPU, storage, networking, firmware and selected device dependencies for review. Emits text or JSON. It does not perform a migration or automatically repair configuration.

**There is no “ready” verdict in this release.** Passing an individual check is evidence for that check only. Offline input is operator-supplied; the live commands are sequential observations, not an atomic snapshot. Neither proves migration compatibility.

## Run locally

Requires Python 3.10+; no Python runtime dependencies. Tested locally with Python 3.14.6.

```sh
python3 -m kvm_preflight check --domain-xml examples/domain.xml --destination-capabilities examples/destination-capabilities.xml --state running
python3 -m kvm_preflight check --domain-xml examples/domain.xml --destination-capabilities examples/destination-capabilities.xml --json
```

Examples are synthetic fixtures, not measurements from real KVM hosts.

For live inspection, install your distribution's libvirt client (`virsh`) and configure noninteractive authentication and read-only libvirt permissions:

```sh
python3 -m kvm_preflight inspect --source qemu+ssh://source/system --destination qemu+ssh://destination/system --domain demo --json
```

Calls `virsh --readonly` for `dumpxml`, destination `capabilities`, and source `domstate`. Each command has a 30-second timeout. The tool does not disable SSH host verification. Domain names beginning with `-` are rejected; use a UUID for such domains. SSH aliases and credentials remain managed by the operator. Management access is not proof that the migration data path works or is encrypted.

Alternatively capture XML yourself with `virsh dumpxml VM` and `virsh capabilities` on the destination, then use `check`. Treat XML and reports as infrastructure information: paths and network names are included. XML input is limited to 4 MiB; DTD/entity declarations are rejected.

## Exit codes and output contract

| Code | Meaning |
| --- | --- |
| 1 | At least one blocker detected |
| 2 | Review required; also argparse usage errors |
| 3 | Collection, input or runtime error |

JSON includes `schema_version`, `status`, `domain`, `observed_at`, `input_mode`, and findings with stable `code`, `level`, `evidence`, `action` fields. Error reports contain `schema_version`, `status: error` and `error`. Usage errors use argparse's stderr format. There is no success/ready exit code in this MVP.

## Package and verify

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 dist/kvmma.pyz --help
```

The zipapp needs only Python 3.10+ on the target machine, plus `virsh` for live inspection. Copy it to a chosen Linux management machine and run `python3 kvmma.pyz inspect ...`. A pip installation is also declared in `pyproject.toml`, but has not been validated in this environment; the zipapp is the tested distribution.

## Acceptance on real hosts (pending)

Use disposable Linux KVM hosts and a test guest. Compare active domain XML and destination capabilities independently; confirm a known unsupported machine generates a blocker. For a supported configuration, expect `review_required`, then independently validate CPU, disk identity/backing chains, bridges/VLANs/MTU, destination capacity and migration transport. Perform a libvirt migration in the lab, monitor a guest service through the switchover, and confirm the guest remains healthy on the destination. Record software versions, migration output and observations in HANDOFF.md. Do not infer success from fixture tests.

## Sources and related work

Reviewed 2026-10-27:

- [libvirt migration](https://libvirt.org/migration.html): management and data paths, storage transfer and transport limitations.
- [virsh reference](https://libvirt.org/manpages/virsh.html): read-only connections and inspection commands.
- [Domain XML](https://libvirt.org/formatdomain.html): guest resources and configuration.
- [Original discussion material](https://kernel-internals.org/virtualization/live-migration/): motivation and migration mechanics.

Existing tools include virsh for orchestration, virt-manager for graphical administration and Proxmox for integrated clusters. KVMMA's narrow scope is an explainable preflight report for existing libvirt hosts. This initial workspace contained no prior code to integrate.

See [TODO.md](TODO.md) for deferred features and [HANDOFF.md](HANDOFF.md) for current evidence and next steps. A reusable validation skill is stored in `skills/kvm-migration-validation/SKILL.md`.

## Repository and license

Canonical repository: https://github.com/xsub/KVMMA. Licensed under the [BSD 3-Clause License](LICENSE).
