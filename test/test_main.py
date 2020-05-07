"""
Unit tests for the main.py file
"""
from pathlib import Path

import pandas as pd
import pytest
from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from PySide2.QtTest import QTest

from chameleon import main, core

# TEST_FOLDER = Path("test")

app = QtWidgets.QApplication(["."])


@pytest.fixture
def worker_files():
    return {
        "old": "test/old.csv",
        "new": "test/new.csv",
        "output": "test/output",
    }


@pytest.fixture
def worker(mainapp, worker_files):
    return main.Worker(mainapp, {"name"}, worker_files)


# Worker tests


def test_load_extra_columns(worker):
    gold_columns = {
        "resolution status": {
            "validate": "list",
            "source": [
                "Fixed",
                "Not an issue",
                "Unsure/Too hard - Leaving as is",
                "On Hold",
            ],
        },
        "editor notes": None,
        "QC status": {
            "validate": "list",
            "source": ["Validated", "Invalidated", "On Hold"],
        },
        "QCer": None,
        "QC notes": None,
        "reworked": {
            "validate": "list",
            "source": ["Addressed", "Disputed", "On Hold"],
        },
        "reworked notes": None,
    }
    loaded_columns = worker.load_extra_columns()
    assert gold_columns == loaded_columns


def test_history_writer():
    pass


@pytest.mark.parametrize(
    "newfile,outcome",
    [("test/new_highdeletions.csv", False), ("test/new.csv", True)],
)
def test_high_deletions_checker(worker, newfile, outcome):
    # TODO Need to simulate click on confirmation dialog
    cdf_set = core.ChameleonDataFrameSet("test/old.csv", newfile)
    assert worker.high_deletions_checker(cdf_set) is outcome


def test_overwrite_confirm():
    # TODO Need to simulate click on confirmation dialog
    pass


def test_check_api_deletions(worker, cdf_set):
    worker.check_api_deletions(cdf_set)
    cdf_set.separate_special_dfs()
    assert len(cdf_set["deleted"]["changeset_new"].isna) == 0


def test_csv_output(self):
    pass


def test_excel_output(self):
    pass


def test_geojson_output(self):
    pass


# GUI Tests


@pytest.fixture
def favorite_location():
    return Path("test/test_favorites.yaml")


@pytest.fixture
def mainapp(favorite_location):
    app = main.MainApp()
    return app


def test_add_to_list(mainapp):
    """
    Verifies 'Add' button function for search bar.
    """
    mainapp.searchBox.insert("highway")
    QTest.mouseClick(mainapp.searchButton, Qt.LeftButton)
    assert len(mainapp.listWidget.findItems("highway", Qt.MatchExactly)) > 0
    assert mainapp.searchBox.text is not True


def test_add_special_char_to_list(mainapp):
    """
    Verifies 'Add' button function for user input with
    special characters.
    """
    mainapp.searchBox.insert("addr:housenumber")
    QTest.mouseClick(mainapp.searchButton, Qt.LeftButton)
    assert (
        len(mainapp.listWidget.findItems("addr:housenumber", Qt.MatchExactly))
        > 0
    )


def test_add_spaces_to_list(mainapp):
    """
    Verifies space and empty values are ignored by
    the 'Add' function.
    """
    mainapp.listWidget.clear()
    mainapp.searchBox.insert("   ")
    QTest.mouseClick(mainapp.searchButton, Qt.LeftButton)
    assert mainapp.listWidget.count() == 0


def test_remove_from_list(mainapp):
    """
    Verifies 'Delete' button function for QListWidget.
    """
    mainapp.listWidget.addItems(["name", "highway", "ref"])
    nameitems = mainapp.listWidget.findItems("name", Qt.MatchExactly)
    for i in nameitems:
        mainapp.listWidget.setCurrentItem(i)
        QTest.mouseClick(mainapp.deleteItemButton, Qt.LeftButton)
    assert len(mainapp.listWidget.findItems("name", Qt.MatchExactly)) == 0
    assert len(mainapp.listWidget.findItems("highway", Qt.MatchExactly)) > 0


def test_clear_list_widget(mainapp):
    """
    Verifies 'Clear' button function for wiping items
    in QListWidget.
    """
    mainapp.listWidget.addItems(
        [
            "name",
            "highway",
            "ref",
            "building",
            "addr:housenumber",
            "addr:street",
        ]
    )
    QTest.mouseClick(mainapp.clearListButton, Qt.LeftButton)
    assert mainapp.listWidget.count() == 0


def test_fav_btn_populate(mainapp, favorite_location):
    """
    Verifies all favorite buttons are populated with
    the correct default and history values.
    """
    mainapp.fav_btn_populate(favorite_location)
    assert mainapp.popTag1.text() == "name"
    assert mainapp.popTag2.text() == "highway"
    assert mainapp.popTag3.text() == "addr:place"
    assert mainapp.popTag4.text() == "ref"
    assert mainapp.popTag5.text() == "addr:housenumber"


def test_fav_btn_click(mainapp):
    """
    Verifies favorite button function and reception
    of favorite values by the QListWidget.
    """
    assert mainapp.listWidget.count() == 0
    assert mainapp.popTag1.text() == "name"
    QTest.mouseClick(mainapp.popTag1, Qt.LeftButton)
    assert len(mainapp.listWidget.findItems("name", Qt.MatchExactly)) > 0


def test_autocompleter(mainapp):
    """
    Checks that autocompleter tags get loaded without raising an exception.
    """
    mainapp.auto_completer()


def test_expand_user(mainapp):
    mainapp.newFileNameBox.insert("~/Desktop/")
    mainapp.newFileNameBox.clearFocus()
    assert mainapp.newFileNameBox.text() == str(Path.home() / "Desktop")


def test_no_settings_files(mainapp):
    """
    Test running chameleon without existing counter.yaml/settings.yaml
    """
    pass
