"""
Unit tests for the main.py file
"""
from pathlib import Path

import oyaml as yaml
import pytest
from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from PySide2.QtTest import QTest
from PySide2.QtWidgets import QMessageBox

from chameleon import main, core

# TEST_FOLDER = Path("test")

app = QtWidgets.QApplication(["."])


@pytest.fixture
def worker_files():
    return {
        "old": Path("test/old.csv"),
        "new": Path("test/new.csv"),
        "output": Path("test/output"),
    }


@pytest.fixture
def worker(mainapp, worker_files):
    return main.Worker(mainapp)


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


@pytest.mark.parametrize("use_api", [True, False])
@pytest.mark.parametrize("file_format", ["csv", "geojson", "excel"])
def test_history_writer(
    worker, worker_files, use_api, file_format, monkeypatch, tmp_path
):
    worker.files = worker_files
    worker.use_api = use_api
    worker.format = file_format

    history_path = tmp_path / "history/history.yaml"
    # history_path = main.HISTORY_LOCATION
    tmp_path.mkdir(exist_ok=True, parents=True)
    monkeypatch.setattr(main, "HISTORY_LOCATION", history_path)
    gold_dict = {
        "use_api": use_api,
        "file_format": file_format,
        "old": worker_files["old"],
        "new": worker_files["new"],
        "output": worker_files["output"],
    }

    worker.history_writer()

    with history_path.open("r") as f:
        assert gold_dict == yaml.safe_load(f)


@pytest.mark.parametrize(
    "newfile,outcome",
    [("test/new_highdeletions.csv", False), ("test/new.csv", True)],
)
def test_high_deletions_checker(worker, newfile, outcome):
    # TODO Need to simulate click on confirmation dialog
    cdf_set = core.ChameleonDataFrameSet("test/old.csv", newfile)
    assert worker.high_deletions_checker(cdf_set) is outcome


# @pytest.mark.parametrize(
#     "role,returned", [(QMessageBox.YesRole, True), (QMessageBox.NoRole, False)]
# )
# def test_overwrite_confirm(mainapp, worker, worker_files, role, returned):
#     # TODO Need to simulate click on confirmation dialog
#     worker.overwrite_confirm(worker_files["output"])
#     messagebox = mainapp.activeModalWidget()
#     the_button = [
#         button
#         for button in messagebox.buttons()
#         if messagebox.buttonRole(button) == role
#     ][0]
#     QTest.mouseClick(the_button)
#     assert worker.response is returned


@pytest.mark.parametrize(
    "role,returned", [(QMessageBox.YesRole, True), (QMessageBox.NoRole, False)]
)
def test_overwrite_confirm(qtbot, mainapp, worker_files, role, returned):
    mainapp.show()
    qtbot.addWidget(mainapp)
    messagebox = mainapp.activeModalWidget()
    the_button = [
        button
        for button in messagebox.buttons()
        if messagebox.buttonRole(button) == role
    ][0]
    QTest.mouseClick(the_button)
    assert worker.response is returned


# def test_check_api_deletions(worker, cdf_set):
#     worker.check_api_deletions(cdf_set)
#     cdf_set.separate_special_dfs()
#     assert len(cdf_set["deleted"]["changeset_new"].isna) == 0


def test_csv_output(self):
    pass


def test_excel_output(self):
    pass


def test_geojson_output(self):
    pass


# GUI Tests


@pytest.fixture
def favorite_location():
    return Path("test/test_counter.yaml")


@pytest.fixture(params=[None, favorite_location])
def mainapp(monkeypatch, favorite_location, worker_files, tmp_path, request):
    if request.param is None:
        # Empty file
        monkeypatch.setattr(main, "COUNTER_LOCATION", tmp_path / "counter.yaml")
    else:
        monkeypatch.setattr(main, "COUNTER_LOCATION", favorite_location)
    app = main.MainApp()
    app.text_fields = worker_files
    return app


@pytest.mark.parametrize(
    "tag,count", [("highway", 1), ("addr:housenumber", 1), ("   ", 0)]
)
def test_add_to_list(tag, count, mainapp):
    """
    Verifies 'Add' button function for search bar.
    """
    mainapp.searchBox.insert(tag)
    QTest.mouseClick(mainapp.searchButton, Qt.LeftButton)
    assert len(mainapp.listWidget.findItems(tag, Qt.MatchExactly)) == count
    assert mainapp.searchBox.text is not True


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
    mainapp.newFileNameBox.selectAll()
    QTest.keyClicks(mainapp.newFileNameBox, "~/Desktop/")
    # mainapp.newFileNameBox.insert("~/Desktop/")
    QTest.mouseClick(mainapp.oldFileNameBox, Qt.LeftButton)
    assert mainapp.newFileNameBox.text() == str(Path.home() / "Desktop")


def test_no_settings_files(monkeypatch, tmp_path, worker_files):
    """
    Test running chameleon without existing counter.yaml/settings.yaml
    """
    history_path = tmp_path / "history.yaml"
    counter_path = tmp_path / "counter.yaml"
    monkeypatch.setattr(main, "HISTORY_LOCATION", history_path)
    monkeypatch.setattr(main, "COUNTER_LOCATION", counter_path)
    mainapp = main.MainApp()

    mainapp.text_fields = worker_files

    mainapp.run_query()

    # TODO Check if the query actually ran


@pytest.mark.parametrize(
    "path,returned",
    [
        (Path.home() / "Documents", Path.home() / "Documents"),
        (Path.home() / "Documents/test.txt", Path.home() / "Documents"),
    ],
)
def test_dirname(path, returned):
    assert main.dirname(path) == returned
