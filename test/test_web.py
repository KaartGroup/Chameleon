"""
Unit tests for the web.py file
"""
import os

import pytest

from chameleon import core
from chameleon.flask import web

# TEST_FOLDER = Path("test")

# Github Actions has some issues with home folders that we haven't yet resolved
# Tests that rely on a realistic home folder setup will be skipped
IS_GHA = bool(os.getenv("IS_GHA", 0))

# TODO Get these tests working with Github Actions


@pytest.fixture
def client():
    web.app.testing = True
    return web.app.test_client()


@pytest.mark.skipif(IS_GHA, reason="Not working with GHA yet")
@pytest.mark.parametrize("uuid", [("7bf45b97-e0b7-4b49-99e6-ac8abd7d76d1")])
def test_longtask_status(client, uuid):
    rv = client.get(f"/longtask_status/{uuid}")
    assert rv.mimetype == "text/event-stream"


@pytest.mark.parametrize(
    "country,startdate,enddate",
    [("SV", "2020-08-01", ""), ("SV", "2020-05-01", "2020-06-01")],
)
@pytest.mark.parametrize("file_format", ["excel", "geojson", "csv"])
@pytest.mark.parametrize("grouping", [True, False])
def test_result_overpass(
    client, country, startdate, enddate, file_format, grouping
):
    filter_list = []
    output = ""
    client_uuid = ""
    high_deletions_ok = False
    modes = ["highway", "ref", "construction", "name"]
    rv = client.post(
        "/result",
        data={
            "country": country,
            "startdate": startdate,
            "enddate": enddate,
            "modes": modes,
            "file_format": file_format,
            "filter_list": filter_list,
            "output": output,
            "client_uuid": client_uuid,
            "grouping": grouping,
            "high_deletions_ok": high_deletions_ok,
        },
    )
    assert rv.json["client_uuid"]
    assert rv.json["mode_count"] == len(modes)


@pytest.mark.parametrize(
    "newpath",
    ["test/BLZ_allroads_2020_02_27.csv", "test/BLZ_HPR_2020_02_03.csv"],
)
@pytest.mark.parametrize("file_format", ["excel", "geojson", "csv"])
@pytest.mark.parametrize("grouping", [True, False])
def test_result_byod(client, newpath, file_format, grouping):
    oldpath = "test/BLZ_allroads_2020_02_03.csv"
    filter_list = []
    modes = ["highway", "ref", "construction", "name"]
    # with highdeletions:
    with open(oldpath, "rb") as oldfile, open(newpath, "rb") as newfile:
        output = ""
        client_uuid = ""
        high_deletions_ok = False
        rv = client.post(
            "/result",
            data={
                "oldfile": oldfile,
                "newfile": newfile,
                "modes": modes,
                "file_format": file_format,
                "filter_list": filter_list,
                "output": output,
                "client_uuid": client_uuid,
                "grouping": grouping,
                "high_deletions_ok": high_deletions_ok,
            },
        )
    assert rv.json["client_uuid"]
    assert rv.json["mode_count"] == len(modes)


@pytest.mark.parametrize(
    "newinput,result",
    [
        ("test/BLZ_MTPST_2020_02_03.csv", True),
        ("test/BLZ_allroads_2020_02_27.csv", False),
    ],
)
def test_high_deletions_checker(newinput, result: bool):
    cdfs = core.ChameleonDataFrameSet(
        "test/BLZ_allroads_2020_02_03.csv", newinput
    )
    assert (web.high_deletions_checker(cdfs) > 20) is result


@pytest.mark.parametrize(
    "filter_list,goldfilter",
    [
        (
            ["highway=* (w)"],
            [{"types": ["way"], "key": "highway", "value": ""}],
        ),
        (
            ["highway=* (w)", "construction (nwr)"],
            [
                {"types": ["way"], "key": "highway", "value": ""},
                {"types": ["nwr"], "key": "construction", "value": ""},
            ],
        ),
        (
            ["highway (nwr)"],
            [{"types": ["nwr"], "key": "highway", "value": ""}],
        ),
        (
            ["highway=primary|secondary|tertiary (w)"],
            [
                {
                    "types": ["way"],
                    "key": "highway",
                    "value": ["primary", "secondary", "tertiary"],
                }
            ],
        ),
    ],
)
def test_filter_processing(filter_list, goldfilter):

    processed_filters = web.filter_processing(filter_list)
    assert processed_filters == goldfilter


@pytest.mark.parametrize(
    "response,json",
    [
        (
            {
                "mode_count": 4,
                "osm_api_max": 2,
                "current_phase": "osm_api",
                "osm_api_completed": 0,
                "state": "PROGRESS",
            },
            "event: task_update\ndata: "
            '{"mode_count": 4, "osm_api_max": 2, '
            '"current_phase": "osm_api", "osm_api_completed": 0, '
            '"state": "PROGRESS"}\n\n',
        )
    ],
)
def test_message_task_update(
    response,
    json,
):
    output = web.message_task_update(response)
    assert output == json
