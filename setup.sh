#!/usr/bin/env bash

./version_writer.py
pyuic5 chameleon2/design.ui -o chameleon2/design.py
pyinstaller Chameleon2.spec -y
