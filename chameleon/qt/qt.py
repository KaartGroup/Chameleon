#!/usr/bin/env python3
"""
Opens a window with fields for input and selectors, which in turn opens
a worker object to process the input files with `q` and create output
in .csv format.
"""
import logging
import os
import shlex
import string
import sys
import time
from collections import Counter
from copy import deepcopy
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable, Mapping

import geojson
import overpass
import pandas as pd
import yaml

# Finds the right place to save config and log files on each OS
from appdirs import user_config_dir, user_log_dir
from bidict import bidict
from PySide6.QtCore import QEvent, QObject, Qt, QThread, Signal
from PySide6.QtGui import QAction, QIcon, QKeyEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCompleter,
    QDialog,
    QFileDialog,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QPushButton,
)
from requests import HTTPError, Timeout

# Import generated UI file
from chameleon.core import (
    HIGH_DELETIONS_THRESHOLD,
    OVERPASS_TIMEOUT,
    ChameleonDataFrame,
    ChameleonDataFrameSet,
    clean_for_presentation,
)
from chameleon.qt import design, favorite_edit, filter_config

# Differentiate sys settings between pre and post-bundling
RESOURCES_DIR = (
    Path(sys._MEIPASS)
    if getattr(
        sys, "frozen", False
    )  # Script is in a frozen package, i.e. PyInstaller
    else Path(__file__).parents[1]  # Script is not in a frozen package
    / "resources"
    # __file__.parent is chameleon, .parents[1] is chameleon
)

# Configuration file locations
CONFIG_DIR = Path(user_config_dir("Chameleon", "Kaart"))
HISTORY_LOCATION = CONFIG_DIR / "history.yaml"
FAVORITES_LOCATION = CONFIG_DIR / "favorites.yaml"
COUNTER_LOCATION = CONFIG_DIR / "counter.yaml"

logger = logging.getLogger()

try:
    with (RESOURCES_DIR / "version.txt").open("r") as version_file:
        APP_VERSION = version_file.read()
except OSError:
    APP_VERSION = ""
    logger.warning("No version number detected")


def logger_setup(log_dir: Path):
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    # Setup console logging output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    # Setup file logging output
    # Generate log file directory
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        logger.error("Cannot create log directory.")
    log_path = str(log_dir / f"Chameleon_{datetime.now().date()}.log")
    try:
        # Initialize Worker class logging
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        logger.error("Log file could not be generated at %s.", log_path)
    else:
        # Clean up log file if there are more than 15 (about 1MB)
        # Reading and sorting log file directory (ascending)
        log_list = sorted([f for f in log_dir.glob("*.log") if f.is_file()])
        if len(log_list) > 15:
            rm_count = len(log_list) - 15
            # Remove extra log files that exceed 15 records
            for f in log_list[:rm_count]:
                try:
                    logger.info("removing…%s", str(f))
                    f.unlink()
                except OSError as e:
                    logger.exception(e)


# Log file locations
logger_setup(Path(user_log_dir("Chameleon", "Kaart")))

# VSCode debugger helper
try:
    import ptvsd

    ptvsd.enable_attach()
except ImportError:
    logger.debug("PTVSD not imported")
else:
    logger.debug("VSCode debug library successful.")


class UserCancelledError(Exception):
    """
    Raised when the user hits the cancel button on a long operation
    """

    pass


class Favorite(yaml.YAMLObject):
    """
    Holds definitions of tags to be saved
    """

    yaml_tag = "!Favorite"
    yaml_loader = yaml.SafeLoader

    def __init__(
        self,
        tags: Iterable = [],
        title: str = None,
    ) -> None:
        super().__init__()
        self._tags = None

        self.title = title
        self.tags = tags

    def __repr__(self) -> str:
        if not self:
            return f"{self.__class__.__name__}()"
        return f"{self.__class__.__name__}(tags={self.tags:r},title={self.title:r or ''})"
        # if not self:
        #     return "%s()" % (self.__class__.__name__)
        # return "%s(tags={self._tags},title={self.title})" % (self.__class__.__name__, )

    def __bool__(self) -> bool:
        return bool(self._tags)

    def __nonzero__(self) -> bool:
        return self.__bool__()

    @property
    def tags(self) -> list[str]:
        return self._tags

    @tags.setter
    def tags(self, new_tags: Iterable) -> None:
        self._tags = [str(tag) for tag in new_tags if str(tag)]


