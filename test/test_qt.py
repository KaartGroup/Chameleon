"""
Unit tests for the qt.py file
"""
from pathlib import Path

import yaml
import pytest
from PySide2.QtCore import Qt

from chameleon import core
from chameleon.qt import qt

# TEST_FOLDER = Path("test")


@pytest.fixture
def worker_files(tmp_path):
    return {
        "old": Path("test/old.csv"),
        "new": Path("test/new.csv"),
        "output": tmp_path / "output",
    }


@pytest.fixture
def worker(mainapp):
    return qt.Worker(mainapp)


@pytest.fixture
def favorite_location():
    return Path("test/test_counter.yaml")


@pytest.fixture
def mainapp(monkeypatch, favorite_location, qtbot, worker_files):
    monkeypatch.setattr(qt, "COUNTER_LOCATION", favorite_location)
    monkeypatch.setattr(qt.MainApp, "file_paths", worker_files)
    monkeypatch.setattr(
        qt.MainApp, "closeEvent", lambda *args: None
    )  # Disable the confirmation dialog while testing
    app = qt.MainApp()
    app.show()
    qtbot.addWidget(app)

    return app


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
    worker,
    worker_files,
    use_api,
    file_format,
    monkeypatch,
    tmp_path,
):
    worker.files = worker_files
    worker.use_api = use_api
    worker.format = file_format

    history_path = tmp_path / "history/history.yaml"
    # history_path = qt.HISTORY_LOCATION
    history_path.parent.mkdir(exist_ok=True, parents=True)
    monkeypatch.setattr(qt, "HISTORY_LOCATION", history_path)
    gold_dict = {"use_api": use_api, "file_format": file_format}
    gold_dict.update(worker_files)

    worker.history_writer()

    with history_path.open("r") as f:
        assert {
            k: (str(v) if isinstance(v, Path) else v)
            for k, v in gold_dict.items()
        } == yaml.safe_load(f)


@pytest.mark.parametrize(
    "newfile,highdeletions",
    [("test/new_highdeletions.csv", True), ("test/new.csv", False)],
)
@pytest.mark.parametrize("user_response", [True, False])
def test_high_deletions_checker(
    worker, newfile, highdeletions, user_response, monkeypatch
):
    def mock_confirm(message):
        return user_response

    monkeypatch.setattr(worker, "user_confirm", mock_confirm)

    cdf_set = core.ChameleonDataFrameSet("test/old.csv", newfile)
    assert worker.high_deletions_checker(cdf_set) == (
        highdeletions and not user_response
    )


@pytest.mark.parametrize("returned", [True, False])
def test_overwrite_confirm(worker, worker_files, returned, monkeypatch):
    monkeypatch.setattr(worker, "user_confirm", lambda *args: returned)

    assert worker.overwrite_confirm(worker_files["output"]) is returned


@pytest.mark.skip
def test_check_api_deletions(worker, cdf_set):
    worker.check_api_deletions(cdf_set)
    cdf_set.separate_special_dfs()
    assert len(cdf_set["deleted"]["changeset_new"].isna) == 0


def test_csv_output():
    pass


def test_excel_output():
    pass


def test_geojson_output():
    pass


# GUI Tests


@pytest.mark.skip
@pytest.mark.parametrize(
    "tag,count", [("highway", 1), ("addr:housenumber", 1), ("   ", 0)]
)
def test_add_to_list(mainapp, qtbot, tag, count):
    """
    Verifies 'Add' button function for search bar.
    """
    qtbot.mouseClick(mainapp.searchBox, Qt.LeftButton)
    mainapp.searchBox.insert(tag)
    qtbot.mouseClick(mainapp.searchButton, Qt.LeftButton)
    qtbot.wait(500)  # Waits until Qt has a chance to process the action

    assert len(mainapp.listWidget.findItems(tag, Qt.MatchExactly)) == count
    assert bool(mainapp.searchBox.text()) is not bool(count)


def test_remove_from_list(mainapp, qtbot):
    """
    Verifies 'Delete' button function for QListWidget.
    """
    mainapp.listWidget.addItems(["name", "highway", "ref"])
    nameitems = mainapp.listWidget.findItems("name", Qt.MatchExactly)
    for i in nameitems:
        mainapp.listWidget.setCurrentItem(i)
        qtbot.mouseClick(mainapp.deleteItemButton, Qt.LeftButton)

    assert len(mainapp.listWidget.findItems("name", Qt.MatchExactly)) == 0
    assert len(mainapp.listWidget.findItems("highway", Qt.MatchExactly)) > 0


