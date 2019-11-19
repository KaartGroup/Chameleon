#!/usr/bin/env python3
"""
Opens a window with fields for input and selectors, which in turn opens
a worker object to process the input files with `q` and create output
in .csv format.
"""
import errno
import logging
import os
import re
import shlex
import sys
import tempfile
from collections import Counter, OrderedDict
from datetime import datetime
from pathlib import Path

import oyaml as yaml
# Finds the right place to save config and log files on each OS
from appdirs import user_config_dir, user_log_dir
from PyQt5 import QtCore, QtGui, QtWidgets
# from PyQt5.QtGui import QKeyEvent
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (QAction, QApplication, QCompleter, QMessageBox,
                             QProgressDialog)

# Import generated UI file
import chameleon.design
# Import sql processing module
from chameleon.q import (QInputParams, QOutput, QOutputParams, QOutputPrinter,
                         QTextAsData)

mutex = QtCore.QMutex()
waiting_for_input = QtCore.QWaitCondition()

# Configuration file locations
CONFIG_DIR = Path(user_config_dir("Chameleon", "Kaart"))
HISTORY_LOCATION = CONFIG_DIR / "history.yaml"
FAVORITE_LOCATION = CONFIG_DIR / "favorites.yaml"
COUNTER_LOCATION = CONFIG_DIR / "counter.yaml"

# Differentiate sys settings between pre and post-bundling
if getattr(sys, 'frozen', False):
    # Script is in a frozen package, i.e. PyInstaller
    RESOURCES_DIR = Path(sys._MEIPASS)
else:
    # Script is not in a frozen package
    # __file__ parent is chameleon2, parents[1] is chameleon-2
    RESOURCES_DIR = Path(__file__).parents[1] / "resources"

LOGGER = logging.getLogger()


def logger_setup(log_dir: Path):
    LOGGER.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Setup console logging output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    LOGGER.addHandler(console_handler)
    # Setup file logging output
    # Generate log file directory
    if not log_dir.is_dir():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            if e.errno != errno.EEXIST:
                LOGGER.error("Cannot create log directory.")
    if log_dir.is_dir():
        try:
            # Initialize Worker class logging
            log_path = str(log_dir / f"Chameleon_{datetime.now().date()}.log")
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            LOGGER.addHandler(file_handler)
        except OSError:
            LOGGER.error("Log file could not be generated at %s.", log_path)
        else:
            # Clean up log file if there are more than 15 (about 1MB)
            # Reading and sorting log file directory (ascending)
            log_list = sorted(
                [f for f in log_dir.glob("*.log") if f.is_file()])
            if len(log_list) > 15:
                rm_count = (len(log_list) - 15)
                # Remove extra log files that exceed 15 records
                for f in log_list[:rm_count]:
                    try:
                        LOGGER.info("removing...%s", f)
                        f.unlink()
                    except OSError:
                        LOGGER.exception()


# Log file locations
logger_setup(Path(user_log_dir("Chameleon", "Kaart")))


