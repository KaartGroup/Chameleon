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
    last_tag = sorted(
        repo.tags, key=lambda t: t.commit.committed_datetime)[-1].name
    with Path('resources/version.txt').open('w') as f:
        f.write(last_tag)
    print("version.txt written")

subprocess.call(["pyuic5", "chameleon2/design.ui",
                 "-o", "chameleon2/design.py"])
print("pyuic complete")

if platform.system().lower() == "darwin":
    specfile = "Chameleon2Mac.spec"
else:
    specfile = "Chameleon2WinLinux.spec"
subprocess.call(["pyinstaller", specfile, "-y"])
print("pyinstaller completed")
