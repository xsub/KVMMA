import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kvm_preflight.core import assess, collect, parse_xml, run_virsh

DOMAIN = '''<domain type="kvm"><name>demo</name><memory unit="MiB">1024</memory>
<os><type arch="x86_64" machine="pc-q35-9.0">hvm</type></os>
<cpu mode="host-passthrough"/><devices><disk type="file" device="disk">
<source file="/vm/demo.qcow2"/></disk><interface type="bridge">
<source bridge="br0"/></interface></devices></domain>'''
CAPS = '''<capabilities><host><cpu><arch>x86_64</arch></cpu></host>
<guest><os_type>hvm</os_type><arch name="x86_64"><domain type="kvm">
<machine canonical="pc-q35-9.0">q35</machine></domain></arch></guest></capabilities>'''


class AssessmentTests(unittest.TestCase):
    def report(self, domain=DOMAIN, caps=CAPS, state="running"):
        return assess(domain, caps, state)

    def codes(self, report, level=None):
        return {f["code"] for f in report["findings"] if level is None or f["level"] == level}

    def test_matching_machine_still_requires_review(self):
        result = self.report()
        self.assertEqual(result["status"], "review_required")
        self.assertIn("machine_supported", self.codes(result, "pass"))
        self.assertIn("cpu_unverified", self.codes(result, "review"))
        self.assertIn("disk_unverified", self.codes(result, "review"))

    def test_machine_missing_blocks(self):
        self.assertEqual(self.report(caps=CAPS.replace("pc-q35-9.0", "pc-q35-8.0"))["status"], "blocked")

    def test_architecture_mismatch_blocks(self):
        self.assertIn("arch_unsupported", self.codes(self.report(caps=CAPS.replace("x86_64", "aarch64")), "block"))

    def test_tcg_only_is_not_kvm_support(self):
        self.assertIn("arch_unsupported", self.codes(self.report(caps=CAPS.replace('type="kvm"', 'type="qemu"')), "block"))

    def test_machine_from_other_backend_does_not_count(self):
        caps = CAPS.replace('<domain type="kvm">', '<domain type="kvm"/><domain type="qemu">')
        self.assertIn("machine_unverified", self.codes(self.report(caps=caps), "review"))

    def test_hostdev_requires_review_not_blanket_impossibility(self):
        result = self.report(domain=DOMAIN.replace("<devices>", '<devices><hostdev type="pci"/>'))
        self.assertIn("host_devices", self.codes(result, "review"))

    def test_stopped_guest_blocks_live_migration(self):
        self.assertIn("guest_not_running", self.codes(self.report(state="shut off"), "block"))

    def test_unknown_state_is_not_pass(self):
        self.assertIn("state_unverified", self.codes(self.report(state=None), "review"))

    def test_missing_machine_is_unknown(self):
        self.assertIn("machine_unverified", self.codes(self.report(domain=DOMAIN.replace(' machine="pc-q35-9.0"', "")), "review"))

    def test_firmware_and_special_memory_require_review(self):
        domain = DOMAIN.replace("<devices>", '<memoryBacking><hugepages/></memoryBacking><devices>').replace("</os>", '<nvram>/vm/nvram</nvram></os>')
        self.assertTrue({"firmware_state", "memory_placement"} <= self.codes(self.report(domain=domain), "review"))

    def test_rejects_bad_or_wrong_xml(self):
        for xml in ["<domain>", "<capabilities/>", '<!DOCTYPE domain [<!ENTITY a "x">]><domain>&a;</domain>']:
            with self.subTest(xml=xml), self.assertRaises(ValueError):
                parse_xml(xml, "domain")

    def test_command_is_read_only_with_separate_arguments(self):
        with patch("subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "<domain/>", "")
            run_virsh("qemu+ssh://server/system", "dumpxml", "name; touch x")
        args, kwargs = run.call_args
        self.assertEqual(args[0][-1], "name; touch x")
        self.assertIn("--readonly", args[0])
        self.assertFalse(kwargs.get("shell", False))
        self.assertGreater(kwargs["timeout"], 0)

    def test_collect_has_no_mutating_calls(self):
        with patch("kvm_preflight.core.run_virsh", side_effect=[DOMAIN, CAPS, "running"]) as run:
            result = collect("source", "dest", "demo")
        self.assertEqual([c.args[1] for c in run.call_args_list], ["dumpxml", "capabilities", "domstate"])
        self.assertEqual(result["state"], "running")

    def test_command_failure_does_not_become_compatibility_result(self):
        with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1, "", "denied")):
            with self.assertRaises(RuntimeError):
                run_virsh("source", "capabilities")

    def test_zipapp_preserves_review_exit_status(self):
        subprocess.run([sys.executable, "scripts/build.py"], check=True, capture_output=True)
        result = subprocess.run([sys.executable, "dist/kvmma.pyz", "check", "--domain-xml", "examples/domain.xml", "--destination-capabilities", "examples/destination-capabilities.xml", "--json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "review_required")

    def test_cli_json_exit_status(self):
        with tempfile.TemporaryDirectory() as directory:
            domain, caps = Path(directory) / "vm.xml", Path(directory) / "caps.xml"
            domain.write_text(DOMAIN)
            caps.write_text(CAPS)
            result = subprocess.run([sys.executable, "-m", "kvm_preflight", "check", "--domain-xml", str(domain), "--destination-capabilities", str(caps), "--json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "review_required")


if __name__ == "__main__":
    unittest.main()