class Worker(QObject):
    """

    Worker class, code inside slot should execute in a separate thread.
    Displays file paths, executes comparison function, writes and saves file.

    """
    done = pyqtSignal()
    mode_start = pyqtSignal(str)
    overwrite_confirm = pyqtSignal(str)
    dialog_critical = pyqtSignal(str, str)
    dialog_information = pyqtSignal(str, str)

    def __init__(self, modes: set, files: dict, group_output: bool, parent):
        super().__init__()
        # Define set of selected modes
        self.modes = modes
        self.files = files
        self.group_output = group_output
        self.parent = parent
        self.response = None
        self.output_printer = QOutputPrinter(
            QOutputParams(delimiter='\t', output_header=True))
        self.input_params = QInputParams(skip_header=True, delimiter='\t')

    @pyqtSlot()
    def run(self):
        """
        Runs when thread started, saves history to file and calls other functions to write files.
        """
        # self.progress_bar
        # Saving paths to config for future loading
        # Make directory if it doesn't exist
        if not CONFIG_DIR.is_dir():
            try:
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            except FileExistsError:
                LOGGER.debug("Config directory already exists")
            except OSError:
                LOGGER.debug("Config directory could not be created.")
        if self.files:
            file_strings = {k: str(v)
                            for k, v in self.files.items()}
            try:
                with HISTORY_LOCATION.open('w') as history_file:
                    yaml.dump(file_strings, history_file)
            except OSError:
                LOGGER.exception("Couldn't write history.yaml.")
            else:
                # In some rare cases (like testing) MainApp may not exist
                try:
                    self.parent.history_dict = file_strings
                except NameError:
                    pass
        # For processing error messages
        old_regex = re.compile(r":\s+\bold\b\.")
        new_regex = re.compile(r":\s+\bnew\b\.")
        # Will hold any failed steps for display at the end
        error_list = []
        # Will hold all successful steps for display at the end
        success_list = []
        has_highway = self.check_highway(self.files, self.input_params)
        if has_highway:
            LOGGER.info("Both source docs have a highway column")
        # print(f"Before run: {self.modes} with {type(self.modes)}.")
        try:
            for mode in self.modes:
                LOGGER.debug("Executing processing for %s.", (mode))
                self.mode_start.emit(mode)
                sanitized_mode = mode.replace(":", "_")
                result = self.execute_query(
                    mode, self.files, self.group_output, has_highway)
                # Check if query ran sucessfully
                file_name = Path(
                    f"{self.files['output']}_{sanitized_mode}.csv")
                # File reading failed, usually because a nonexistent column
                if result.status == 'error':
                    # Build error message for later display
                    error_message = str(result.error.exception)
                    if old_regex.search(error_message):
                        error_message = re.sub(
                            old_regex, " in old data file: ", error_message)
                    elif new_regex.search(error_message):
                        error_message = re.sub(
                            new_regex, " in new data file: ", error_message)
                    error_message = error_message.capitalize()
                    error_list.append(error_message)
                    continue
                if file_name.is_file():  # Prompt and wait for confirmation before overwriting
                    self.overwrite_confirm.emit(str(file_name))
                    mutex.lock()
                    try:
                        # Don't check for a response until after the user has a chance to give one
                        waiting_for_input.wait(mutex)
                        if not self.response:
                            LOGGER.info("Skipping %s.", (mode))
                            continue
                    finally:
                        mutex.unlock()
                LOGGER.info("Writing %s", (file_name))
                try:
                    with file_name.open("w") as output_file:
                        self.output_printer.print_output(
                            output_file, sys.stderr, result)
                except OSError:
                    LOGGER.exception("Write error.")
                else:
                    if not result.data or len(result.data) == 1:
                        # If there's only one row, it's a header
                        success_message = (f"{mode} has no change.")
                    else:
                        # Exclude the header row from the row count
                        data_len = len(result.data) - 1
                        s = ""
                        if data_len > 1:
                            s = "s"
                        success_message = (
                            f"{mode} output with {data_len} row{s}.")
                    success_list.append(success_message)
                    # Logging q errors when try fails.
                    LOGGER.debug("q_output details: %s.", result)
                    LOGGER.info(
                        "Processing for %s complete. %s written.", mode, file_name)
            # print(f"After run: {self.modes} with {type(self.modes)}.")
        finally:
            # print(f"End run: {self.modes} with {type(self.modes)}.")
            # print(f"Before clear: {self.modes} with {type(self.modes)}.")

            if error_list:  # Some tags failed
                if len(error_list) == 1:
                    headline = "A tag could not be queried"
                    summary = error_list[0]
                else:
                    headline = "Tags could not be queried"
                    summary = "\n".join(error_list)
                if success_list:
                    headline = "Some tags could not be queried"
                    summary += "\nThe following tags completed successfully:\n\n".join(
                        success_list)
                self.dialog_critical.emit(
                    headline, summary)
            elif success_list:  # Nothing failed, everything suceeded
                summary = "All tags completed!\n\n".join(success_list)
                self.dialog_information.emit("Success", summary)
            # Nothing succeeded and nothing failed, probably because user declined to overwrite
            else:
                self.dialog_information.emit("Nothing saved", "No files saved")
            self.modes.clear()
            # print(f"After clear: {self.modes} with {type(self.modes)}.")
            LOGGER.info(success_list)
            # Signal the main thread that this thread is complete
            self.done.emit()

    @staticmethod
    def check_highway(files: dict, input_params: QInputParams) -> bool:
        """

        Parameters
        ----------
        files : dict:
            Dictionary containing old and new file paths
        input_params : QInputParams:
            input params for files
        Returns
        -------
        bool:
            True if both files contain a highway column
            False if one or none of the files contain a highway column
        """
        highway_check_old_sql = f"SELECT highway FROM {files['old']} LIMIT 1"
        highway_check_new_sql = f"SELECT highway FROM {files['new']} LIMIT 1"
        q_engine = QTextAsData()
        return q_engine.execute(
            highway_check_new_sql, input_params).status != 'error' and q_engine.execute(
                highway_check_old_sql, input_params).status != 'error'

    def execute_query(self, mode: str, files: dict, group_output=False, has_highway=False) -> QOutput:
        """
        Saves file path for future loading, create a directory if one does not
        already exist. Groups JOSM tags with SQL and generates suitable output.

        Raises
        ------
        OSError
            If history path does not exist and returns a system-related error.
        """
        # Clean up tags with : that cannot be escaped with sqlite3
        sanitized_mode = mode.replace(":", "_")
        q_engine = QTextAsData()
        # Creating SQL snippets
        sql = self.build_query(mode, files, group_output, has_highway)
        # When using the grouped output option, files are queried twice,
        # with the first step being written to a tempfile.
        if group_output:
            # Generating temporary output files (max size 100 MB)
            tempf = tempfile.NamedTemporaryFile(
                mode='w', buffering=-1, encoding=None, newline=None,
                suffix=".csv", prefix=None, dir=None, delete=True)
            LOGGER.debug("Writing to temp file.")
            q_output = q_engine.execute(
                sql, self.input_params)
            # If missing a tag, return early so the calling loop can grab the error
            if q_output.status == 'error':
                tempf.close()
                return q_output
            # print(q_output.data)
            # grouped_output_printer = QOutputPrinter(
            # QOutputParams(delimiter='\t', output_header=True))
            self.output_printer.print_output(
                tempf, sys.stderr, q_output)

            # Logging and printing debug statements for associated q errors
            LOGGER.debug(
                "Intermediate processing completed for %s.", (mode))

            # Grouping function with q
            sql = ("SELECT ('http://localhost:8111/load_object?new_layer=true&objects=' || "
                   "group_concat(id)) AS url, count(id) AS count,"
                   "group_concat(distinct user) AS users,max(timestamp) AS latest_timestamp,"
                   "min(version) AS version, ")
            if mode != "highway" and has_highway:
                sql += "highway,"
            sql += (f"old_{sanitized_mode},new_{sanitized_mode}, "
                    "group_concat(DISTINCT action) AS actions, "
                    f"NULL AS \"notes\" FROM {tempf.name} "
                    f"GROUP BY old_{sanitized_mode},new_{sanitized_mode},action;")
            LOGGER.debug(
                f"Grouped enabled, Processing group sql query: {sql}.")
        # Proceed with generating tangible output for user
        result = q_engine.execute(sql, self.input_params)
        if group_output:
            tempf.close()
        return result

    @staticmethod
    def build_query(mode: str, files: dict, group_output=False, has_highway=False) -> str:
        """
        Constructs the SQL string from user input
        """
        # Clean up tags with : that cannot be escaped with sqlite3
        sanitized_mode = mode.replace(":", "_")
        # Added based ID SQL to ensure Object ID output
        # LEFT OUTER JOIN to isolate instances of old NOT LIKE new
        sql = ("SELECT (substr(ifnull(new.\"@type\",old.\"@type\"),1,1) || "
               "ifnull(new.\"@id\",old.\"@id\")) AS id, ")
        if not group_output:
            sql += ("('http://localhost:8111/load_object?new_layer=true&objects=' || "
                    "substr(ifnull(new.\"@type\",old.\"@type\"),1,1) || "
                    "ifnull(new.\"@id\",old.\"@id\")) AS url, ")
        sql += ("ifnull(new.\"@user\",old.\"@user\") AS user, substr(ifnull(new.\"@timestamp\","
                "old.\"@timestamp\"),1,10) AS timestamp, "
                "ifnull(new.\"@version\",old.\"@version\") AS version, ")
        if mode != "highway" and has_highway:
            sql += "ifnull(new.highway,old.highway) AS highway, "
        if mode != "name":
            sql += "ifnull(new.name,old.name) AS name, "
        sql += (f"ifnull(old.\"{mode}\",'') AS old_{sanitized_mode}, "
                f"ifnull(new.\"{mode}\",'') AS new_{sanitized_mode}, "
                # Differentiate between objects that are modified and deleted
                "CASE WHEN new.\"@id\" LIKE old.\"@id\" THEN \"modified\" "
                "ELSE \"deleted\" END \"action\" ")
        if not group_output:
            sql += ", NULL AS \"notes\" "
        sql += (f"FROM {files['old']} AS old "
                f"LEFT OUTER JOIN {files['new']} AS new ON old.\"@id\" = new.\"@id\" "
                f"WHERE old_{sanitized_mode} NOT LIKE new_{sanitized_mode} "
                # UNION FULL LEFT OUTER JOIN to isolated instances of new objects
                "UNION ALL SELECT (substr(new.\"@type\",1,1) || new.\"@id\") AS id, ")
        if not group_output:
            sql += ("('http://localhost:8111/load_object?new_layer=true&objects=' || "
                    "substr(new.\"@type\",1,1) || new.\"@id\") AS url, ")
        sql += ("new.\"@user\" AS user, substr(new.\"@timestamp\",1,10) AS timestamp, "
                "new.\"@version\" AS version, ")
        if mode != "highway" and has_highway:
            sql += "new.highway AS highway, "
        if mode != "name":
            sql += "new.name AS name, "
        sql += (f"ifnull(old.\"{mode}\",'') AS old_{sanitized_mode}, "
                f"ifnull(new.\"{mode}\",'') AS new_{sanitized_mode}, "
                # 'action' defaults to 'new' to capture 'added' and 'split' objects
                "\"new\" AS \"action\" ")
        if not group_output:
            sql += ", NULL AS \"notes\" "
        sql += (f"FROM {files['new']} AS new "
                f"LEFT OUTER JOIN {files['old']} AS old ON new.\"@id\" = old.\"@id\" "
                f"WHERE old.\"@id\" IS NULL AND length(ifnull(new_{sanitized_mode},'')) > 0")
        LOGGER.debug("Processing sql query: %s", (sql))
        return sql


