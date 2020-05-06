"""
Unit tests for the main.py file
"""

import unittest
from pathlib import Path

import oyaml as yaml

from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from PySide2.QtTest import QTest

import chameleon.main

# from pathlib import Path
# TEST_FOLDER = Path("test")

app = QtWidgets.QApplication(["."])


class TestBuildQuery(unittest.TestCase):
    """
    Unittesting for Worker class comparing sample csv and code outputs.
    This test validates sql query and analysis outputs.
    """

    # def __init__(self):
    #     super().__init__()

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
        self.func = chameleon.main.Worker("name", self.files, False, None)

    def test_build_query_ungrouped(self):
        """
        Comparison of sql query used for ungrouped analysis.
        """
        # print(gold_sql)
        test_sql = self.func.build_query("name", self.files, False, True)
        # print(test_sql)
        self.assertEqual(test_sql, self.gold_sql)

    def test_execute_query_ungrouped(self):
        """
        Tests that querying an output without grouping gives expected results
        """
        test_output = (
            self.func.execute_query("name", self.files, False, True)
        ).data
        with open("test/test_ungrouped_q_output.yaml", "r") as file:
            gold_ungrouped_output = yaml.load(file)
        self.assertEqual(test_output, gold_ungrouped_output)

    def test_execute_query_grouped(self):
        """
        Tests that querying an output with grouping gives expected results
        """
        test_output = (
            self.func.execute_query("name", self.files, True, True)
        ).data
        with open("test/test_grouped_q_output.yaml", "r") as file:
            gold_grouped_output = yaml.load(file)
        self.assertEqual(test_output, gold_grouped_output)

    def test_highway_missing_ungrouped(self):
        """
        Test that omitting a highway tag in the inputs does not block analysis in ungrouped mode
        """
        files = {
            "old": "test/old_nohighway.csv",
            "new": "test/new_nohighway.csv",
            "output": "test/output",
        }
        test_output = (
            self.func.execute_query("name", files, False, False)
        ).data
        with open("test/test_ungrouped_q_output_nohighway.yaml", "r") as file:
            gold_ungrouped_output = yaml.load(file)
        self.assertEqual(test_output, gold_ungrouped_output)

    def test_highway_missing_grouped(self):
        """
        Test that omitting a highway tag in the inputs does not block analysis in grouped mode
        """
        files = {
            "old": "test/old_nohighway.csv",
            "new": "test/new_nohighway.csv",
            "output": "test/output",
        }
        test_output = (self.func.execute_query("name", files, True, False)).data
        with open("test/test_grouped_q_output_nohighway.yaml", "r") as file:
            gold_grouped_output = yaml.load(file)
        self.assertEqual(test_output, gold_grouped_output)

    def test_missing_tag_ungrouped(self):
        """
        Test that a missing tag gives a helpful error message in ungrouped mode
        """
        files = {
            "old": "test/old_noname.csv",
            "new": "test/new_noname.csv",
            "output": "test/output",
        }
        test_output = (
            self.func.execute_query("name", files, False, False)
        ).status
        self.assertEqual(test_output, "error")

    def test_missing_tag_grouped(self):
        """
        Test that a missing tag gives a helpful error message in grouped mode
        """
        files = {
            "old": "test/old_noname.csv",
            "new": "test/new_noname.csv",
            "output": "test/output",
        }
        test_output = (
            self.func.execute_query("name", files, True, False)
        ).status
        self.assertEqual(test_output, "error")

    # def test_write_file_ungrouped(self):
    #     """
    #     Comparison of sample and code csv outputs.
    #     """
    #     self.func.write_file(self.gold_sql, self.file_name, "name")
    #     with open(self.file_name, "r") as file:
    #         test_file = file.read()
    #     with open("test/test_name.csv", "r") as file:
    #         gold_file = file.read()
    #     self.assertMultiLineEqual(test_file, gold_file)

    def test_csv_output(self):
        pass

    def test_excel_output(self):
        pass

    def test_geojson_output(self):
        pass


