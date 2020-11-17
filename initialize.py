#!/usr/bin/env python3

import platform
import subprocess
from pathlib import Path

try:
    from git import Repo
except ImportError:
    pass
else:
    repo = Repo()
    last_tag = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)[
        -1
    ].name
    with Path("resources/version.txt").open("w") as f:
        f.write(last_tag)
    print("version.txt written")

subprocess.check_call(
    ["pyside2-uic", "chameleon/qt/design.ui", "-o", "chameleon/qt/design.py"]
)
print("pyuic complete")

if platform.system().lower() == "darwin":
    specfile = "ChameleonMac.spec"
else:
    specfile = "ChameleonWinLinux.spec"
subprocess.check_call(["pyinstaller", specfile, "-y"])
print("pyinstaller completed")