class MainApp(QtWidgets.QMainWindow, QtGui.QKeyEvent, chameleon.design.Ui_MainWindow):
    """

    Main PyQT window class that allows communication between UI and backend.
    Passes QMainWindow parameter to provide main application window, establish
    event handling with signal/slot connection.

    """
    clear_search_box = pyqtSignal()

    def __init__(self, parent=None):
        """
        Loads history file path, establish event handling with signal/slot
        connection.
        """
        super().__init__()
        self.setupUi(self)
        # Set up application logo on main window
        self.setWindowTitle("Chameleon")
        # Enable QWidgets to capture and filter QKeyEvents
        self.searchButton.installEventFilter(self)
        self.listWidget.installEventFilter(self)

        # Differentiate sys settings between pre and post-bundling
        if getattr(sys, 'frozen', False):
            logo = Path(sys._MEIPASS) / "chameleon.png"
            logo_path = str(Path.resolve(logo))
        else:
            logo = Path(__file__).parents[1] / "resources/chameleon.png"
            logo_path = str(Path.resolve(logo))
        self.setWindowIcon(QtGui.QIcon(logo_path))
        self.logo = logo_path

        self.text_fields = {
            "old": self.oldFileNameBox,
            "new": self.newFileNameBox,
            "output": self.outputFileNameBox
        }

        # Menu bar customization
        # Define Qactions for menu bar
        # About action for File menu
        info_action = QAction("&About Chameleon", self)
        info_action.setShortcut("Ctrl+I")
        info_action.setStatusTip('Software description.')
        info_action.triggered.connect(self.about_menu)
        # Exit action for File menu
        extract_action = QAction("&Exit Chameleon", self)
        extract_action.setShortcut("Ctrl+Q")
        extract_action.setStatusTip('Close application.')
        extract_action.triggered.connect(self.close)
        # Declare menu bar settings
        main_menu = self.menuBar()
        file_menu = main_menu.addMenu('&File')
        file_menu.addAction(info_action)
        file_menu.addAction(extract_action)

        # Logging initialization of Chameleon
        LOGGER.info("Chameleon started at %s.", (datetime.now()))

        # Sets run button to not enabled
        self.run_checker()
        # OSM tag resource file, construct list from file
        autocomplete_source = RESOURCES_DIR / "OSMtag.yaml"

        try:
            with autocomplete_source.open() as read_file:
                self.auto_completer(yaml.safe_load(read_file))
        except OSError:
            LOGGER.exception("Couldn't read the autocomplete source file.")
        except (TypeError, NameError):
            LOGGER.exception("Could not load any autocomplete tags.")

        # YAML file loaders
        # Load file paths into boxes from previous session

        # Check for history file and load if exists
        try:
            with HISTORY_LOCATION.open('r') as history_file:
                self.history_dict = yaml.safe_load(history_file)
        # If file doesn't exist, fail silently
        except FileNotFoundError:
            LOGGER.warning(
                "History file could not be found. "
                "This is normal when running the program for the first time.")
        except PermissionError:
            LOGGER.exception("History file found but not readable.")
        else:
            if isinstance(self.history_dict, dict):
                for k, v in self.text_fields.items():
                    v.insert(self.history_dict.get(k, ''))

        # List all of our buttons to populate so we can iterate through them
        self.fav_btn = [self.popTag1, self.popTag2,
                        self.popTag3, self.popTag4, self.popTag5]

        # Populate the buttons defined above
        self.fav_btn_populate(FAVORITE_LOCATION, self.fav_btn)

        # Connecting signals to slots within init
        self.oldFileSelectButton.clicked.connect(self.open_input_file)
        self.newFileSelectButton.clicked.connect(self.open_input_file)
        self.outputFileSelectButton.clicked.connect(self.output_file)
        self.runButton.clicked.connect(self.run_query)
        self.runButton.clicked.connect(self.list_sender)
        for i in self.fav_btn:
            i.clicked.connect(self.add_tag)
        self.searchButton.clicked.connect(self.add_tag)
        self.deleteItemButton.clicked.connect(self.delete_tag)
        self.clearListButton.clicked.connect(self.clear_tag)
        # Clears the search box after an item is selected from the autocomplete list
        self.clear_search_box.connect(
            self.searchBox.clear, QtCore.Qt.QueuedConnection)

        # Labelling strings for filename boxes
        self.oldFileSelectButton.shortname = "old"
        self.newFileSelectButton.shortname = "new"
        # Define which button controls which filename box
        self.oldFileSelectButton.box_control = self.oldFileNameBox
        self.newFileSelectButton.box_control = self.newFileNameBox

    def about_menu(self):
        """
        Handles about page information.

        Parameters
        ----------
        path: str
            File path to application logo
        """
        logo = QtGui.QIcon(QtGui.QPixmap(self.logo))
        try:
            with (RESOURCES_DIR / 'version.txt').open('r') as version_file:
                version = version_file.read()
        except FileNotFoundError:
            version = ''
            LOGGER.warning("No version number detected")
        except OSError:
            pass
        else:
            if version:
                version = f"<p><center>Version {version}</center></p>"
        about = QMessageBox(self, icon=logo, textFormat=QtCore.Qt.RichText)
        about.setWindowTitle("About Chameleon")
        about.setIconPixmap(QtGui.QPixmap(
            self.logo).scaled(160, 160, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        about.setText('''
                    <h2><center>Chameleon</center></h2>
                    <p>This application compares OSM snapshot data from
                    <a href="https://overpass-turbo.eu/">Overpass Turbo</a>
                    and returns an output of changes that occurred between the snapshots.</p>
                    <p>Application made by <a href="http://kaartgroup.com/">Kaart</a>'s development team.<br>
                    Licensed under <a href="https://choosealicense.com/licenses/gpl-3.0/">GPL3</a>.</p>''')
        about.setInformativeText(
            "<i>Powered by: <a href=https://www.riverbankcomputing.com/software/pyqt/download5>PyQt5</a>, "
            "<a href=https://github.com/harelba/q>q</a>, "
            "<a href=https://github.com/ActiveState/appdirs>appdir</a>, "
            "<a href=https://github.com/wimglenn/oyaml>oyaml</a>, "
            "and <a href=https://www.pyinstaller.org>PyInstaller</a>.</i>")
        about.show()

    @staticmethod
    def fav_btn_populate(favorite_path: Path, fav_btn: list):
        """
        Populates the listed buttons with favorites from the given file

        Parameters
        ----------
        favorite_path : Path
            Location of YAML file with favorite values to be loaded
        fav_btn : list
            List of buttons to be populated with values
        """
        # Holds the button values until they are inserted
        fav_list = []
        # Check for favorite file and load if exists
        try:
            with favorite_path.open('r') as favorite_read:
                # Load in popular tags from history file
                # Default values are taken if history file does not exist
                fav_list = yaml.safe_load(favorite_read)  # dict()
        except FileNotFoundError:
            LOGGER.warning("favorites.yaml could not be found. "
                           "This is normal when running the program for the first time.")
        except PermissionError:
            LOGGER.exception("favorites.yaml could not be opened.")
        else:  # Don't bother doing anything with favorites if the file couldn't be read
            LOGGER.debug(
                f"Fav history is: {fav_list} with type: {type(fav_list)}.")
        if len(fav_list) < len(fav_btn):
            # If we run out of favorites, start adding non-redundant default tags
            # We use these when there aren't enough favorites
            default_tags = ['highway', 'name', 'ref',
                            'addr:housenumber', 'addr:street']
            # Count how many def tags are needed
            def_count = len(fav_btn) - len(fav_list)
            # Add requisite number of non-redundant tags from the default list
            fav_list += [i for i in default_tags
                         if i not in fav_list][:def_count]
        # Loop through the buttons and apply our ordered tag values
        for index, btn in enumerate(fav_btn):
            try:
                # The fav_btn and set_lists should have a 1:1 correspondence
                btn.setText(fav_list[index])
            # Capture errors from the set_list not being created properly
            except IndexError as e:
                LOGGER.exception(
                    "Index %s of fav_btn doesn't exist! Attempted to insert from %s.", index, fav_list)
                raise IndexError(f"Index {index} of fav_btn doesn't exist! "
                                 f"Attempted to insert from{fav_list}.") from e

    def auto_completer(self, tags: list):
        """
        Autocompletion of user searches in searchBox.
        Utilizes resource file for associated autocomplete options.
        """
        # Needs to have tags reference a resource file of OSM tags
        # Check current autocomplete list
        LOGGER.debug(
            f"A total of {len(tags)} tags was added to auto-complete.")
        completer = QCompleter(tags)
        self.searchBox.setCompleter(completer)

    def add_tag(self):
        """
        Adds user defined tags into processing list on QListWidget.
        """
        # Identifies sender signal and grabs button text
        if self.sender() is self.searchButton:
            # Value was typed by user
            raw_label = self.searchBox.text()
            if not raw_label.strip():  # Don't accept whitespace-only values
                LOGGER.warning('No value entered.')
                return
        elif self.sender() in self.fav_btn:
            # Value was clicked from fav btn
            raw_label = self.sender().text()
        splitter = shlex.shlex(raw_label)
        splitter.whitespace += ','  # Count commas as a delimiter and don't include in the tags
        splitter.whitespace_split = True
        label_list = sorted(list(splitter))
        for i, label in enumerate(label_list):
            # Check if the label is in the list already
            existing_item = self.listWidget.findItems(
                label, QtCore.Qt.MatchExactly)
            if existing_item:
                if i == 0:
                    self.listWidget.selectionModel().clear()
                # existing_item should never have more than 1 member
                existing_item[0].setSelected(True)
                LOGGER.warning('%s is already in the list.', label)
            else:
                self.listWidget.addItem(label)
                LOGGER.info('Adding to list: %s', label)
        self.clear_search_box.emit()
        self.run_checker()
        self.listWidget.repaint()

    def delete_tag(self):
        """
        Clears selected list items with "Delete" button.
        Execute on `Delete` button signal.
        """
        try:
            # Remove selected items in user-selected Qlist
            for item in self.listWidget.selectedItems():
                self.listWidget.takeItem(self.listWidget.row(item))
                LOGGER.info("Deleted %s from processing list.", (item.text()))
            self.run_checker()
        # Fails silently if nothing is selected
        except AttributeError:
            LOGGER.exception()
        self.listWidget.repaint()

    def clear_tag(self):
        """
        Wipes all tags listed on QList with "Clear" button.
        Execute on `Clear` button signal.
        """
        self.listWidget.clear()
        LOGGER.info('Cleared tag list.')
        self.run_checker()
        self.listWidget.repaint()

    def list_sender(self) -> list:
        """
        Sends user-defined list as sets for backend processing.
        Executes on `Run` operations.
        """

        return [self.listWidget.item(i).text() for i in range(self.listWidget.count())]

    @staticmethod
    def document_tag(run_list: list, counter_location: Path, favorite_location: Path):
        """
        Python counter for tags that are frequently chosen by user.
        Document counter and favorites using yaml file storage.
        Function parses counter.yaml and dump into favorites.yaml.
        """
        cur_counter = dict()
        # Parse counter.yaml for user tag preference
        try:
            with counter_location.open('r') as counter_read:
                cur_counter = OrderedDict(yaml.load(counter_read))
                LOGGER.debug("counter.yaml history: %s.", (cur_counter))
        # If file doesn't exist, fail silently
        except FileNotFoundError:
            LOGGER.warning("Couldn't read the tag count file. "
                           "This is normal if this is your first time runnning the application.")
        except OSError:
            LOGGER.exception()

        # Casting list into dictionary with counts
        # Counter() sorts in reverse order (highest first)
        # Counter() generates a counter collections object
        dict_counter = dict(Counter(run_list).items())
        # Combining history counter with new counter
        sum_counter = dict(Counter(dict_counter) + Counter(cur_counter))
        # Sorting counter collections into ordered dictionary
        sorted_counter = OrderedDict(
            sorted(sum_counter.items(), key=lambda x: x[1], reverse=True))
        rank_tags = list(sorted_counter.keys())
        # Saving tag counts to config directory
        try:
            with counter_location.open('w') as counter_write:
                yaml.dump(dict(sorted_counter), counter_write)
                LOGGER.info(f"counter.yaml dump with: {sorted_counter}.")
        except OSError:
            LOGGER.exception("Couldn't write counter file.")
        # Saving favorite tags to config directory
        try:
            with favorite_location.open('w') as favorite_write:
                yaml.dump(rank_tags, favorite_write)
                LOGGER.info(f"favorites.yaml dump with: {rank_tags}.")
        # If file doesn't exist, fail silently
        except OSError:
            LOGGER.exception("Couldn't write favorite file.")

    def open_input_file(self):
        """
        Adds functionality to the Open Old/New File (...) button, opens the
        '/downloads' system path to find csv file.
        """
        sender = self.sender()
        destination = sender.box_control
        # If there is text in the input box, open the dialog at that location
        if destination.text().strip():
            file_dir = destination.text()
        # If the target box is empty, look for a value in each of the boxes
        elif self.oldFileNameBox.text().strip():
            file_dir = self.oldFileNameBox.text()
        elif self.newFileNameBox.text().strip():
            file_dir = self.newFileNameBox.text()
        # If no previous location, default to Downloads folder
        else:
            file_dir = os.path.expanduser("~/Downloads")
        file_name, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, f"Select CSV file with {sender.shortname} data", file_dir, "CSV (*.csv)")
        if file_name:  # Clear the box before adding the new path
            destination.clear()
            destination.insert(file_name)

    def output_file(self):
        """
        Adds functionality to the Output File (...) button, opens the
        '/downloads' system path for user to name an output file.
        """
        if self.outputFileNameBox.text().strip():
            output_file_dir = os.path.dirname(self.outputFileNameBox.text())
        else:
            # If no previous location, default to Documents folder
            output_file_dir = os.path.expanduser("~/Documents")
        output_file_name, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self, "Enter output file prefix", output_file_dir)
        if output_file_name:  # Clear the box before adding the new path
            # Since this is a prefix, the user shouldn't be adding their own extension
            if ".csv" in output_file_name:
                output_file_name = output_file_name.replace('.csv', '')
            self.outputFileNameBox.clear()
            self.outputFileNameBox.insert(output_file_name)

    def run_checker(self):
        """
        Function that disable/enables run button based on list items.
        """
        if self.listWidget.count() > 0:
            self.runButton.setEnabled(True)
        else:
            self.runButton.setEnabled(False)
        self.repaint()

    def dialog_critical(self, text: str, info: str):
        """
        Method to pop-up critical error box

        Parameters
        ----------
        text, info : str
            Optional error box text.
        """
        dialog = QMessageBox(self)
        dialog.setText(text)
        dialog.setIcon(QMessageBox.Critical)
        dialog.setInformativeText(info)
        dialog.exec()

    def dialog_information(self, text: str, info: str):
        """
        Method to pop-up informational error box

        Parameters
        ----------
        text, info : str
            Optional error box text.
        """
        dialog = QMessageBox(self)
        dialog.setMinimumWidth(300)
        dialog.setText(text)
        dialog.setIcon(QMessageBox.Information)
        dialog.setInformativeText(info)
        dialog.exec()

    def run_query(self):
        """
        Allows run button to execute based on selected tag parameters.
        Also Enables/disables run button while executing function and allows
        progress bar functionality. Checks for file/directory validity and spacing.
        """
        # Check for blank values
        space_expression = re.compile("^\\S+\\s+\\S+$")
        for k, v in self.text_fields.items():
            if not v.text().strip():
                self.dialog_critical(
                    f"{k.title()} file field is blank.",
                    "Please enter a value"
                )
                return
            # Check for spaces in file names
            if space_expression.match(v.text()):
                # Popup here
                self.dialog_critical(
                    "Chameleon cannot use files or folders with spaces in their names.",
                    "Please rename your files and/or folders to remove spaces.")
                return
        # Wrap the file references in Path object to prepare "file not found" warning
        file_paths = {k: Path(v.text())
                      for k, v in self.text_fields.items()}
        # Check if either old or new file/directory exists. If not, notify user.
        if not file_paths['old'].is_file() or not file_paths['new'].is_file():
            if not file_paths['old'].is_file() and not file_paths['new'].is_file():
                self.dialog_critical("File or directories not found!", "")
            elif not file_paths['old'].is_file():
                self.dialog_critical(
                    "Old file or directory not found!", "")
            elif not file_paths['new'].is_file():
                self.dialog_critical(
                    "New file or directory not found!", "")
            return
        # Check if output directory is writable
        try:
            if not os.access(file_paths['output'].parent, os.W_OK):
                self.dialog_critical(
                    "Output directory not writeable!", "")
                return
        except IndexError:
            self.dialog_critical(
                "Output file field is blank.",
                "Please enter a value."
            )
            return
        # modes var needs to be type set()
        self.document_tag(self.list_sender(), COUNTER_LOCATION,
                          FAVORITE_LOCATION)  # Execute favorite tracking
        modes = set(self.list_sender())
        LOGGER.info("Modes to be processed: %s.", (modes))
        group_output = self.groupingCheckBox.isChecked()

        self.progress_bar = QProgressDialog()
        self.progress_bar.setModal(True)
        self.progress_bar.setCancelButton(None)
        self.progress_bar.setMinimumWidth(400)
        # self.progress_bar.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        # Add one mode more that the length so that a full bar represents completion
        # When the final tag is started, the bar will show one increment remaining
        self.progress_bar.setMaximum(len(modes) + 1)
        self.progress_bar.setValue(0)
        # Disables the system default close, minimize, maximuize buttons
        self.progress_bar.setWindowFlags(
            QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.CustomizeWindowHint)
        # First task of Worker is to check for highway tag in source files
        self.progress_bar.setLabelText("Analyzing file structure…")
        self.progress_bar.show()
        # Handles Worker class and QThreads for Worker
        self.work_thread = QThread()
        self.worker = Worker(modes, file_paths, group_output, self)
        # Connect to progbar_counter() when 1 mode begins in Worker
        self.worker.mode_start.connect(self.progbar_counter)
        # Connect to finished() when all modes are done in Worker
        self.worker.done.connect(self.finished)
        # Connect signal from Worker to handle overwriting files
        self.worker.overwrite_confirm.connect(self.overwrite_message)
        self.worker.dialog_critical.connect(self.dialog_critical)
        self.worker.dialog_information.connect(self.dialog_information)
        self.worker.moveToThread(self.work_thread)
        self.work_thread.started.connect(self.worker.run)
        self.work_thread.start()

    def progbar_counter(self, mode: str):
        """
        Tracker for completion of individual modes in Worker class.

        Parameters
        ----------
        mode : str
            str returned from mode_start.emit()
        """
        LOGGER.info("mode_start signal -> caught mode: %s.", (mode))
        if mode:
            # Advance index of modes by 1
            self.progress_bar.setValue(self.progress_bar.value() + 1)
            self.progress_bar.setLabelText(f"Analyzing {mode} tag…")

    def eventFilter(self, obj, event):
        """
        Allows installed objects to filter QKeyEvents.

        Parameters
        ----------
        obj : class
            Specific QWidget target

        event : class
            Event which handles keystroke input
        """
        # Sets up filter to enable keyboard input in listWidget
        if self.searchButton == obj and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Tab and self.listWidget.count() > 0:
                self.listWidget.item(0).setSelected(True)
            elif event.key() == QtCore.Qt.Key_Tab and self.listWidget.count() == 0:
                event.ignore()

        # Set up filter to enable delete key within listWidget
        if self.listWidget == obj and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Delete and self.listWidget.count() > 0:
                self.delete_tag()
            elif event.key() == QtCore.Qt.Key_Delete and self.listWidget.count() == 0:
                event.ignore()

        return super(MainApp, self).eventFilter(obj, event)

    # Re-enable run button when function complete
    def finished(self):
        """
        Helper method finalizes run process: re-enable run button
        and notify user of run process completion.
        """
        # Quits work_thread and reset
        # Needs worker logging
        self.work_thread.quit()
        # self.work_thread.wait()
        # In theory this deletes the worker only when done
        self.worker.deleteLater()
        self.progress_bar.close()
        # Logging processing completion
        LOGGER.info("All Chameleon analysis processing completed.")
        self.run_checker()

    def overwrite_message(self, file_name: str):
        """
        Display user notification box for overwrite file option.

        Parameters
        ----------
        file_name : str
            File (named by user) to be saved and written.
        """
        overwrite_prompt = QtWidgets.QMessageBox()
        overwrite_prompt.setIcon(QMessageBox.Question)
        overwrite_prompt_response = overwrite_prompt.question(
            self, '', f"{file_name} exists. <p> Do you want to overwrite? </p>",
            overwrite_prompt.No | overwrite_prompt.Yes)
        if overwrite_prompt_response == overwrite_prompt.Yes:
            self.worker.response = True
        else:
            self.worker.response = False
        waiting_for_input.wakeAll()

    def closeEvent(self, event):
        """
        Overrides the closeEvent method to allow an exit prompt.

        Parameters
        ----------
        event : class
            Event which handles the exit prompt.
        """
        # Make a dict of text field values
        files = {k: v.text()
                 for k, v in self.text_fields.items()}
        # Prompt if user has changed input values from what was loaded
        try:
            if self.history_dict != files:
                exit_prompt = QtWidgets.QMessageBox()
                exit_prompt.setIcon(QMessageBox.Question)
                exit_response = exit_prompt.question(
                    self, '', "Discard field inputs?",
                    exit_prompt.Yes, exit_prompt.No
                )
                if exit_response == exit_prompt.Yes:
                    event.accept()
                else:
                    event.ignore()
        # Fail silently if history.yaml does not exist
        except AttributeError:
            LOGGER.warning("All Chameleon analysis processing completed.")


def main():
    """
    Creates a new instance of the QtWidget application, sets the form to be
    out MainWIndow (design) and executes the application.
    """
    app = QApplication(sys.argv)
    # Enable High DPI display with PyQt5
    QtWidgets.QApplication.setAttribute(
        QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    form = MainApp()
    form.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
