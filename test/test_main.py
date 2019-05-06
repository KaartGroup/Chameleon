import unittest
import time

from pathlib import Path

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtTest import QTest

import src.main


# from pathlib import Path


# TEST_FOLDER = Path("test")

app = QtWidgets.QApplication(['.'])


class TestBuildQuery(unittest.TestCase):
    # def __init__(self):
    #     super().__init__()

    def setUp(self):
        self.maxDiff = None
        self.files = {
            "old": "test/old.csv",
            "new": "test/new.csv",
            "output": "test/output"
        }
        self.gold_sql = (
            "SELECT (substr(ifnull(new.\"@type\",old.\"@type\"),1,1) || ifnull(new.\"@id\",old.\"@id\")) AS id, "
            "('http://localhost:8111/load_object?new_layer=true&objects=' || substr(ifnull(new.\"@type\","
            "old.\"@type\"),1,1) || ifnull(new.\"@id\",old.\"@id\")) AS url, "
            "ifnull(new.\"@user\",old.\"@user\") AS user, substr(ifnull(new.\"@timestamp\","
            "old.\"@timestamp\"),1,10) AS timestamp, "
            "ifnull(new.\"@version\",old.\"@version\") AS version, "
            "ifnull(new.highway,old.highway) AS highway, "
            "ifnull(old.\"name\",'') AS old_name, ifnull(new.\"name\",'') AS new_name, "
            "CASE WHEN new.\"@id\" LIKE old.\"@id\" THEN \"modified\" ELSE \"deleted\" END \"action\" , "
            "NULL AS \"notes\" "
            f"FROM {self.files['old']} AS old LEFT OUTER JOIN {self.files['new']} AS new ON old.\"@id\" = new.\"@id\" "
            "WHERE old_name NOT LIKE new_name "
            "UNION ALL SELECT (substr(new.\"@type\",1,1) || new.\"@id\") AS id, "
            "('http://localhost:8111/load_object?new_layer=true&objects=' || substr(new.\"@type\",1,1) || new.\"@id\") AS url, "
            "new.\"@user\" AS user, substr(new.\"@timestamp\",1,10) AS timestamp, "
            "new.\"@version\" AS version, new.highway AS highway, "
            "ifnull(old.\"name\",'') AS old_name, ifnull(new.\"name\",'') AS new_name, "
            "\"new\" AS \"action\" , NULL AS \"notes\" "
            f"FROM {self.files['new']} AS new LEFT OUTER JOIN {self.files['old']} AS old ON new.\"@id\" = old.\"@id\" "
            "WHERE old.\"@id\" IS NULL AND length(ifnull(new_name,'')) > 0"
        )
        self.file_name = f"{self.files['output']}_name.csv"
        self.func = src.main.Worker("name", self.files, False)

    def test_build_query_ungrouped(self):
        # print(gold_sql)
        test_sql = self.func.build_query("name", self.files, False)
        # print(test_sql)
        self.assertEqual(test_sql, self.gold_sql)

    def test_write_file_ungrouped(self):
        self.func.write_file(self.gold_sql, self.file_name, "name")
        with open(self.file_name, "r") as f:
            test_file = f.read()
        with open("test/test_name.csv", "r") as f:
            gold_file = f.read()
        self.assertMultiLineEqual(test_file, gold_file)


class TestGUI(unittest.TestCase):
    def setUp(self):
        self.mainapp = src.main.MainApp()
        self.favorite_location = Path('test/test_favorites.yaml')
        self.fav_btn = [self.mainapp.popTag1, self.mainapp.popTag2,
                        self.mainapp.popTag3, self.mainapp.popTag4, self.mainapp.popTag5]
        self.mainapp.fav_btn_populate(self.favorite_location, self.fav_btn)

    def test_add_to_list(self):
        self.mainapp.searchBox.insert("highway")
        QTest.mouseClick(self.mainapp.searchButton, Qt.LeftButton)
        self.assertGreater(len(self.mainapp.listWidget.findItems(
            "highway", Qt.MatchExactly)), 0)

    def test_add_special_char_to_list(self):
        self.mainapp.searchBox.insert("addr:housenumber")
        QTest.mouseClick(self.mainapp.searchButton, Qt.LeftButton)
        self.assertGreater(len(self.mainapp.listWidget.findItems(
            "addr:housenumber", Qt.MatchExactly)), 0)

    def test_add_spaces_to_list(self):
        self.mainapp.listWidget.clear()
        self.mainapp.searchBox.insert("   ")
        QTest.mouseClick(self.mainapp.searchButton, Qt.LeftButton)
        self.assertEqual(self.mainapp.listWidget.count(), 0)

    def test_remove_from_list(self):
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
        self.assertEqual(len(self.mainapp.listWidget.findItems(
            "name", Qt.MatchExactly)), 0)
        self.assertGreater(
            len(self.mainapp.listWidget.findItems("highway", Qt.MatchExactly)), 0)

    def test_clear_list_widget(self):
        self.mainapp.listWidget.addItems(
            ["name", "highway", "ref", "building", "addr:housenumber", "addr:street"])
        QTest.mouseClick(self.mainapp.clearListButton, Qt.LeftButton)
        self.assertEqual(self.mainapp.listWidget.count(), 0)

    def test_fav_btn_populate(self):
        self.assertEqual(self.mainapp.popTag1.text(), "name")
        self.assertEqual(self.mainapp.popTag2.text(), "highway")
        self.assertEqual(self.mainapp.popTag3.text(), "addr:place")
        self.assertEqual(self.mainapp.popTag4.text(), "ref")
        self.assertEqual(self.mainapp.popTag5.text(), "addr:housenumber")

    def test_fav_btn_click(self):
        self.assertEqual(self.mainapp.listWidget.count(), 0)
        self.assertEqual(self.mainapp.popTag1.text(), "name")
        print("Clicking fav button 1")
        QTest.mouseClick(self.mainapp.popTag1, Qt.LeftButton)
        self.assertGreater(
            len(self.mainapp.listWidget.findItems("name", Qt.MatchExactly)), 0)


# class TestFavBtns(unittest.TestCase):
#     def setUp(self):

#     def test_fav_btns(self):

if __name__ == '__main__':
    unittest.main()
