"""
Unit tests for the web.py file
"""
from pathlib import Path

import yaml
import pytest

from contextlib import nullcontext

from chameleon import core
from chameleon.flask import web

# TEST_FOLDER = Path("test")


@pytest.fixture
def client():
    web.app.testing = True
    return web.app.test_client()


@pytest.mark.parametrize("uuid", [("7bf45b97-e0b7-4b49-99e6-ac8abd7d76d1")])
def test_longtask_status(client, uuid):
    rv = client.get(f"/longtask_status/{uuid}")
    assert rv.mimetype == "text/event-stream"


@pytest.mark.parametrize(
    "newinput,result",
    [
        ("test/BLZ_HPR_2020_02_03.csv", True),
        ("test/BLZ_allroads_2020_02_27.csv", False),
    ],
)
def test_high_deletions_checker(newinput, result: bool):
    cdfs = core.ChameleonDataFrameSet(
        "test/BLZ_allroads_2020_02_03.csv", newinput
    )
    assert (web.high_deletions_checker(cdfs) > 20) is result


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
    output = ""
    client_uuid = ""
    high_deletions_ok = False
    modes = ["highway", "ref", "construction", "name"]
    # with highdeletions:
    with open(oldpath, "rb") as oldfile, open(newpath, "rb") as newfile:
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
    response, json,
):
    output = web.message_task_update(response)
    assert output == json
