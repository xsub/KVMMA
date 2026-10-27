"""Build a zipapp containing only the runtime package."""
from pathlib import Path
import shutil
import tempfile
import zipapp

root = Path(__file__).resolve().parents[1]
out = root / "dist" / "kvmma.pyz"
out.parent.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as directory:
    shutil.copytree(root / "kvm_preflight", Path(directory) / "kvm_preflight", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (Path(directory) / "__main__.py").write_text("from kvm_preflight.__main__ import main\nraise SystemExit(main())\n")
    zipapp.create_archive(directory, out, interpreter="/usr/bin/env python3")
print(out)
