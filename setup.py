#!/usr/bin/env python3

from pathlib import Path
from subprocess import Popen

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

Popen(["pyuic5", "chameleon2/design.ui", "-o", "chameleon2/design.py"])
Popen(["pyinstaller", "Chameleon2.spec", "-y"])
