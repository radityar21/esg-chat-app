#!/usr/bin/env python3
"""Builds build/agent.zip for AgentCore Runtime "direct code deployment" (no Docker needed).

The runtime is arm64 Linux, so dependencies are downloaded as aarch64 wheels even when this runs on Windows:

    python scripts/build_agent_zip.py            (from esg-reporting-poc/)

Layout of the zip (all at the root): app.py, orchestrator/, _shared/, and the installed dependencies.
Limits: 250 MB zipped, 750 MB unzipped. File modes are written as 644 (files) and 755 (directories), as AgentCore requires.
"""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PY = "3.12"  # must match the runtime value in infra/stacks/platform_stack.py (PYTHON_3_12)
ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
PKG = BUILD / "agent_pkg"
OUT = BUILD / "agent.zip"


SCRIPT = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
from {module} import {func}
if __name__ == "__main__":
    sys.argv[0] = re.sub(r"(-script\\.pyw|\\.exe)?$", "", sys.argv[0])
    sys.exit({func}())
"""


def write_console_scripts() -> None:
    """Rewrite bin/ from the packages' entry points so the scripts run on Linux arm64.

    pip writes host-specific launchers: .exe files on Windows, and on Linux a shebang that points at the build machine's
    Python. AgentCore starts the entry point (opentelemetry-instrument) from bin/, so it must be a portable Python script.
    """
    import configparser

    bindir = PKG / "bin"
    shutil.rmtree(bindir, ignore_errors=True)
    bindir.mkdir()
    n = 0
    for ep in PKG.glob("*.dist-info/entry_points.txt"):
        cp = configparser.ConfigParser(delimiters=("=",), interpolation=None)
        cp.optionxform = str
        cp.read(ep, encoding="utf-8")
        if not cp.has_section("console_scripts"):
            continue
        for name, target in cp.items("console_scripts"):
            target = target.split("[")[0].strip()
            module, _, func = target.partition(":")
            if not func or "." in func:
                continue
            (bindir / name).write_text(SCRIPT.format(module=module.strip(), func=func.strip()), encoding="utf-8", newline="\n")
            n += 1
    if not (bindir / "opentelemetry-instrument").exists():
        raise SystemExit("opentelemetry-instrument entry point not found: is aws-opentelemetry-distro in requirements.lock.txt?")
    print(f"wrote {n} portable console scripts")


def main() -> None:
    shutil.rmtree(PKG, ignore_errors=True)
    PKG.mkdir(parents=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--target", str(PKG), "--platform", "manylinux2014_aarch64",
                    "--implementation", "cp", "--python-version", PY, "--only-binary=:all:", "--upgrade", "--no-deps",
                    "-r", str(ROOT / "agentcore" / "requirements.lock.txt")], check=True)
    write_console_scripts()
    shutil.copy2(ROOT / "agentcore" / "app.py", PKG / "app.py")
    shutil.copytree(ROOT / "agentcore" / "orchestrator", PKG / "orchestrator", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (PKG / "_shared").mkdir()
    for f in (ROOT / "lambda" / "_shared").glob("*.py"):
        shutil.copy2(f, PKG / "_shared" / f.name)
    for junk in list(PKG.rglob("__pycache__")) + list(PKG.glob("*.dist-info/RECORD")):
        shutil.rmtree(junk, ignore_errors=True) if junk.is_dir() else None

    OUT.parent.mkdir(exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    total = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(PKG.rglob("*")):
            rel = p.relative_to(PKG).as_posix()
            if p.is_dir():
                info = zipfile.ZipInfo(rel + "/")
                info.external_attr = (0o40755 << 16) | 0x10
                info.create_system = 3
                z.writestr(info, "")
                continue
            info = zipfile.ZipInfo.from_file(p, rel)
            info.external_attr = ((0o100755 if rel.startswith('bin/') else 0o100644) << 16)
            info.create_system = 3  # Unix, so the mode bits above are honoured
            info.compress_type = zipfile.ZIP_DEFLATED
            total += p.stat().st_size
            z.writestr(info, p.read_bytes())
    mb = OUT.stat().st_size / 1e6
    print(f"{OUT}: {mb:.1f} MB zipped, {total / 1e6:.1f} MB unzipped")
    if mb > 250 or total / 1e6 > 750:
        raise SystemExit("package exceeds the AgentCore limits (250 MB zipped / 750 MB unzipped)")


if __name__ == "__main__":
    main()