class TestGUI(unittest.TestCase):
    """
    Unittest for MainApp class validating UI functionalities.
    This test verifies button function, user input values and backend
    UI display parameters for the application.
    """

    def setUp(self):
        """
        Definition of testing vars for TestGUI class.
        """
        self.mainapp = chameleon.main.MainApp()
        self.favorite_location = Path("test/test_favorites.yaml")
        self.mainapp.fav_btn_populate(self.favorite_location)

    def test_add_to_list(self):
        """
        Verifies 'Add' button function for search bar.
        """
        self.mainapp.searchBox.insert("highway")
        QTest.mouseClick(self.mainapp.searchButton, Qt.LeftButton)
        self.assertGreater(
            len(self.mainapp.listWidget.findItems("highway", Qt.MatchExactly)),
            0,
        )
        self.assertIsNot(self.mainapp.searchBox.text, True)

    def test_add_special_char_to_list(self):
        """
        Verifies 'Add' button function for user input with
        special characters.
        """
        self.mainapp.searchBox.insert("addr:housenumber")
        QTest.mouseClick(self.mainapp.searchButton, Qt.LeftButton)
        self.assertGreater(
            len(
                self.mainapp.listWidget.findItems(
                    "addr:housenumber", Qt.MatchExactly
                )
            ),
            0,
        )

    def test_add_spaces_to_list(self):
        """
        Verifies space and empty values are ignored by
        the 'Add' function.
        """
        self.mainapp.listWidget.clear()
        self.mainapp.searchBox.insert("   ")
        QTest.mouseClick(self.mainapp.searchButton, Qt.LeftButton)
        self.assertEqual(self.mainapp.listWidget.count(), 0)

    def test_remove_from_list(self):
        """
        Verifies 'Delete' button function for QListWidget.
        """
        self.mainapp.listWidget.addItems(["name", "highway", "ref"])
        # nameitem = QtWidgets.QListWidgetItem("name")
        nameitems = self.mainapp.listWidget.findItems("name", Qt.MatchExactly)
        for i in nameitems:
            self.mainapp.listWidget.setCurrentItem(i)
            # self.mainapp.listWidget.setCurrentRow(0)
            # self.mainapp.listWidget.item(
            #     current_list.index("name")).setSelected(True)
            QTest.mouseClick(self.mainapp.deleteItemButton, Qt.LeftButton)
            # self.mainapp.delete_tag()
        self.assertEqual(
            len(self.mainapp.listWidget.findItems("name", Qt.MatchExactly)), 0
        )
        self.assertGreater(
            len(self.mainapp.listWidget.findItems("highway", Qt.MatchExactly)),
            0,
        )

    def test_clear_list_widget(self):
        """
        Verifies 'Clear' button function for wiping items
        in QListWidget.
        """
        self.mainapp.listWidget.addItems(
            [
                "name",
                "highway",
                "ref",
                "building",
                "addr:housenumber",
                "addr:street",
            ]
        )
        QTest.mouseClick(self.mainapp.clearListButton, Qt.LeftButton)
        self.assertEqual(self.mainapp.listWidget.count(), 0)

    def test_fav_btn_populate(self):
        """
        Verifies all favorite buttons are populated with
        the correct default and history values.
        """
        self.assertEqual(self.mainapp.popTag1.text(), "name")
        self.assertEqual(self.mainapp.popTag2.text(), "highway")
        self.assertEqual(self.mainapp.popTag3.text(), "addr:place")
        self.assertEqual(self.mainapp.popTag4.text(), "ref")
        self.assertEqual(self.mainapp.popTag5.text(), "addr:housenumber")

    def test_fav_btn_click(self):
        """
        Verifies favorite button function and reception
        of favorite values by the QListWidget.
        """
        self.assertEqual(self.mainapp.listWidget.count(), 0)
        self.assertEqual(self.mainapp.popTag1.text(), "name")
        print("Clicking fav button 1")
        QTest.mouseClick(self.mainapp.popTag1, Qt.LeftButton)
        self.assertGreater(
            len(self.mainapp.listWidget.findItems("name", Qt.MatchExactly)), 0
        )

    def test_autocompleter(self):
        """
        Checks that autocompleter tags get loaded without raising an exception.
        """
        self.mainapp.auto_completer()

    # def test_expand_user(self):
    #     self.mainapp.newFileNameBox.insert('~/Desktop/')
    #     self.mainapp.newFileNameBox.clearFocus()
    #     self.assertEqual(self.newFileNameBox)

    def test_no_settings_files(self):
        """
        Test running chameleon without existing counter.yaml/settings.yaml
        """
        pass


# class TestFavBtns(unittest.TestCase):
#     def setUp(self):

#     def test_fav_btns(self):

if __name__ == "__main__":
    unittest.main()
