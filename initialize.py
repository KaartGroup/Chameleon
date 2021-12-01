#!/usr/bin/env python3

import subprocess

try:
    from git import Repo
except ImportError:
    pass
else:
    repo = Repo()
    last_tag = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)[
        -1
    ].name
    with open("chameleon/resources/version.txt", "w") as f:
        f.write(last_tag)
    print("version.txt written")

subprocess.check_call(
    ["pyside6-uic", "chameleon/qt/design.ui", "-o", "chameleon/qt/design.py"]
)
subprocess.check_call(
    [
        "pyside6-uic",
        "chameleon/qt/filter_config.ui",
        "-o",
        "chameleon/qt/filter_config.py",
    ]
)
subprocess.check_call(
    [
        "pyside6-uic",
        "chameleon/qt/favorite_edit.ui",
        "-o",
        "chameleon/qt/favorite_edit.py",
    ]
)
print("pyuic complete")

subprocess.check_call(["pyinstaller", "Chameleon.spec", "-y"])
print("pyinstaller completed")
