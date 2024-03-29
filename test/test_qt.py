"""
Unit tests for the qt.py file
"""
import os
from pathlib import Path

import yaml
import pytest
from PySide6.QtCore import Qt

from chameleon import core
from chameleon.qt import qt

# TEST_FOLDER = Path("test")

# Github Actions has some issues with home folders that we haven't yet resolved
# Tests that rely on a realistic home folder setup will be skipped
IS_GHA = bool(os.getenv("IS_GHA", 0))


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
    worker, worker_files, use_api, file_format, monkeypatch, tmp_path
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

    def check_is_added():
        assert len(mainapp.listWidget.findItems(tag, Qt.MatchExactly)) == count
        assert bool(mainapp.searchBox.text()) is not bool(count)

    qtbot.waitUntil(check_is_added)


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


def test_fav_btn_click(mainapp, qtbot):
    """
    Verifies favorite button function and reception
    of favorite values by the QListWidget.
    """
    mainapp.fav_btn_populate()

    def check_empty():
        assert mainapp.modes_inclusive == {"new", "deleted"}
        assert not mainapp.modes
        assert mainapp.popTag1.text() == "name"

    qtbot.waitUntil(check_empty)

    qtbot.mouseClick(mainapp.popTag1, Qt.LeftButton)

    def check_has_name():
        assert mainapp.modes == {"name"}

    qtbot.waitUntil(check_has_name)


def test_autocompleter(mainapp):
    """
    Checks that autocompleter tags get loaded without raising an exception.
    """
    mainapp.auto_completer()


@pytest.mark.skipif(
    IS_GHA, reason="Cannot currently check home folder-related tests on GHA"
)
def test_expand_user(mainapp, qtbot):
    qtbot.mouseClick(mainapp.newFileNameBox, Qt.LeftButton)
    mainapp.newFileNameBox.selectAll()
    qtbot.keyClicks(mainapp.newFileNameBox, "~/Desktop/")
    qtbot.mouseClick(mainapp.oldFileNameBox, Qt.LeftButton)

    def check_expanded():
        assert mainapp.newFileNameBox.text() == str(Path.home() / "Desktop")

    qtbot.waitUntil(check_expanded)


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


@pytest.mark.parametrize(
    "modes,button_enabled",
    [([], True), (["highway"], True), (["ref", "oneway"], True)],
)
def test_run_checker(mainapp, qtbot, modes, button_enabled):
    for mode in modes:
        qtbot.mouseClick(mainapp.searchBox, Qt.LeftButton)
        mainapp.searchBox.insert(mode)
        qtbot.mouseClick(mainapp.searchButton, Qt.LeftButton)

    def check_is_enabled():
        assert mainapp.runButton.isEnabled() is button_enabled

    qtbot.waitUntil(check_is_enabled)


@pytest.mark.parametrize(
    "modes,button_enabled",
    [(("highway",), True), (("highway", "ref"), True)],
)
def test_run_checker_remove(mainapp, qtbot, modes, button_enabled):
    for tag in ("highway", "ref"):
        mainapp.listWidget.addItem(tag)
    for mode in modes:
        next(
            iter(mainapp.listWidget.findItems(mode, Qt.MatchExactly)),
            None,
        ).setSelected(True)
        mainapp.delete_tag()

    def check_is_enabled():
        assert mainapp.runButton.isEnabled() is button_enabled

    qtbot.waitUntil(check_is_enabled)


# Fails on GHA
@pytest.mark.skipif(
    IS_GHA, reason="Cannot currently check home folder-related tests on GHA"
)
@pytest.mark.parametrize(
    "path,returned",
    [
        (Path.home() / "Documents", Path.home() / "Documents"),
        (Path.home() / "Documents/test.txt", Path.home() / "Documents"),
    ],
)
def test_dirname(path, returned):
    assert qt.dirname(path) == returned


# Incomplete
@pytest.mark.skip
@pytest.mark.parametrize(
    "status_file",
    [
        "test/overpass_status/no_slots_waiting.txt",
        "test/overpass_status/one_slot_running.txt",
        "test/overpass_status/one_slot_waiting.txt",
        "test/overpass_status/two_slots_waiting.txt",
    ],
)
def test_too_many_requests(status_file, worker, requests_mock):
    mock_response = Path(status_file).read_text()
    requests_mock.post("//overpass-api.de/api/interpreter", status=429)
    requests_mock.get("//overpass-api.de/api/status", text=mock_response)


@pytest.mark.parametrize(
    "uinput,gold",
    [
        (None, {"all": {}}),
        ({}, {"all": {}}),
        ({"all": {}}, {"all": {}}),
        (
            {
                "user_whitelist": ["alpha", "bravo", "charlie"],
                "always_include": ["motorway"],
            },
            {
                "all": {
                    "user_whitelist": ["alpha", "bravo", "charlie"],
                    "always_include": ["motorway"],
                }
            },
        ),
    ],
)
def test_filter_process(uinput, gold):
    assert qt.filter_process(uinput) == gold
