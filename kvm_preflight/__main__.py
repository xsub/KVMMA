import argparse
import json
import sys
from pathlib import Path

from .core import MAX_XML_BYTES, assess, collect


def read_xml(path):
    with Path(path).open("rb") as stream:
        data = stream.read(MAX_XML_BYTES + 1)
    if len(data) > MAX_XML_BYTES:
        raise ValueError("XML exceeds the 4 MiB limit")
    return data.decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description="KVM Migration Assistant: read-only preflight inspection")
    commands = parser.add_subparsers(dest="command", required=True)
    offline = commands.add_parser("check", help="Inspect saved XML; does not contact hosts")
    offline.add_argument("--domain-xml", required=True)
    offline.add_argument("--destination-capabilities", required=True)
    offline.add_argument("--state", choices=["running", "paused", "shut off"], help="Operator-supplied state; not independently verified")
    live = commands.add_parser("inspect", help="Read active domain XML and destination capabilities using virsh")
    live.add_argument("--source", required=True, help="Source libvirt URI")
    live.add_argument("--destination", required=True, help="Destination libvirt URI")
    live.add_argument("--domain", required=True)
    for sub in (offline, live):
        sub.add_argument("--json", action="store_true", help="Emit a structured report")
    args = parser.parse_args()
    try:
        if args.command == "check":
            inputs = dict(domain_xml=read_xml(args.domain_xml), destination_capabilities=read_xml(args.destination_capabilities), state=args.state)
        else:
            inputs = collect(args.source, args.destination, args.domain)
        report = assess(**inputs)
        report["input_mode"] = "offline_operator_supplied" if args.command == "check" else "virsh_readonly"
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"{report['domain']}: {report['status']} ({report['input_mode']})")
            for item in report["findings"]:
                print(f"[{item['level'].upper()}] {item['code']}: {item['evidence']}")
                print(f"  Next: {item['action']}")
        return 1 if report["status"] == "blocked" else 2
    except (OSError, ValueError, RuntimeError) as exc:
        if args.json:
            print(json.dumps({"schema_version": 1, "status": "error", "error": str(exc)}))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
