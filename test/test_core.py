"""
Unit tests for core.py file.
"""
import pickle
import unittest
from pathlib import Path

import pandas as pd

from chameleon.core import (
    ChameleonDataFrame,
    ChameleonDataFrameSet,
    separate_ids_by_feature_type,
    split_id,
)


class TestQuery(unittest.TestCase):
    def setUp(self):
        """
        Definition of testing vars for TestBuildQuery class.
        """
        self.maxDiff = None
        self.files = {
            "old": "test/old.csv",
            "new": "test/new.csv",
            "output": "test/output",
        }

        self.file_name = f"{self.files['output']}_name.csv"

        self.mode = "highway"

    def test_chameleon_dataframe_set(self):
        self.df_set = ChameleonDataFrameSet(
            self.files["old"], self.files["new"], use_api=False
        )

    def test_chameleon_dataframe_constructor_ungrouped(self):
        self.df = ChameleonDataFrame(
            self.df_set.source_data, mode=self.mode, grouping=False
        ).query_cdf()

    def test_chameleon_dataframe_constructor_grouped(self):
        pass

    def test_highway_missing_ungrouped(self):
        pass

    def test_highway_missing_grouped(self):
        pass

    def test_missing_tag_ungrouped(self):
        pass

    def test_missing_tag_grouped(self):
        pass

    def test_check_api(self):
        pass

    def test_add_cdf_to_set(self):
        self.df_set[self.mode] = self.df

    def test_separate_ids_by_feature_type(self):
        mixed = [
            "n1234567",
            "n8901234",
            "w5678901",
            "n23456789",
            "r0123456",
            "w7801234",
        ]
        gold = {
            "node": ["1234567", "8901234", "23456789"],
            "way": ["5678901", "7801234"],
        }
        self.assertEqual(separate_ids_by_feature_type(mixed), gold)

    def test_split_id(self):
        fid = "w1234567"
        gold = ("way", "1234567")
        self.assertEqual(gold, split_id(fid))
