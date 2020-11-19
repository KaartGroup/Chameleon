"""
Unit tests for core.py file.
"""
import json
from pathlib import Path

import pytest
from pandas.testing import assert_frame_equal

from chameleon.core import (
    ChameleonDataFrame,
    ChameleonDataFrameSet,
    pager,
    separate_ids_by_feature_type,
    split_id,
)


@pytest.mark.parametrize("mode", ["highway", "ref", "name"])
@pytest.mark.parametrize("grouping", [False, True])
def test_query_cdf(mode, grouping, cdf_set):
    cdf = ChameleonDataFrame(cdf_set.source_data, mode)
    cdf.query_cdf()


@pytest.mark.parametrize("mode", ["highway", "ref", "name"])
@pytest.mark.parametrize("grouping", [False, True])
def test_highway_missing(mode, grouping):
    cdf_set = ChameleonDataFrameSet(
        "test/old_nohighway.csv", "test/new_nohighway.csv"
    )
    # should not raise exception
    ChameleonDataFrame(cdf_set.source_data, mode=mode)


@pytest.mark.parametrize("mode", ["oneway:conditional"])
@pytest.mark.parametrize("grouping", [False, True])
def test_missing_tag(mode, grouping):
    cdf_set = ChameleonDataFrameSet("test/old.csv", "test/new.csv")
    cdf_set.separate_special_dfs()
    with pytest.raises(KeyError):
        ChameleonDataFrame(cdf_set.source_data, mode).query_cdf()


@pytest.mark.parametrize("mode", ["highway", "ref", "oneway:conditional"])
@pytest.mark.parametrize("grouping", [False, True])
def name_missing(mode, grouping):
    cdf_set = ChameleonDataFrameSet("test/old_noname.csv", "test/new_noname.csv")
    with pytest.raises(KeyError):
        ChameleonDataFrame(cdf_set.source_data, mode)


@pytest.mark.parametrize(
    "feature_id,gold_file,gold_dict",
    [
        (
            "w389652224",
            "test/way389652224.json",
            {
                "user_new": "schnelli",
                "changeset_new": "36375031",
                "timestamp_new": "2016-01-05T07:51:43Z",
                "version_new": "1",
                "action": "dropped",
            },
        ),
        (
            "w796424739",
            "test/way796424739.json",
            {
                "user_new": "wobness",
                "timestamp_new": "2020-05-07T15:40:29Z",
                "version_new": "2",
                "changeset_new": "84841207",
            },
        ),
    ],
)
def test_check_api(feature_id, gold_file, gold_dict, files, requests_mock):
    ftype, fid = split_id(feature_id)
    gold_file = Path(f"test/{ftype}{fid}.json")
    with gold_file.open("r") as f:
        gold_json = json.load(f)
    cdfs = ChameleonDataFrameSet(files["old"], files["new"], use_api=True)
    requests_mock.get(
        f"https://www.openstreetmap.org/api/0.6/{ftype}/{fid}/history.json",
        json=gold_json,
    )
    element_attribs = cdfs.check_feature_on_api(feature_id)
    assert gold_dict == element_attribs


@pytest.mark.parametrize("mode", ["highway"])
def test_add_cdf_to_set(mode, cdf_set):
    cdf = ChameleonDataFrame(cdf_set.source_data, mode=mode).query_cdf()
    cdf_set.add(cdf)
    assert_frame_equal(cdf_set[cdf.chameleon_mode], cdf)


@pytest.mark.parametrize(
    "mixed,gold",
    [
        (
            [
                "n1234567",
                "n8901234",
                "w5678901",
                "n23456789",
                "r0123456",
                "w7801234",
            ],
            {
                "node": ["1234567", "8901234", "23456789"],
                "way": ["5678901", "7801234"],
                "relation": ["0123456"],
            },
        )
    ],
)
def test_separate_ids_by_feature_type(mixed, gold):
    assert separate_ids_by_feature_type(mixed) == gold


@pytest.mark.parametrize(
    "fid,gold",
    [
        ("n1234567", ("node", "1234567")),
        ("w1234567", ("way", "1234567")),
        ("r1234567", ("relation", "1234567")),
        ("1234567", (None, "1234567")),
        (1234567, (None, "1234567")),
    ],
)
def test_split_id(fid, gold):
    assert gold == split_id(fid)


@pytest.mark.parametrize(
    "the_list,length,gold",
    [
        (
            ["n1234567", "n8901234", "w5678901", "n23456789", "r0123456",],
            2,
            [["n1234567", "n8901234"], ["w5678901", "n23456789"], ["r0123456"],],
        )
    ],
)
def test_pager(the_list, length, gold):
    assert pager(the_list, length) == gold
