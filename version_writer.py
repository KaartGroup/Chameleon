#!/usr/bin/env python3

from pathlib import Path

from git import Repo

repo = Repo()
last_tag = sorted(
    repo.tags, key=lambda t: t.commit.committed_datetime)[-1].name
with Path('chameleon2/version.txt').open('w') as f:
    f.write(last_tag)
