"""Conservative, read-only inspection. Never promises migration success."""
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

MAX_XML_BYTES = 4 * 1024 * 1024


def parse_xml(text, expected):
    if len(text.encode("utf-8")) > MAX_XML_BYTES:
        raise ValueError("XML exceeds the 4 MiB limit")
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError("DTD and entity declarations are not accepted")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML: {exc}") from exc
    if root.tag != expected:
        raise ValueError(f"Expected <{expected}> root, got <{root.tag}>")
    return root


def run_virsh(uri, command, *args):
    if command not in {"dumpxml", "capabilities", "domstate"}:
        raise ValueError("Only inspection commands are allowed")
    if not uri or uri.startswith("-") or any(a.startswith("-") for a in args):
        raise ValueError("URI and domain must not be empty options")
    try:
        result = subprocess.run(
            ["virsh", "--readonly", "--connect", uri, command, *args],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "LC_ALL": "C"}, stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("virsh is not installed; use offline XML files or install the libvirt client") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"virsh {command} exceeded 30 seconds") from exc
    if result.returncode:
        raise RuntimeError(f"virsh {command} failed: {result.stderr.strip()[:2000]}")
    return result.stdout.strip()


def collect(source, destination, domain):
    return {
        "domain_xml": run_virsh(source, "dumpxml", domain),
        "destination_capabilities": run_virsh(destination, "capabilities"),
        "state": run_virsh(source, "domstate", domain),
    }


def assess(domain_xml, destination_capabilities, state=None):
    domain = parse_xml(domain_xml, "domain")
    caps = parse_xml(destination_capabilities, "capabilities")
    findings = []

    def add(code, level, evidence, action):
        findings.append(dict(code=code, level=level, evidence=evidence, action=action))

    if domain.get("type") != "kvm":
        add("backend_unsupported", "block", f"Domain type: {domain.get('type')}", "This MVP supports KVM domains only.")
    if state is None:
        add("state_unverified", "review", "No runtime state supplied.", "Confirm the VM is running on the source.")
    elif state.strip() != "running":
        add("guest_not_running", "block", f"Source state: {state.strip()}", "Use a running VM for this live-migration check.")
    else:
        add("guest_running", "pass", "Source reports running.", "Recheck immediately before migration.")

    guest_type = domain.find("os/type")
    arch = guest_type.get("arch") if guest_type is not None else None
    machine = guest_type.get("machine") if guest_type is not None else None
    candidates = []
    if guest_type is not None and guest_type.text == "hvm":
        for guest in caps.findall("guest"):
            if guest.findtext("os_type") != "hvm":
                continue
            for entry in guest.findall("arch"):
                if entry.get("name") == arch and entry.find("domain[@type='kvm']") is not None:
                    candidates.append(entry)
    if not arch:
        add("arch_unverified", "review", "Guest architecture absent.", "Collect the active domain XML.")
    elif not candidates:
        add("arch_unsupported", "block", f"No KVM HVM guest capability for {arch}.", "Use a destination supporting this guest architecture and KVM.")
    else:
        add("arch_supported", "pass", f"Destination advertises KVM HVM {arch}.", "CPU feature compatibility still needs a separate check.")
        machines = set()
        for entry in candidates:
            nodes = entry.findall("domain[@type='kvm']/machine") or entry.findall("machine")
            for node in nodes:
                machines.update(v for v in (node.text, node.get("canonical")) if v)
        if not machine or not machines:
            add("machine_unverified", "review", "Guest machine or destination machine list absent.", "Inspect destination domcapabilities for the actual emulator.")
        elif machine not in machines:
            add("machine_unsupported", "block", f"Machine {machine!r} is not advertised for KVM.", "Install a compatible QEMU machine version on the destination.")
        else:
            add("machine_supported", "pass", f"Destination advertises {machine}.", "An alias match does not prove identical machine versions; check canonical versions.")

    cpu = domain.find("cpu")
    mode = cpu.get("mode", "custom") if cpu is not None else "unspecified"
    add("cpu_unverified", "review", f"Guest CPU mode: {mode}.", "Validate the active guest CPU against the destination hypervisor; names alone are insufficient.")
    add("memory_unverified", "review", f"Configured memory: {domain.findtext('memory', 'unknown')} (see domain XML for units).", "Check destination allocatable memory, overhead and concurrent allocations.")
    if domain.find("memoryBacking") is not None or domain.find("numatune") is not None or domain.find("cputune") is not None:
        add("memory_placement", "review", "Special memory backing or CPU/NUMA placement configured.", "Check hugepages, NUMA topology, pinning and destination capacity.")
    for index, disk in enumerate(domain.findall("devices/disk"), 1):
        source = disk.find("source")
        evidence = dict(source.attrib) if source is not None else {}
        if evidence:
            add("disk_unverified", "review", f"Disk {index}: type={disk.get('type')}, source={evidence}.", "Verify storage identity, permissions, backing chain and access; equal paths do not prove shared storage. Include attached ISO media.")
    for index, interface in enumerate(domain.findall("devices/interface"), 1):
        source = interface.find("source")
        add("network_unverified", "review", f"NIC {index}: type={interface.get('type')}, source={dict(source.attrib) if source is not None else {}}.", "Verify destination bridge/network, VLAN, MTU and guest reachability; equal names do not prove equal networks.")
    if domain.findall("devices/hostdev") or domain.findall("devices/interface[@type='hostdev']"):
        add("host_devices", "review", "Host device assignment detected.", "Require device-specific migration support; do not assume passthrough devices migrate.")
    if domain.find("os/loader") is not None or domain.find("os/nvram") is not None or domain.find("os[@firmware]") is not None:
        add("firmware_state", "review", "Firmware or NVRAM configured.", "Check destination firmware compatibility and NVRAM handling.")
    for tag in ("tpm", "filesystem", "redirdev", "shmem", "vsock"):
        if domain.find(f"devices/{tag}") is not None:
            add("device_state", "review", f"Device requiring additional validation: {tag}.", "Check migration support and any external state or host resources.")
    add("transport_unverified", "review", "Only management connectivity may have been inspected.", "Verify source-to-destination migration connectivity and encrypted data transport; qemu+ssh alone does not encrypt native migration data.")
    add("coverage_limit", "review", "This MVP checks advertised architecture/machine support and flags selected resources.", "Validate QEMU/libvirt versions, all device backends, secrets, security labels, storage locks and workload convergence in a staging migration.")
    return {
        "schema_version": 1,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "domain": domain.findtext("name", "unknown"),
        "status": "blocked" if any(f["level"] == "block" for f in findings) else "review_required",
        "findings": findings,
    }