class Worker(QObject):
    """

    Worker class, code inside slot should execute in a separate thread.
    Displays file paths, executes comparison function, writes and saves file.

    """

    done = Signal()
    mode_start = Signal(str)
    scale_with_api_items = Signal(int)
    increment_progbar_api = Signal()
    check_api_done = Signal()
    user_confirm_signal = Signal(str)
    dialog = Signal(str, str, str)
    overpass_counter = Signal(datetime, datetime, int, int)
    overpass_complete = Signal()

    def __init__(self, parent):
        super().__init__()
        # Define set of selected modes
        self.host = parent
        self.modes = parent.modes
        self.files = parent.file_paths
        self.group_output = parent.group_output
        self.use_api = parent.use_api
        self.format = parent.file_format
        self.response = None
        self.output_path = None
        self.config = parent.config_format

        self.error_list = []
        self.successful_items = {}

        self.write_output = {
            "csv": self.write_csv,
            "excel": self.write_excel,
            "geojson": self.write_geojson,
        }

    def run(self):
        """
        Runs when thread started, saves history to file and calls other functions to write files.
        """
        # For debugging in VSCode only
        try:
            ptvsd.debug_this_thread()
        except (ModuleNotFoundError, NameError):
            logger.debug("Worker thread not exposed to VSCode")
        else:
            logger.debug("Worker thread successfully exposed to debugger.")
        try:  # Global exception catcher
            # Saving paths to config for future loading
            # Make directory if it doesn't exist
            if not CONFIG_DIR.is_dir():
                try:
                    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                except FileExistsError:
                    logger.debug("Config directory already exists")
                except OSError:
                    logger.debug("Config directory could not be created.")
            if self.files:
                self.history_writer()
            cdf_set = ChameleonDataFrameSet(
                self.files["old"],
                self.files["new"],
                use_api=self.use_api,
                extra_columns=self.load_extra_columns(),
                config=self.config,
            )

            if self.high_deletions_checker(cdf_set):
                return

            if self.use_api:
                try:
                    self.check_api_deletions(cdf_set)
                except UserCancelledError:
                    # User cancelled the API check manually
                    return
                except RuntimeError:
                    # Rate-limited by server
                    return

            # Separate out the new and deleted dataframes
            cdf_set.separate_special_dfs()

            for mode in self.modes:
                logger.debug("Executing processing for %s.", mode)
                self.mode_start.emit(mode)
                try:
                    result = ChameleonDataFrame(
                        cdf_set.source_data,
                        mode=mode,
                        grouping=self.group_output,
                        config=self.config,
                    ).query_cdf()
                except KeyError as e:
                    # File reading failed, usually because a nonexistent column
                    logger.exception(e)
                    self.error_list.append(mode)
                    continue
                cdf_set.add(result)
            self.write_output[self.format](cdf_set)
        except Exception as e:
            self.dialog.emit(
                "An unhandled exception occurred", str(e), "critical"
            )
            logger.exception(e)
        else:
            self.dialog.emit(*self.summary_message())
        finally:
            try:
                if (
                    self.files["report"]
                    # and self.format != "excel"
                ):
                    self.write_report()
            except Exception:
                logger.exception()
            self.modes.clear()
            logger.info(list(self.successful_items.values()))
            # Signal the main thread that this thread is complete
            self.done.emit()

    def summary_message(self) -> tuple[str, str, str]:
        # If any modes aren't in either list,
        # the process was cancelled before they could be completed
        cancelled_list = self.modes - (
            set(self.error_list) | set(self.successful_items.keys())
        )
        dialog_icon = "information"
        if self.error_list:  # Some tags failed
            dialog_icon = "critical"
            headline = (
                "<p>A tag could not be queried</p>"
                if len(self.error_list) == 1
                else "<p>Tags could not be queried</p>"
            )
            summary = "\n".join(self.error_list)
            if self.successful_items:
                headline = "<p>Some tags could not be queried</p>"
                summary += "\nThe following tags completed successfully:\n"
                summary += "\n".join(self.successful_items.values())
        elif self.successful_items:  # Nothing failed, everything suceeded
            headline = "<p>Success!</p>"
            summary = "All tags completed!\n"
            summary += "\n".join(self.successful_items.values())
        # Nothing succeeded and nothing failed, probably because user declined to overwrite
        else:
            headline = "<p>Nothing saved</p>"
            summary = "No files saved"
        if cancelled_list:
            summary += "\nThe process was cancelled before the following tags completed:\n"
            summary += "\n".join(cancelled_list)
        if self.successful_items:
            s = "s" if self.format != "excel" else ""
            # We want to always show in the file explorer, so we'll always link to a directory
            headline += (
                f"<p>Output file{s} written to "
                f"<a href='{dirname(self.output_path).as_uri()}'>{self.output_path}</a></p>"
            )
        return (headline, summary, dialog_icon)

    @staticmethod
    def load_extra_columns() -> dict:
        try:
            with (RESOURCES_DIR / "extracolumns.yaml").open("r") as f:
                extra_columns = yaml.safe_load(f)
        except OSError:
            logger.info("No extra columns loaded.")
            extra_columns = {"notes": None}
        return extra_columns

    def history_writer(self) -> None:
        staged_history_dict = {k: str(v) for k, v in self.files.items() if v}
        staged_history_dict["use_api"] = self.use_api
        staged_history_dict["file_format"] = self.format
        try:
            with HISTORY_LOCATION.open("w") as history_file:
                yaml.dump(staged_history_dict, history_file)
        except OSError:
            logger.exception("Couldn't write history.yaml.")
        else:
            try:
                self.host.history_dict = staged_history_dict
            except NameError:
                # In some rare cases (like testing) MainApp may not exist
                pass

    def high_deletions_checker(self, cdf_set: ChameleonDataFrameSet) -> bool:
        """
        If more than 20% of features have been deleted,
        alerts the user and asks if they want to continue

        :return: True if more than 20% of features were deleted *and* user
                 chose to cancel
                 False if less than 20% of features were deleted *or*
                 more than 20% of features were deleted but
                 user chose to continue
        """
        deletion_percentage = (
            len(cdf_set.source_data[cdf_set.source_data["action"] == "deleted"])
            / len(cdf_set.source_data)
        ) * 100

        # The order matters here. user_confirm() waits for user input,
        # so we only want to evaluate it if the deletion_percentage is high
        return (
            deletion_percentage > HIGH_DELETIONS_THRESHOLD
            and not self.user_confirm(
                "There is an unusually high proportion of deletions "
                f"({round(deletion_percentage,2)}%). "
                "This often indicates that the two input files have different scope. "
                "Would you like to continue?"
            )
        )

    def overwrite_confirm(self, file_name: str) -> bool:
        return self.user_confirm(
            f"{file_name} exists. <p> Do you want to overwrite? </p>"
        )

    def user_confirm(self, message: str) -> bool:
        self.user_confirm_signal.emit(message)
        while self.response is None:  # Wait for user input
            time.sleep(0.1)
        response = self.response
        self.response = None
        return response

    def check_api_deletions(self, cdfs: ChameleonDataFrameSet) -> None:
        """
        Pings OSM server to see if ways were actually deleted or just dropped
        """
        # How long to wait between API calls
        REQUEST_INTERVAL = 0.1

        df = cdfs.source_data

        empty_count = 0
        deleted_ids = list(df.loc[df["action"] == "deleted"].index)
        self.scale_with_api_items.emit(len(deleted_ids))
        for feature_id in deleted_ids:
            from_cache = False
            # Ends the API check early if the user cancels it
            if self.thread().isInterruptionRequested():
                raise UserCancelledError
            self.increment_progbar_api.emit()

            try:
                element_attribs, from_cache = cdfs.check_feature_on_api(
                    feature_id, app_version=APP_VERSION
                )
            except (Timeout, ConnectionError) as e:
                # Couldn't contact the server, could be client-side
                logger.exception(e)
                if empty_count > 20:
                    break
                empty_count += 1
                continue
            except HTTPError as e:
                if str(e.response.status_code) == "429":
                    retry_after = e.response.headers.get("retry-after", "")
                    logger.error(
                        "The OSM server says you've made too many requests."
                        "You can retry after %s seconds.",
                        retry_after,
                    )
                    raise
                else:
                    logger.error(
                        "Server replied with a %s error", e.response.status_code
                    )
                element_attribs = {}

            df.update(pd.DataFrame(element_attribs, index=[feature_id]))

            if not from_cache:
                # Wait between iterations to avoid ratelimit problems
                time.sleep(REQUEST_INTERVAL)
        self.check_api_done.emit()

    def write_csv(self, dataframe_set: ChameleonDataFrameSet) -> None:
        """
        Writes all members of a ChameleonDataFrameSet to a set of CSV files
        """

        def to_csv(output_file: BytesIO, mode: str) -> None:
            result.to_csv(
                output_file, mode=mode, sep="\t", index=True, encoding="utf-8"
            )

        for result in dataframe_set:
            file_name = Path(
                f"{self.files['output']}_{result.chameleon_mode_cleaned}.csv"
            )
            logger.info("Writing %s", file_name)
            try:
                to_csv(file_name, "x")
            except FileExistsError:
                # Prompt and wait for confirmation before overwriting
                if not self.overwrite_confirm(file_name):
                    logger.info("Skipping %s.", result.chameleon_mode)
                    continue
                else:
                    to_csv(file_name, "w")
            except OSError:
                logger.exception("Write error.")
                self.error_list.append(result.chameleon_mode)
                continue

            self.successful_items.update(
                {result.chameleon_mode: success_message(result)}
            )
            logger.info(
                "Processing for %s complete. %s written.",
                result.chameleon_mode,
                file_name,
            )
        self.output_path = self.files["output"].parent

    def write_excel(self, dataframe_set: ChameleonDataFrameSet) -> None:
        """
        Writes all members of a ChameleonDataFrameSet as sheets in an Excel file
        """
        self.output_path = file_name = self.files["output"].with_suffix(".xlsx")
        if file_name.is_file() and not self.overwrite_confirm(file_name):
            logger.info("Not writing output")
            return

        dataframe_set.write_excel(file_name)

        self.successful_items.update(
            {
                result.chameleon_mode: success_message(result)
                for result in dataframe_set
            }
        )

    def write_geojson(self, dataframe_set: ChameleonDataFrameSet) -> None:
        """
        Writes all members of a ChameleonDataFrameSet to a geojson file,
        using the overpass API
        """

        overpass_query = dataframe_set.OverpassQuery(dataframe_set)

        logger.info("Querying Overpass…")
        try:
            for _ in overpass_query.get():
                self.overpass_counter.emit(
                    overpass_query.overpass_start_time,
                    overpass_query.overpass_timeout_time,
                    overpass_query.queries_completed,
                    overpass_query.number_of_queries,
                )
        except TimeoutError:
            logger.error("Overpass timeout")
            self.dialog.emit(
                "Overpass timeout",
                "The Overpass server did not respond in time.",
                "critical",
            )
            return
        except overpass.MultipleRequestsError:
            logger.error("Too many Overpass requests in a period of time")
            self.dialog.emit(
                "Too many Overpass requests",
                "The Overpass server is refusing "
                f"to accept any more queries for {overpass_query.time_remaining_fmt}.",
                "critical",
            )
            return
        finally:
            self.overpass_complete.emit()
        logger.info("All responses recieved from Overpass.")

        logger.info("Writing geojson…")
        file_name = self.files["output"].with_suffix(".geojson")

        try:
            with file_name.open("x") as output_file:
                geojson.dump(overpass_query.geojson, output_file, indent=4)
        except FileExistsError:
            if not self.overwrite_confirm(file_name):
                logger.info("User chose not to overwrite")
            else:
                fc = (
                    overpass_query.geojson
                )  # Assign this before opening the file
                with file_name.open("w") as output_file:
                    geojson.dump(fc, output_file, indent=4)
                self.successful_items.update(
                    {
                        result.chameleon_mode: success_message(result)
                        for result in dataframe_set.nondeleted
                    }
                )
                logger.info(
                    "Processing complete. %s written.",
                    file_name,
                )
        except OSError:
            logger.exception("Write error.")
            self.error_list += [
                result.chameleon_mode for result in dataframe_set.nondeleted
            ]
        else:
            self.successful_items.update(
                {
                    result.chameleon_mode: success_message(result)
                    for result in dataframe_set.nondeleted
                }
            )
            logger.info(
                "Processing complete. %s written.",
                file_name,
            )
        self.output_path = self.files["output"].parent

    def write_report(self) -> None:
        report_path: Path = self.files["report"]
        try:
            with report_path.open("x") as f:
                f.write(self.summary_message()[1])
        except FileExistsError:
            for letter in string.ascii_lowercase:
                alternate_path = report_path.with_stem(report_path.stem + letter)
                try:
                    with alternate_path.open("x") as f:
                        f.write(self.summary_message()[1])
                except FileExistsError:
                    continue
                else:
                    break
            else:
                raise FileExistsError


