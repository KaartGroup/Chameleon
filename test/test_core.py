"""
Unit tests for core.py file.
"""
import pickle
import unittest
from pathlib import Path

import pandas as pd

from chameleon.core import ChameleonDataFrame, ChameleonDataFrameSet


class TestQuery(unittest.TestCase):
    def setUp(self):
        """
        Definition of testing vars for TestBuildQuery class.
        """
        self.maxDiff = None
        self.files = {
            'old': 'test/old.csv',
            'new': 'test/new.csv',
            'output': 'test/output'
        }

        self.file_name = f"{self.files['output']}_name.csv"

        self.mode = 'highway'

    def test_chameleon_dataframe_set(self):
        self.df_set = ChameleonDataFrameSet(
            self.files['old'], self.files['new'], use_api=False)

    def test_chameleon_dataframe_constructor_ungrouped(self):
        self.df = ChameleonDataFrame(self.df_set.source_data,
                                     mode=self.mode,
                                     grouping=False).query_cdf()

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

    def test_csv_output(self):
        pass

    def test_excel_output(self):
        pass

    def test_geojson_output(self):
        pass