def test_clear_list_widget(mainapp, qtbot):
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
    qtbot.mouseClick(mainapp.clearListButton, Qt.LeftButton)
    assert mainapp.modes_inclusive == {"new", "deleted"}
    assert not mainapp.modes


def test_fav_btn_populate(mainapp):
    """
    Verifies all favorite buttons are populated with
    the correct default and history values.
    """
    mainapp.fav_btn_populate()
    assert mainapp.popTag1.text() == "name"
    assert mainapp.popTag2.text() == "highway"
    assert mainapp.popTag3.text() == "addr:place"
    assert mainapp.popTag4.text() == "ref"
    assert mainapp.popTag5.text() == "addr:housenumber"


@pytest.mark.skip
def test_fav_btn_click(mainapp, qtbot):
    """
    Verifies favorite button function and reception
    of favorite values by the QListWidget.
    """
    mainapp.fav_btn_populate()
    qtbot.wait(500)
    assert mainapp.modes_inclusive == {"new", "deleted"}
    assert not mainapp.modes
    assert mainapp.popTag1.text() == "name"
    qtbot.mouseClick(mainapp.popTag1, Qt.LeftButton)
    qtbot.wait(500)

    assert mainapp.modes == {"name"}


def test_autocompleter(mainapp):
    """
    Checks that autocompleter tags get loaded without raising an exception.
    """
    mainapp.auto_completer()


def test_expand_user(mainapp, qtbot):
    qtbot.mouseClick(mainapp.newFileNameBox, Qt.LeftButton)
    mainapp.newFileNameBox.selectAll()
    qtbot.keyClicks(mainapp.newFileNameBox, "~/Desktop/")
    qtbot.mouseClick(mainapp.oldFileNameBox, Qt.LeftButton)
    assert mainapp.newFileNameBox.text() == str(Path.home() / "Desktop")


def test_no_settings_files(mainapp, monkeypatch, tmp_path, worker_files):
    """
    Test running chameleon without existing counter.yaml/settings.yaml
    """

    file_fields = worker_files
    history_path = tmp_path / "history.yaml"
    counter_path = tmp_path / "counter.yaml"
    monkeypatch.setattr(qt, "HISTORY_LOCATION", history_path)
    monkeypatch.setattr(qt, "COUNTER_LOCATION", counter_path)
    monkeypatch.setattr(mainapp, "file_fields", file_fields)

    mainapp.run_query()
    # TODO Check if the query actually ran


@pytest.mark.skip
@pytest.mark.parametrize(
    "modes,button_enabled",
    [([], True), (["highway"], True), (["ref", "oneway"], True)],
)
def test_run_checker(mainapp, qtbot, modes, button_enabled):
    for mode in modes:
        qtbot.mouseClick(mainapp.searchBox, Qt.LeftButton)
        mainapp.searchBox.insert(mode)
        qtbot.mouseClick(mainapp.searchButton, Qt.LeftButton)
        qtbot.wait(500)  # Waits until Qt has a chance to process the action

    assert mainapp.runButton.isEnabled() is button_enabled


@pytest.mark.skip
@pytest.mark.parametrize(
    "modes,button_enabled",
    [(("highway",), True), (("highway", "ref"), True)],
)
def test_run_checker_remove(mainapp, qtbot, modes, button_enabled):
    for tag in ("highway", "ref"):
        mainapp.listWidget.addItem(tag)
        qtbot.wait(500)
    for mode in modes:
        next(
            iter(mainapp.listWidget.findItems(mode, Qt.MatchExactly)),
            None,
        ).setSelected(True)
        mainapp.delete_tag()
        qtbot.wait(500)

    qtbot.wait(500)
    assert mainapp.runButton.isEnabled() is button_enabled


# @pytest.mark.parametrize(
#     "path,returned",
#     [
#         (Path.home() / "Documents", Path.home() / "Documents"),
#         (Path.home() / "Documents/test.txt", Path.home() / "Documents"),
#     ],
# )
# def test_dirname(path, returned):
#     assert qt.dirname(path) == returned