class MainApp(QMainWindow, QKeyEvent, design.Ui_MainWindow):
    """
    Main PySide window class that allows communication between UI and backend.
    Passes QMainWindow parameter to provide main application window, establish
    event handling with signal/slot connection.
    """

    clear_search_box = Signal()

    QMB_MAP = {QMessageBox.Yes: True, QMessageBox.No: False}
    EXTENSION_MAP = {
        "excel": ".xlsx",
        "geojson": ".geojson",
        "csv": r"_{mode}.csv",
    }

    def __init__(self, parent=None):
        """
        Loads history file path, establish event handling with signal/slot
        connection.
        """
        super().__init__()
        self.setupUi(self)
        # Enable QWidgets to capture and filter QKeyEvents
        self.searchButton.installEventFilter(self)
        self.listWidget.installEventFilter(self)
        self.progress_bar = None
        self.work_thread = None
        self.worker = None

        # Set up application logo on main window
        self.logo = str((RESOURCES_DIR / "chameleon.png").resolve())
        self.setWindowIcon(QIcon(self.logo))
        self.filter_menu = FilterDialog(self)
        self.favorite_edit = FavoriteEditDialog(self)
        self.actions_setup()

        self.tag_count = Counter()

        self.file_fields = bidict(
            {
                "old": self.oldFileNameBox,
                "new": self.newFileNameBox,
                "output": self.outputFileNameBox,
                "report": self.reportFileNameBox,
            }
        )

        # Logging initialization of Chameleon
        logger.info("Chameleon started at %s.", datetime.now())

        self.file_format_radio = bidict(
            {
                self.excelRadio: "excel",
                self.csvRadio: "csv",
                self.geojsonRadio: "geojson",
            }
        )
        # List all of our buttons to populate so we can iterate through them
        self.fav_btn = (
            self.popTag1,
            self.popTag2,
            self.popTag3,
            self.popTag4,
            self.popTag5,
        )

        self.favorites = []

        # YAML file loaders
        # Favorites saved in file
        self.load_favorites()
        # Load count of tags used
        self.load_tag_count()
        # Populate the buttons defined above
        self.fav_btn_populate()
        # Load file paths into boxes from previous session
        self.history_loader()
        # OSM tag resource file, construct list from file
        self.auto_completer()
        # Filters saved in file
        self.filter_load()

        # Connecting signals to slots within init
        self.oldFileSelectButton.clicked.connect(self.open_input_file)
        self.newFileSelectButton.clicked.connect(self.open_input_file)
        self.outputFileSelectButton.clicked.connect(self.output_file)
        self.reportFileSelectButton.clicked.connect(self.report_file)

        # Changes the displayed file name template depending on the selected file format
        for radio in self.file_format_radio:
            radio.clicked.connect(self.file_format_action)

        for btn in self.fav_btn:
            btn.clicked.connect(self.add_tag)

        self.fav_menu_setup()

        self.searchButton.clicked.connect(self.add_tag)
        self.deleteItemButton.clicked.connect(self.delete_tag)
        self.clearListButton.clicked.connect(self.clear_tag)
        self.runButton.clicked.connect(self.run_query)

        # Clears the search box after an item is selected from the autocomplete list
        # QueuedConnection is needed to make sure the events fire in the right order
        self.clear_search_box.connect(self.searchBox.clear, Qt.QueuedConnection)

        self.oldFileNameBox.editingFinished.connect(self.on_editing_finished)
        self.newFileNameBox.editingFinished.connect(self.on_editing_finished)
        self.outputFileNameBox.editingFinished.connect(self.on_editing_finished)

        # Define which button controls which filename box
        self.oldFileSelectButton.box_control = self.oldFileNameBox
        self.newFileSelectButton.box_control = self.newFileNameBox

        # Set the output name template
        # Set the default deleted item in the list
        self.file_format_action()
        # Sets run button to not enabled
        self.run_checker()

    def actions_setup(self) -> None:
        """
        Menu bar customization
        """
        # Define QActions for menu bar
        # About action for File menu
        info_action = QAction("&About Chameleon", self)
        info_action.setShortcut("Ctrl+I")
        info_action.setStatusTip("Software description.")
        info_action.triggered.connect(self.about_menu)
        # Exit action for File menu
        extract_action = QAction("&Exit Chameleon", self)
        extract_action.setShortcut("Ctrl+Q")
        extract_action.setStatusTip("Close application.")
        extract_action.triggered.connect(self.close)
        # Filter config
        config_action = QAction("&Configure filters", self)
        config_action.triggered.connect(self.config_menu)
        # Declare menu bar settings
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(info_action)
        file_menu.addAction(extract_action)
        file_menu.addAction(config_action)

    def edit_favorite(self) -> None:
        target = self.sender().data()

        self.favorite_edit.target = target
        self.favorite_edit.setup()
        self.favorite_edit.show()

    def save_favorite(self) -> None:
        """
        Save current tags as a favorite
        """
        sender = self.sender()
        fav_index = self.fav_btn.index(sender)
        self.favorites[fav_index].tags = self.modes

        if any(self.favorites):  # Don't create a file if everything is blank
            with FAVORITES_LOCATION.open("w") as f:
                yaml.dump(self.favorites, f)

    def load_favorites(self) -> None:
        """
        Load favorites from YAML file in preferences
        """
        try:
            with FAVORITES_LOCATION.open() as f:
                self.favorites = yaml.safe_load(f)
                # Make sure we loaded a list and it has at least one member
                self.favorites[0]
        except (OSError, yaml.YAMLError, IndexError):
            logger.warning("Couldn't load favorites file")
            self.favorites = [
                Favorite(),
                Favorite(),
                Favorite(),
                Favorite(),
                Favorite(),
            ]

    def about_menu(self) -> None:
        """
        Handles about page information.
        """
        logo = QPixmap(self.logo)

        formatted_version = (
            f"<p><center>Version {APP_VERSION}</center></p>"
            if APP_VERSION
            else ""
        )
        about = QMessageBox(self, textFormat=Qt.RichText)
        about.setWindowTitle("About Chameleon")
        about.setIconPixmap(
            logo.scaled(
                160,
                160,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        about.setText(
            f"<h2><center>Chameleon</center></h2>{formatted_version}"
            "<p>This application compares OSM snapshot data from "
            '<a href="https://overpass-turbo.eu/">Overpass Turbo</a> '
            "and returns an output of changes that occurred between the snapshots.</p>"
            '<p>Made by <a href="http://kaartgroup.com/">Kaart</a>\'s development team.<br>'
            'Licensed under <a href="https://choosealicense.com/licenses/gpl-3.0/">GPL3</a>.</p>'
        )
        about.setInformativeText(
            "<i>Powered by: "
            "<a href=https://www.qt.io/qt-for-python>Qt for Python</a>, "
            "<a href=https://pandas.pydata.org>pandas</a>, "
            "<a href=https://github.com/ActiveState/appdirs>appdir</a>, "
            "<a href=https://github.com/wimglenn/oyaml>oyaml</a>, "
            "and <a href=https://www.pyinstaller.org>PyInstaller</a>.</i>"
        )
        about.show()

    def config_menu(self) -> None:
        self.filter_menu.properties = self.config_format
        self.filter_menu.show()

    def auto_completer(self) -> None:
        """
        Autocompletion of user searches in searchBox.
        Utilizes resource file for associated autocomplete options.
        """

        # OSM tag resource file, construct list from file
        with (RESOURCES_DIR / "OSMtag.txt").open("r") as read_file:
            tags = read_file.read().splitlines()

        # Needs to have tags reference a resource file of OSM tags
        # Check current autocomplete list
        logger.debug("A total of %s tags was added to auto-complete.", len(tags))
        completer = QCompleter(tags)
        self.searchBox.setCompleter(completer)

    def file_format_action(self) -> None:
        self.suffix_updater()
        self.update_default_frames()
        self.run_checker()

    def history_loader(self) -> None:
        """
        Check for history file and load if exists
        """
        try:
            with HISTORY_LOCATION.open("r") as history_file:
                self.history_dict = yaml.safe_load(history_file)
        # If file doesn't exist, fail silently
        except FileNotFoundError:
            logger.warning(
                "History file could not be found. "
                "This is normal when running the program for the first time."
            )
            self.history_dict = {}
        except OSError:
            logger.exception("History file found but not readable.")
            self.history_dict = {}

        for label, field in self.file_fields.items():
            field.insert(self.history_dict.get(label, ""))
        self.offlineRadio.setChecked(not self.history_dict.get("use_api", True))
        self.file_format = self.history_dict.get("file_format", "csv")

    def fav_menu_setup(self) -> None:
        self.fav_btn_menus = bidict({})

        for btn, target in zip(self.fav_btn, self.favorites):
            fav_menu = QMenu()
            edit_action = QAction("&Edit", self)
            edit_action.setData(target)
            edit_action.triggered.connect(self.edit_favorite)
            save_action = QAction("&Save", self)
            save_action.triggered.connect(self.save_favorite)

            fav_menu.addAction(edit_action)
            fav_menu.addAction(save_action)

            self.fav_btn_menus[btn] = fav_menu

            btn.setMenu(self.fav_btn_menus[btn])

    def load_tag_count(self) -> None:
        # Holds the button values until they are inserted

        # Parse counter.yaml for user tag preference
        try:
            with COUNTER_LOCATION.open("r") as counter_read:
                self.tag_count = Counter(yaml.safe_load(counter_read))
        # If file doesn't exist, fail silently
        except FileNotFoundError:
            logger.warning(
                "Couldn't find the tag count file. "
                "This is normal if this is your first time runnning the application."
            )
        except OSError:
            logger.exception()
        else:
            logger.debug("counter.yaml history: %s.", (self.tag_count))

    def fav_btn_populate(self) -> None:
        """
        Populates the listed buttons with favorites from the given file
        """

        frequent_tags = sorted(
            self.tag_count, key=self.tag_count.get, reverse=True
        )
        # If we run out of favorites, start adding non-redundant default tags
        # We use these when there aren't enough favorites
        default_tags = (
            "highway",
            "name",
            "ref",
            "addr:housenumber",
            "addr:street",
        )
        # Add requisite number of non-redundant tags from the default list
        frequent_tags += [
            tag for tag in default_tags if tag not in frequent_tags
        ]
        # Loop through the buttons and apply our ordered tag values
        for btn, counter_text, favorite in zip(
            self.fav_btn, frequent_tags, self.favorites
        ):
            if favorite:
                if favorite.title:
                    btn.setText(favorite.title)
                else:
                    label = favorite.tags[0]
                    if len(favorite.tags) > 1:
                        label += f" + {len(favorite.tags) - 1} more"
                    btn.setText(label)
            else:
                btn.setText(counter_text)

    def add_tag(self) -> None:
        """
        Adds user defined tags into processing list on QListWidget.
        """
        tags_to_add = None
        # Identifies sender signal and grabs button text
        sender = self.sender()
        try:
            # Value was clicked from fav btn if this works without exception
            fav_btn_index = self.fav_btn.index(sender)
            if favorite := self.favorites[fav_btn_index]:
                tags_to_add = favorite.tags
            else:
                tags_to_add = [sender.text().strip()]
        except ValueError:
            # Value was typed by user
            # sender is self.searchButton
            raw_label = self.searchBox.text().strip()

            self.clear_search_box.emit()

            if not raw_label:  # Don't accept whitespace-only values
                logger.warning("No value entered.")
                return
            tags_to_add = tag_split(raw_label)

        self.listWidget.add_tags_to_list(tags_to_add)
        self.run_checker()

    def delete_tag(self) -> None:
        self.listWidget.delete_tag()
        self.run_checker()

    def clear_tag(self) -> None:
        self.listWidget.clear_tag()
        self.run_checker()

    def document_tag(
        self, run_tags: set, counter_location: Path = COUNTER_LOCATION
    ) -> None:
        """
        Python counter for tags that are frequently chosen by user.
        Document counter and favorites using yaml file storage.
        Function parses counter.yaml and dump into favorites.yaml.
        """

        # Combining history counter with new counter
        self.tag_count.update(run_tags)

        # Saving tag counts to config directory
        try:
            with counter_location.open("w") as counter_write:
                yaml.dump(dict(self.tag_count), counter_write)
        except OSError:
            logger.exception("Couldn't write counter file.")
        else:
            logger.info(f"counter.yaml dump with: {self.tag_count}.")

    def open_input_file(self) -> None:
        """
        Adds functionality to the Open Old/New File (…) button, opens the
        '/downloads' system path to find csv file.
        """
        destination = self.sender().box_control
        # Gets first non-empty value in order
        file_dir = next(
            (
                e
                for e in (
                    destination.text().strip(),
                    self.oldFileNameBox.text().strip(),
                    self.newFileNameBox.text().strip(),
                )
                if e
            ),
            str(Path.home() / "Downloads"),
        )
        shortname = self.file_fields.inverse[destination]
        file_name = QFileDialog.getOpenFileName(
            self,
            f"Select CSV file with {shortname} data",
            file_dir,
            "CSV (*.csv)",
        )[0]
        if file_name:  # Clear the box before adding the new path
            destination.selectAll()
            destination.insert(file_name)

    def output_file(self) -> None:
        """
        Adds functionality to the Output File (…) button, opens the
        '/documents' system path for user to name an output file.
        """
        # If no previous location, default to Documents folder
        output_file_dir = str(
            dirname(
                self.outputFileNameBox.text().strip()
                or Path.home() / "Documents"
            ),
        )
        output_file_name = QFileDialog.getSaveFileName(
            self, "Enter output file prefix", output_file_dir
        )[0]
        if output_file_name:  # Clear the box before adding the new path
            # Since this is a prefix, the user shouldn't be adding their own extension
            output_file_name = output_file_name.replace(".csv", "")
            self.outputFileNameBox.selectAll()
            self.outputFileNameBox.insert(output_file_name)

    def report_file(self) -> None:
        """
        Adds functionality to the Report File (…) button, opens the
        '/documents' system path for user to name an report file.
        """
        destination = self.reportFileNameBox
        file_dir = next(
            (
                e
                for e in (
                    destination.text().strip(),
                    self.outputFileNameBox.text().strip(),
                )
                if e
            ),
            str(Path.home() / "Documents"),
        )

        file_name = QFileDialog.getSaveFileName(
            self,
            "Enter report filename",
            file_dir,
            "TXT (*.txt)",
        )[0]
        if file_name:  # Clear the box before adding the new path
            destination.selectAll()
            destination.insert(file_name)

    def report_box_disabler(self) -> None:
        """
        Disables the Report File box if Excel output is selected,
        because the report will be a sheet in the workbook instead
        """
        widgets_tooltips = {
            self.reportFileSelectButton: "Set save location for report file.",
            self.reportFileNameBox: "",
        }
        excel_output = self.file_format == "excel"

        for widget, tooltip in widgets_tooltips.items():
            widget.setReadOnly(excel_output)
            widget.setToolTip(
                "Not used when Excel output is selected; "
                "report will be added as a sheet in the workbook instead"
                if excel_output
                else tooltip
            )
        self.update()

    def run_checker(self) -> None:
        """
        Function that enables run button if form is complete
        """
        self.runButton.setEnabled(
            all(self.file_paths_mandatory.values())
            and bool(self.modes_inclusive)
        )
        self.update()

    def suffix_updater(self) -> None:
        self.fileSuffix.setText(self.EXTENSION_MAP[self.file_format])
        self.update()

    def update_default_frames(self) -> None:
        """
        Hides special modes from the list widget if geojson format selected,
        or if explicitly excluded in config file, shows it otherwise
        """

        def add_special_item(name) -> None:
            item_to_add = QListWidgetItem(name)
            item_to_add.setFlags(Qt.NoItemFlags)
            self.listWidget.addItem(item_to_add)

        ignored_modes = self.config_format.get("ignored_modes", set())

        deleted_item = next(
            iter(self.listWidget.findItems("deleted", Qt.MatchExactly)),
            None,
        )
        if deleted_item and (
            self.file_format == "geojson" or "deleted" in ignored_modes
        ):
            self.listWidget.takeItem(self.listWidget.row(deleted_item))
        elif (
            self.file_format != "geojson"
            and not deleted_item
            and "deleted" not in ignored_modes
        ):
            add_special_item("deleted")

        new_item = next(
            iter(self.listWidget.findItems("new", Qt.MatchExactly)),
            None,
        )
        if new_item and "new" in ignored_modes:
            self.listWidget.takeItem(self.listWidget.row(new_item))
        elif not new_item and "new" not in ignored_modes:
            add_special_item("new")

        self.update()

    def on_editing_finished(self) -> None:
        """
        If user types a value into a file name box, expand user if applicable
        """
        sender = self.sender()
        text = sender.text().strip()
        expanded = str(Path(text).expanduser()) if text else ""
        sender.selectAll()
        sender.insert(expanded)
        self.run_checker()

    def dialog_display(
        self, text: str, info: str, icon: str = "information"
    ) -> None:
        """
        Method to pop-up critical error box

        Parameters
        ----------
        text, info : str
            Optional error box text.
        icon : str
            Which icon to use
        """
        dialog_box = QMessageBox(self)
        dialog_box.setText(text)
        dialog_box.setIcon(
            QMessageBox.Critical
            if icon == "critical"
            else QMessageBox.Information
        )
        dialog_box.setInformativeText(info)
        dialog_box.setTextFormat(Qt.RichText)
        dialog_box.exec()

    @property
    def file_paths(self) -> dict[str, Path | None]:
        # Wrap the file references in Path object to prepare "file not found" warning
        return {
            name: Path(stripped) if (stripped := field.text().strip()) else None
            for name, field in self.file_fields.items()
        }

    @property
    def file_paths_mandatory(self) -> dict[str, Path | None]:
        """
        Subset of file_paths that must be filled before chameleon can run
        """
        return {
            k: v
            for k, v in self.file_paths.items()
            if k in {"old", "new", "output"}
        }

    @property
    def use_api(self) -> bool:
        """
        Returns whether the user has selected to use the OSM API
        to check deleted features
        """
        # The offline radio button is a dummy. The online button functions as a checkbox
        # rather than as true radio buttons
        return self.onlineRadio.isChecked()

    @property
    def file_format(self) -> str:
        """
        Returns the selected file format
        """
        checked_radio = next(
            radio for radio in self.file_format_radio if radio.isChecked()
        )
        return self.file_format_radio[checked_radio]

    @file_format.setter
    def file_format(self, file_format) -> None:
        """
        Sets the file format radio to the given format
        """
        self.file_format_radio.inverse.get(
            file_format, self.csvRadio
        ).setChecked(True)

    @property
    def modes_inclusive(self) -> set:
        """
        Returns modes including the special "new" and "deleted" modes
        """
        return self.listWidget.modes_inclusive

    @property
    def modes(self) -> set:
        """
        Returns the modes the user has input as a set,
        ignoring the special "new" and "deleted" modes
        """
        return self.listWidget.modes

    @property
    def group_output(self) -> bool:
        """
        Returns True if the user has selected grouping
        """
        return self.groupingCheckBox.isChecked()

    @property
    def config_format(self) -> dict:
        """
        Returns the subset of config that applies to
        the currently-selected file format
        """
        return self.config.get("all", {}) | self.config.get(self.file_format, {})

    def validate_files(self) -> dict:
        """
        Validates the file paths the user has given
        """
        errors = {}
        # Check for blank values
        if name := next(
            (
                label
                for label, path in self.file_paths_mandatory.items()
                if not path
            ),
            None,
        ):
            errors["blank"] = f"{name} file field is blank."

        badfiles = []
        for key, path in ((k, self.file_paths.get(k)) for k in ["old", "new"]):
            try:
                with path.open("r"):
                    pass
            except OSError:
                badfiles.append(key)
        if badfiles:
            s = plur(len(badfiles))
            errors[
                "notfound"
            ] = f"{' and '.join(badfiles)} file{s} not found.".capitalize()

        # Check if output directory is writable
        if not os.access(self.file_paths["output"].parent, os.W_OK):
            errors["notwritable"] = (
                f"{self.file_paths['output'].parent} "
                "is not a writable directory"
            )
        return errors

    def filter_load(self) -> None:
        # Check for resource file in directory
        try:
            with (RESOURCES_DIR / "filter.yaml").open() as f:
                config = yaml.safe_load(f)
        except OSError:
            self.config = {}
            return

        # If keys are not sorted by file type, put them all under "all" key
        if set(config.keys()).isdisjoint({"all", "geojson", "csv", "excel"}):
            config["all"] = config

        new_config = config.copy()
        for file_format, file_format_config in config.items():
            new_config[file_format]["ignored_modes"] = set(
                file_format_config.get("ignored_modes") or []
            )

        self.config = filter_process(config)

    def run_query(self) -> None:
        """
        Allows run button to execute based on selected tag parameters.
        Also Enables/disables run button while executing function and allows
        progress bar functionality. Checks for file/directory validity and spacing.
        """

        if self.validate_files():
            errormessage = "\n".join(self.validate_files().values())
            self.dialog_display(
                "There are problems with your input!", errormessage, "critical"
            )
            return

        self.document_tag(self.modes)  # Execute favorite tracking

        logger.info(
            "Modes to be processed: %s.",
            self.modes_inclusive,
        )

        self.progress_bar = ChameleonProgressDialog(
            len(self.modes), self.file_format == "geojson"
        )
        self.progress_bar.show()

        # Handles Worker class and QThreads for Worker
        self.work_thread = QThread(parent=self)
        self.worker = Worker(self)
        # Connect to count_mode() when 1 mode begins in Worker
        self.worker.mode_start.connect(self.progress_bar.count_mode)
        self.worker.increment_progbar_api.connect(
            self.progress_bar.increment_progbar_api
        )
        self.worker.scale_with_api_items.connect(
            self.progress_bar.scale_with_api_items
        )
        self.progress_bar.canceled.connect(self.work_thread.requestInterruption)
        self.worker.check_api_done.connect(self.progress_bar.check_api_done)

        self.worker.overpass_counter.connect(self.progress_bar.overpass_counter)
        self.worker.overpass_complete.connect(
            self.progress_bar.overpass_complete
        )
        # Run finished() when all modes are done in Worker
        self.worker.done.connect(self.finished)
        # Connect signal from Worker to handle overwriting files
        self.worker.user_confirm_signal.connect(self.confirmation_dialog)
        self.worker.dialog.connect(self.dialog_display)

        self.worker.moveToThread(self.work_thread)
        self.work_thread.started.connect(self.worker.run)
        self.work_thread.start()

    def eventFilter(self, obj, event) -> bool:
        """
        Allows installed objects to filter QKeyEvents. Overrides the Qt default method.

        Parameters
        ----------
        obj : class
            Specific QWidget target

        event : class
            Event which handles keystroke input
        """
        if event.type() == QEvent.KeyPress:
            # Sets up filter to enable keyboard input in listWidget
            if obj == self.searchButton and event.key() == Qt.Key_Tab:
                if self.listWidget.count() > 0:
                    self.listWidget.item(0).setSelected(True)
                elif self.listWidget.count() == 0:
                    event.ignore()

            # Set up filter to enable delete key within listWidget
            if obj == self.listWidget and event.key() == Qt.Key_Delete:
                if self.listWidget.count() > 0:
                    self.delete_tag()
                elif self.listWidget.count() == 0:
                    event.ignore()

        return super(MainApp, self).eventFilter(obj, event)

    def finished(self) -> None:
        """
        Helper method finalizes run process: re-enable run button
        and notify user of run process completion.
        """
        # Quits work_thread and reset
        self.work_thread.quit()
        self.work_thread.wait()
        # In theory this deletes the worker only when done
        self.worker.deleteLater()
        self.progress_bar.close()
        logger.info("All Chameleon analysis processing completed.")
        # Re-enable run button when function complete
        self.run_checker()

    def confirmation_dialog(self, message: str) -> None:
        """
        Asks the user to confirm something.

        Parameters
        ----------
        message : str
            A question for the user to answer with yes or no.
        """
        confirm_response = QMessageBox.question(self, "", message)

        self.worker.response = self.QMB_MAP[confirm_response]

    def closeEvent(self, event) -> None:
        """
        Overrides the closeEvent method to allow an exit prompt.
        Checks if the user's input has changed from the saved value
        and confirms before exit if so

        Parameters
        ----------
        event : class
            Event which handles the exit prompt.
        """
        # Make a dict of text field values
        files = {name: field.text() for name, field in self.file_fields.items()}
        if not files.get("report"):
            files["report"] = None
        # Prompt if user has changed input values from what was loaded
        try:
            if {
                k: self.history_dict.get(k) for k in self.file_fields.keys()
            } != {k: files.get(k) for k in self.file_fields.keys()}:
                exit_prompt = QMessageBox()
                exit_prompt.setIcon(QMessageBox.Question)
                exit_response = exit_prompt.question(
                    self,
                    "",
                    "Discard field inputs?",
                    exit_prompt.Yes,
                    exit_prompt.No,
                )
                if exit_response == exit_prompt.Yes:
                    event.accept()
                else:
                    event.ignore()
        # Fail silently if history.yaml does not exist
        except AttributeError:
            logger.warning("All Chameleon analysis processing completed.")


class FavoriteEditDialog(QDialog, favorite_edit.Ui_favoriteEditor):
    def __init__(self, parent) -> None:
        super().__init__()
        self.setupUi(self)

        self.host = parent

        self.target = None

        self.addButton.clicked.connect(self.add_item)
        self.removeButton.clicked.connect(self.remove_item)
        self.clearButton.clicked.connect(self.clear_list)

        self.buttonBox.rejected.connect(self.close)
        self.buttonBox.accepted.connect(self.save_and_close)

    def setup(self) -> None:
        self.title = getattr(self.target, "title", None)
        self.tags = getattr(self.target, "tags", [])

    def add_item(self) -> None:
        """
        Add item to list
        """
        dest = self.tagsListWidget
        raw_label = self.tagLineEdit.text().strip()
        if not raw_label:  # Don't accept whitespace-only values
            logger.warning("No value entered.")
            return
        for count, label in enumerate(tag_split(raw_label)):
            label = clean_for_presentation(label)
            # Check if the label is in the list already
            existing_item = next(
                iter(dest.findItems(label, Qt.MatchExactly)),
                None,
            )
            if existing_item:
                # Clear the prior selection on the first iteration only
                if count == 0:
                    dest.selectionModel().clear()
                existing_item.setSelected(True)
                logger.warning("%s is already in the list.", label)
            else:
                dest.addItem(label)
                logger.info("Adding to list: %s", label)
        self.tagLineEdit.clear()
        # TODO Adapt from mainapp to filter dialog
        # self.clear_search_box.emit()

    def remove_item(self) -> None:
        dest = self.tagsListWidget
        for item in dest.selectedItems():
            dest.takeItem(dest.row(item))

    def clear_list(self) -> None:
        self.tagsListWidget.clear()

    @property
    def title(self) -> str:
        return self.titleLineEdit.text()

    @title.setter
    def title(self, new_title: str) -> None:
        self.titleLineEdit.clear()
        self.titleLineEdit.insert(new_title)

    @property
    def tags(self) -> list[str]:
        return tuple(
            tag.text()
            for tag in self.tagsListWidget.findItems("*", Qt.MatchWildcard)
        )

    @tags.setter
    def tags(self, new_tags: Iterable) -> None:
        self.clear_list()
        for tag in new_tags:
            self.tagsListWidget.addItem(tag)

    def save_and_close(self) -> None:
        self.target.title = self.title
        self.target.tags = self.tags
        if self.tags:
            with FAVORITES_LOCATION.open("w") as f:
                yaml.dump(self.host.favorites, f)
        elif FAVORITES_LOCATION.exists():
            if not any(self.host.favorites):
                # Remove file if all favorites are empty
                FAVORITES_LOCATION.unlink()
            else:
                with FAVORITES_LOCATION.open("w") as f:
                    yaml.dump(self.host.favorites, f)
        self.host.fav_btn_populate()
        self.target = None
        self.setup()
        self.close()


class FilterDialog(QDialog, filter_config.Ui_Dialog):
    def __init__(self, parent) -> None:
        super().__init__()
        self.setupUi(self)

        self.host = parent

        self.add_mapping = {
            self.whitelistAdd: self.whitelistLineEdit,
            self.alwaysIncludeAdd: self.alwaysIncludeLineEdit,
        }

        # Matches buttons to object it controls
        self.list_mapping = {
            self.whitelistAdd: self.whitelistList,
            self.alwaysIncludeAdd: self.alwaysIncludeList,
            self.whitelistRemove: self.whitelistList,
            self.alwaysIncludeRemove: self.alwaysIncludeList,
            self.whitelistClear: self.whitelistList,
            self.alwaysIncludeClear: self.alwaysIncludeList,
        }

        self.whitelistAdd.clicked.connect(self.add_item)
        self.alwaysIncludeAdd.clicked.connect(self.add_item)

        self.whitelistRemove.clicked.connect(self.remove_item)
        self.alwaysIncludeRemove.clicked.connect(self.remove_item)

        self.whitelistClear.clicked.connect(self.clear_list)
        self.alwaysIncludeClear.clicked.connect(self.clear_list)

        self.buttonBox.rejected.connect(self.close)
        self.buttonBox.accepted.connect(self.save_and_close)

    def save_and_close(self) -> None:
        self.host.config.setdefault("all", {}).update(self.properties)
        self.close()

    def add_item(self) -> None:
        """
        Add item to list
        """
        # Identifies sender signal and grabs button text
        dest = self.list_mapping[self.sender()]
        source_field = self.add_mapping[self.sender()]
        raw_label = source_field.text().strip()
        if not raw_label:  # Don't accept whitespace-only values
            logger.warning("No value entered.")
            return
        for count, label in enumerate(tag_split(raw_label)):
            label = clean_for_presentation(label)
            # Check if the label is in the list already
            existing_item = next(
                iter(dest.findItems(label, Qt.MatchExactly)),
                None,
            )
            if existing_item:
                # Clear the prior selection on the first iteration only
                if count == 0:
                    dest.selectionModel().clear()
                existing_item.setSelected(True)
                logger.warning("%s is already in the list.", label)
            else:
                dest.addItem(label)
                logger.info("Adding to list: %s", label)
        source_field.clear()

    def remove_item(self) -> None:
        dest = self.list_mapping[self.sender()]
        for item in dest.selectedItems():
            dest.takeItem(dest.row(item))

    def clear_list(self) -> None:
        dest = self.list_mapping[self.sender()]
        dest.clear()

    @property
    def properties(self) -> dict[str, list[str] | int]:
        return {
            "user_whitelist": [
                item.text()
                for item in self.whitelistList.findItems("*", Qt.MatchWildcard)
            ],
            "always_include": [
                item.text()
                for item in self.alwaysIncludeList.findItems(
                    "*", Qt.MatchWildcard
                )
            ],
            "highway_step_change": self.highwayStepChanges.value(),
        }

    @properties.setter
    def properties(self, config: Mapping) -> None:
        self.whitelistList.clear()
        for item in config.get("user_whitelist", []):
            self.whitelistList.addItem(item)
        self.alwaysIncludeList.clear()
        for item in config.get("always_include", []):
            self.alwaysIncludeList.addItem(item)
        if val := config.get("highway_step_change"):
            self.highwayStepChanges.setValue(max(val, 1))


class ChameleonProgressDialog(QProgressDialog):
    """
    Customizes QProgressDialog with methods specific to this app.
    """

    overpass_timeout_duration = OVERPASS_TIMEOUT

    def __init__(self, mode_count: int, geojson: bool = False):
        self.mode_count = mode_count
        self.current_phase = None  # osm_api, overpass, or mode
        self.current_mode = None
        # Tracks how many actual modes have been completed, independent of scaling
        self.modes_completed = 0
        self.osm_api_completed = 0
        self.osm_api_max = 0
        self.overpass_start_time = None
        self.overpass_timeout_time = None
        self.overpass_queries_completed = 0
        self.overpass_queries_max = int(geojson)

        self.is_overpass_complete = False

        super().__init__("", None, 0, self.real_max)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.setCancelButton(self.cancel_button)
        self.setAutoClose(False)
        self.setAutoReset(False)
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setLabelText("Beginning analysis…")
        self.setWindowFlags(
            Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint
        )

    @property
    def real_max(self) -> int:
        return (
            self.overpass_timeout_duration * self.overpass_queries_max
            + self.osm_api_max
            + self.mode_count * 10
        )

    @property
    def real_value(self) -> int:
        return (
            (
                (
                    # Count full overpass time if it already completed
                    self.is_overpass_complete
                    * self.overpass_timeout_duration
                    * self.overpass_queries_max
                )
                or (
                    # Add the overpass timeout time if it's being used.
                    self.overpass_elapsed
                    + self.overpass_queries_completed
                    * self.overpass_timeout_duration
                )
            )
            + self.osm_api_completed
            + self.modes_completed * 10
        )

    @property
    def using_overpass(self) -> bool:
        return (
            self.overpass_start_time is not None
            and self.overpass_timeout_time is not None
        )

    @property
    def overpass_remaining(self) -> int:
        return (
            max(
                round(
                    (
                        self.overpass_timeout_time - datetime.now().astimezone()
                    ).total_seconds()
                ),
                0,
            )
            if self.using_overpass
            else 0
        )

    @property
    def overpass_elapsed(self) -> int:
        return (
            round(
                (
                    datetime.now().astimezone() - self.overpass_start_time
                ).total_seconds()
            )
            if self.using_overpass
            else 0
        )

    def count_mode(self, mode: str) -> None:
        """
        Tracker for completion of individual modes in Worker class.

        Parameters
        ----------
        mode : str
            str returned from mode_start.emit()
        """
        self.current_phase = "mode"
        logger.info("mode_start signal -> caught mode: %s.", mode)
        if self.current_mode != mode:
            self.modes_completed += 1
            self.current_mode = mode

        self.update_info(f"Analyzing {self.current_mode} tag…")

    def scale_with_api_items(self, item_count: int) -> None:
        """
        Scales the bar by the number of items the API will be called for, so that the deleted mode
        is the same size as the other modes, but subdivided by the API item count

        Parameters
        ----------
        item_count : int
            Count of API items that will be run
        """
        self.cancel_button.setEnabled(True)
        self.current_phase = "osm_api"
        self.osm_api_max = item_count
        self.update_info(
            "Checking deleted items on OSM server "
            f"({self.osm_api_completed} of {self.osm_api_max})"
        )

    def increment_progbar_api(self) -> None:
        self.osm_api_completed += 1
        self.update_info(
            "Checking deleted items on OSM server "
            f"({self.osm_api_completed} of {self.osm_api_max})"
        )

    def check_api_done(self) -> None:
        """
        Disables the cancel button after the API check is complete
        """
        self.cancel_button.setEnabled(False)

    def overpass_counter(
        self,
        overpass_start_time: datetime,
        overpass_timeout_time: datetime,
        overpass_queries_completed: int,
        overpass_queries_max: int,
    ) -> None:
        self.current_phase = "overpass"
        self.overpass_start_time = overpass_start_time
        self.overpass_timeout_time = overpass_timeout_time
        self.overpass_queries_max = overpass_queries_max
        self.overpass_queries_completed = overpass_queries_completed

        while self.overpass_remaining > 0 and not self.is_overpass_complete:
            QApplication.processEvents()
            self.update_info(
                f"Getting query {self.overpass_queries_completed + 1} of "
                f"{self.overpass_queries_max} from Overpass. "
                f"{self.overpass_remaining} seconds until timeout"
            )
            time.sleep(0.1)
        if self.is_overpass_complete:
            self.update_info("Overpass response returned")
        else:
            self.update_info("Overpass timeout")

    def overpass_complete(self) -> None:
        self.is_overpass_complete = True

    def update_info(self, message) -> None:
        self.setLabelText(message)
        self.setMaximum(self.real_max)
        self.setValue(self.real_value)
        self.update()


def dirname(the_path: str | Path) -> Path:
    """
    Return the URI of the nearest directory,
    which can be self if it is a directory
    or else the parent
    """
    the_path = Path(the_path)
    return the_path.parent if not the_path.is_dir() else the_path


def plur(count: int) -> str:
    """
    Meant to used within f-strings, fills in an 's' where appropriate,
    based on input parameter. i.e., f"You have {count} item{plur(count)}."
    """
    return "" if count == 1 else "s"


def success_message(frame: ChameleonDataFrame) -> str:
    row_count = len(frame)
    return (
        # Empty dataframe
        f"{frame.chameleon_mode} has no change."
        if not row_count
        else (
            f"{frame.chameleon_mode} output "
            f"with {row_count} row{plur(row_count)}."
        )
    )


def filter_process(config: Mapping | None) -> dict:
    file_formats = {"all", "geojson", "csv", "excel"}

    # Check for resource file in directory
    if not config:
        config = {}

    # If keys are not sorted by file type, put them all under "all" key
    if set(config.keys()).isdisjoint(file_formats):
        config = {"all": deepcopy(config)}

    # Cast ignored modes to set where present
    for file_format in file_formats:
        if ignored_modes := config.get(file_format, {}).get("ignored_modes"):
            config[file_format]["ignored_modes"] = set(ignored_modes)
    return config


def tag_split(raw_label: str) -> list[str]:
    """
    Splits comma- and/or space-separated values and returns sorted list
    """
    splitter = shlex.shlex(raw_label)
    # Count commas as a delimiter and don't include in the tags
    splitter.whitespace += ","
    splitter.whitespace_split = True
    return sorted(splitter)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    form = MainApp()
    form.show()
    app.exec()
