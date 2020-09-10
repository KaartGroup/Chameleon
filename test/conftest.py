"""
Defines fixtures shared across test files
"""


from pathlib import Path

import pytest

from chameleon import core


@pytest.fixture
def files():
    files = {"old": Path("test/old.csv"), "new": Path("test/new.csv")}
    return files


@pytest.fixture
def cdf_set(files):
    return core.ChameleonDataFrameSet(**files, use_api=False)


@pytest.fixture
def cdf0(files):
    return core.ChameleonDataFrame()


@pytest.fixture
def cdf1(files):
    return core.ChameleonDataFrame(
        {
            "id": ["w624284243", "w212013924", "w182144320"],
            "url": [
                "http://localhost:8111/load_object?new_layer=true&objects=w624284243",
                "http://localhost:8111/load_object?new_layer=true&objects=w212013924",
                "http://localhost:8111/load_object?new_layer=true&objects=w182144320",
            ],
            "user": ["plamen", "plamen", "Admasawi"],
            "timestamp": ["2020-03-30", "2020-04-18", "2020-01-06"],
            "version": ["4", "9", "4"],
            "changeset": ["82808003", "83746481", "79265089"],
            "osmcha": [
                "https://osmcha.mapbox.com/changesets/82808003",
                "https://osmcha.mapbox.com/changesets/83746481",
                "https://osmcha.mapbox.com/changesets/79265089",
            ],
            "name": ["37", "Доростол", ""],
            "highway": ["secondary", "primary", "tertiary"],
            "old_ref": ["37", "2", "64"],
            "new_ref": ["", "", ""],
            "action": ["dropped", "dropped", "modified"],
        },
        mode="ref",
    )
