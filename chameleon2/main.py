#!/usr/bin/env python3
"""
Opens a window with fields for input and selectors, which in turn opens
a worker object to process the input files with `q` and create output
in .csv format.
"""
import errno
import logging
import os
import os.path
import re
import sys
import tempfile
import time
from collections import Counter, OrderedDict
from datetime import datetime
from pathlib import Path

import oyaml as yaml
# Finds the right place to save config and log files on each OS
from appdirs import user_config_dir, user_log_dir
from PyQt5 import QtCore, QtGui, QtWidgets
# from PyQt5.QtGui import QKeyEvent
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QAction, QApplication, QCompleter, QMessageBox

import chameleon2.design  # Import generated UI file
from chameleon2.ProgressBar import ProgressBar
# Does the processing
from chameleon2.q import QInputParams, QOutputParams, QOutputPrinter, QTextAsData, QOutput

mutex = QtCore.QMutex()
waiting_for_input = QtCore.QWaitCondition()

# Configuration file locations
CONFIG_DIR = Path(user_config_dir("Chameleon 2", "Kaart"))
HISTORY_LOCATION = CONFIG_DIR.joinpath("history.yaml")
FAVORITE_LOCATION = CONFIG_DIR.joinpath("favorites.yaml")
COUNTER_LOCATION = CONFIG_DIR.joinpath("counter.yaml")
# Log file locations
LOG_DIR = Path(user_log_dir("Chameleon 2", "Kaart"))
# Generate log file directory
if not LOG_DIR.is_dir():
    try:
        LOG_DIR.mkdir()
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            print(f"Cannot create log directory: {exc}.")
if LOG_DIR.is_dir():
    try:
        # Initialize Worker class logging
        LOG_PATH = str(LOG_DIR.joinpath(
            f"Chameleon2_{datetime.now().date()}.log"))
        logging.basicConfig(filename=LOG_PATH, level=logging.DEBUG)
    except OSError:
        print(f"Log file could not be generated at {LOG_PATH}.")


class Worker(QObject):
    """

    Worker class, code inside slot should execute in a separate thread.
    Displays file paths, executes comparison function, writes and saves file.

    """
    done = pyqtSignal()
    mode_done = pyqtSignal(str)
    overwrite_confirm = pyqtSignal(str)
    dialog_critical = pyqtSignal(str, str)
    dialog_information = pyqtSignal(str, str)

    def __init__(self, modes: set, files: dict, group_output: bool):
        super().__init__()
        # Define set of selected modes
        self.modes = modes
        self.files = files
        self.group_output = group_output
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
                CONFIG_DIR.mkdir()
            except FileExistsError:
                logging.debug("Config directory already exists")
            except OSError as e:
                logging.debug(f"Config directory could not be created: {e}")
        if self.files:
            with HISTORY_LOCATION.open('w') as file:
                yaml.dump(self.files, file)
        # For processing error messages
        old_regex = re.compile(r":\s+\bold\b\.")
        new_regex = re.compile(r":\s+\bnew\b\.")
        error_list = []
        success_list = []
        has_highway = self.check_highway(self.files, self.input_params)
        if has_highway:
            print("Both source docs have a highway column")
        # print(f"Before run: {self.modes} with {type(self.modes)}.")
        try:
            for mode in self.modes:
                logging.debug(f"Executing processing for {mode}.")
                sanitized_mode = mode.replace(":", "_")
                result = self.execute_query(
                    mode, self.files, self.group_output, has_highway)
                # self.write_file(result, files['output'], self.output_printer)
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
                    self.mode_done.emit(mode)
                    continue
                # Prompt and wait for confirmation before overwriting
                if file_name.is_file():
                    self.overwrite_confirm.emit(str(file_name))
                    mutex.lock()
                    try:
                        # Don't check for a response until after the user has a chance to give one
                        waiting_for_input.wait(mutex)
                        if not self.response:
                            print(f"Skipping {mode}.")
                            continue
                    finally:
                        mutex.unlock()
                print(f"Writing {file_name}")
                try:
                    with file_name.open("w") as output_file:
                        self.output_printer.print_output(
                            output_file, sys.stderr, result)
                except OSError as e:
                    logging.error(str(e))
                    print("Write error")
                else:
                    if not result.data:
                        success_message = (f"{mode} has no change.")
                    else:
                        success_message = (
                            f"{mode} output with {len(result.data)} row")
                        if len(result.data) > 1:
                            success_message += "s"
                        success_message += "."
                    success_list.append(success_message)
                    # Logging q errors when try fails.
                    logging.debug(f"q_output details: {result}.")
                    logging.debug(
                        f"Processing for {mode} complete.")
                    print(f"{file_name} written.")
                    self.mode_done.emit(mode)
            # print(f"After run: {self.modes} with {type(self.modes)}.")
        finally:
            # print(f"End run: {self.modes} with {type(self.modes)}.")
            # print(f"Before clear: {self.modes} with {type(self.modes)}.")

            # Some tags failed
            if error_list:
                if len(error_list) == 1:
                    headline = "A tag could not be queried"
                    summary = error_list[0]
                else:
                    headline = "Tags could not be queried"
                    summary = "\n".join(error_list)
                if success_list:
                    headline = "Some tags could not be queried"
                    summary += "\nThe following tags completed successfully:\n"
                    summary += "\n".join(success_list)
                self.dialog_critical.emit(
                    headline, summary)
            # Nothing failed, everything suceeded
            elif success_list:
                summary = "All tags completed!\n"
                summary += "\n".join(success_list)
                self.dialog_information.emit("Success", summary)
            # Nothing succeeded and nothing failed, probably because user declined to overwrite
            else:
                self.dialog_information.emit("Nothing saved", "No files saved")
            self.modes.clear()
            # print(f"After clear: {self.modes} with {type(self.modes)}.")
            print(success_list)
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
        if group_output:
            # Generating temporary output files (max size 100 MB)
            tempf = tempfile.NamedTemporaryFile(
                mode='w', buffering=-1, encoding=None, newline=None,
                suffix=".csv", prefix=None, dir=None, delete=True)
            print(f"Writing to temp file.")
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
            logging.debug(f"Intermediate processing completed for {mode}.")
            print(f"Completed intermediate processing for {mode}.")

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
            logging.debug(
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
        logging.debug(f"Processing sql query: {sql}")
        return sql


class MainApp(QtWidgets.QMainWindow, QtGui.QKeyEvent, chameleon2.design.Ui_MainWindow):
    """

    Main PyQT window class that allows communication between UI and backend.
    Passes QMainWindow parameter to provide main application window, establish
    event handling with signal/slot connection.

    """
    # Sets up signal and var for pbar
    pbar_update = pyqtSignal()
    clear_search_box = pyqtSignal()
    # Declare progress bar var for values
    pbar_inc = 0

    def __init__(self, completer_list=None, parent=None):
        """
        Loads history file path, establish event handling with signal/slot
        connection.
        """
        super().__init__()
        self.setupUi(self)
        # Set up application logo on main window
        self.setWindowTitle("Chameleon 2")
        # Differentiate sys settings between pre and post-bundling
        if getattr(sys, 'frozen', False):
            logo = Path(sys._MEIPASS).parents[0].joinpath(
                sys._MEIPASS, "chameleonalpha.png")
            logo_path = str(Path.resolve(logo))
        else:
            logo = Path(__file__).parents[1].joinpath(
                "resources/chameleonalpha.png")
            logo_path = str(Path.resolve(logo))
        self.setWindowIcon(QtGui.QIcon(logo_path))
        self.logo = logo_path

        # Menu bar customization
        # Define Qactions for menu bar
        # About action for File menu
        info_action = QAction("&About Chameleon 2", self)
        info_action.setShortcut("Ctrl+I")
        info_action.setStatusTip('Software description.')
        info_action.triggered.connect(self.about_menu)
        # Exit action for File menu
        extract_action = QAction("&Exit Chameleon 2", self)
        extract_action.setShortcut("Ctrl+Q")
        extract_action.setStatusTip('Close application.')
        extract_action.triggered.connect(self.close)
        # Declare menu bar settings
        main_menu = self.menuBar()
        file_menu = main_menu.addMenu('&File')
        file_menu.addAction(info_action)
        file_menu.addAction(extract_action)

        # Logging initialization of Chameleon 2
        logging.info(f"Chameleon 2 started at {datetime.now()}.")

        # Sets run button to not enabled
        self.run_checker()
        # OSM tag resource file, construct list from file
        # Differentiate sys settings between pre and post-bundling
        if getattr(sys, 'frozen', False):
            ftl = Path(sys._MEIPASS).parents[0].joinpath(
                sys._MEIPASS, "data/OSMtag.yaml")
            # Debug Codeblock
            # frozen = 'not'
            # bundle_dir = sys._MEIPASS
            # print( 'we are',frozen,'frozen')
            # print( 'bundle dir is', bundle_dir )
            # print( 'sys.argv[0] is', sys.argv[0] )
            # print( 'sys.executable is', sys.executable )
            # print( 'os.getcwd is', os.getcwd() )
        else:
            ftl = Path(__file__).parents[0].joinpath("OSMtag.yaml")
            # Debug Codeblock
            # frozen = 'not'
            # bundle_dir = os.path.dirname(os.path.abspath(__file__))
            # print( 'we are',frozen,'frozen')
            # print( 'bundle dir is', bundle_dir )
            # print( 'sys.argv[0] is', sys.argv[0] )
            # print( 'sys.executable is', sys.executable )
            # print( 'os.getcwd is', os.getcwd() )

        try:
            with ftl.open() as file:
                completer_list = yaml.safe_load(file)
                # Debug print(completer_list)
        except OSError as e:
            logging.error(f"Autocomplete intialization failed: {e}.")
            print("Couldn't load autocomplete file.")

        # Load in tags from external file
        if completer_list is None:
            completer_list = []
        self.auto_completer(completer_list)

        # YAML file loaders
        # Load file paths into boxes from previous session

        # Check for history file and load if exists
        try:
            self.history_loader(HISTORY_LOCATION, self.oldFileNameBox,
                                self.newFileNameBox, self.outputFileNameBox)
        # If file doesn't exist, fail silently
        except FileNotFoundError:
            logging.error(f"History file could not be found.")
        except PermissionError:
            logging.error(f"History file found but not readable.")

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
        self.box_text = {
            self.oldFileSelectButton: "old",
            self.newFileSelectButton: "new"
        }
        # Define which button controls which filename box
        self.box_controls = {
            self.oldFileSelectButton: self.oldFileNameBox,
            self.newFileSelectButton: self.newFileNameBox
        }

    def about_menu(self, path: str):
        """
        Handles about page information.

        Parameters
        ----------
        path: str
            File path to application logo
        """
        logo = QtGui.QIcon(QtGui.QPixmap(self.logo))
        about = QMessageBox(self, icon=logo, textFormat=QtCore.Qt.RichText)
        about.setWindowTitle("About Chameleon 2")
        about.setIconPixmap(QtGui.QPixmap(
            self.logo).scaled(160, 160, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        about.setText('''
                    <h2><center>Chameleon 2</center></h2>
                    <p>This application compares two Overpass API CSV datasets
                    and returns an output of the differences between the snapshots.</p>
                    <p>Product of <a href="http://kaartgroup.com/">Kaart</a> made by SeaKaart tools team.<br>
                    Licensed under <a href="https://choosealicense.com/licenses/gpl-3.0/">GPL3</a>.</p>''')
        about.setInformativeText(
            "<i>Credits: <a href=https://github.com/harelba/q>q</a>, "
            "<a href=https://github.com/ActiveState/appdirs>appdir</a>, "
            "<a href=https://yaml.readthedocs.io/en/latest>yaml</a>, "
            "and <a href=https://www.pyinstaller.org>pyinstaller</a>.</i>")
        about.show()

    @staticmethod
    def history_loader(history_path: Path, old_box: QtWidgets.QLineEdit,
                       new_box: QtWidgets.QLineEdit, output_box: QtWidgets.QLineEdit):
        """
        Loads previous entries from YAML file and loads into selected fields

        Parameters:
        -----------
        history_path : Path
            File to load history from
        old_box : QLineEdit
            Field for the location of old data
        new_box : QLineEdit
            Field for the location of new date
        output_box : QLineEdit
            Field for the output file location prefix
        """
        with history_path.open('r') as file:
            loaded = yaml.safe_load(file)
            if isinstance(loaded, dict):
                old_box.insert(loaded.get('old', ''))
                new_box.insert(loaded.get('new', ''))
                output_box.insert(loaded.get('output', ''))

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
        set_list = []
        # We use these when there aren't enough favorites
        default_tags = ['highway', 'name', 'ref',
                        'addr:housenumber', 'addr:street']
        # Holds our place as we step through the list above
        def_index = 0
        # Assume no favorites until the file is loaded
        fav_list_length = 0
        # Check for favorite file and load if exists
        try:
            with favorite_path.open('r') as favorite_read:
                # Load in popular tags from history file
                # Default values are taken if history file does not exist
                fav_list = yaml.safe_load(favorite_read)  # dict()
        except FileNotFoundError as e:
            logging.error(e)
            print("favorites.yaml could not be found")
        except PermissionError as e:
            logging.error(e)
            print("favorites.yaml could not be opened")

        else:  # Don't bother doing anything with favorites if the file couldn't be read
            logging.info(
                f"Fav history is: {fav_list} with type: {type(fav_list)}.")
            print(
                f"Fav history is: {fav_list} with type: {type(fav_list)}.")
            fav_list_length = len(fav_list)
            for i in range(0, fav_list_length):
                set_list.append(fav_list[i])
        # If we run out of favorites, start adding non-redundant default tags
        if fav_list_length < 5:
            # Start where we left off with favorites, stop before we run out of buttons to populate
            for i in range((fav_list_length), (len(fav_btn) + 1)):
                # Loop through default_tags until we get a non-redundant value
                while len(set_list) < i:
                    # If the selected tag is not already a favorite, use it
                    if default_tags[def_index] not in set_list:
                        set_list.append(default_tags[def_index])
                    # Either way, move on the the next tag in the defaults list
                    def_index += 1
        # Loop through the buttons and apply our ordered tag values
        for btn in fav_btn:
            try:
                # The fav_btn and set_lists should have a 1:1 correspondence
                btn.setText(set_list[fav_btn.index(btn)])
            # Capture errors from the set_list not being created properly
            except IndexError as e:
                logging.error(f"{e}. Index {fav_btn.index(btn)} of fav_btn doesn't exist! "
                              f"Attempted to insert from{set_list}.")
                raise IndexError(f"Index {fav_btn.index(btn)} of fav_btn doesn't exist! "
                                 f"Attempted to insert from{set_list}.") from e

    def auto_completer(self, tags: list):
        """
        Autocompletion of user searches in searchBox.
        Utilizes resource file for associated autocomplete options.
        """
        # Needs to have tags reference a resource file of OSM tags
        # Check current autocomplete list
        logging.info(
            f"A total of {len(tags)} tags was added to auto-complete.")
        print(f"A total of {len(tags)} tags was added to auto-complete.")
        completer = QCompleter(tags)
        self.searchBox.setCompleter(completer)

    def add_tag(self):
        """
        Adds user defined tags into processing list on QListWidget.
        """
        if self.sender() is self.searchButton:
            # Value was typed by user
            label = self.searchBox.text()
            if not label or not label.strip():  # Don't accept whitespace-only values
                print('No value entered.')
                return
        elif self.sender() in self.fav_btn:
            # Value was clicked from fav btn
            label = self.sender().text()
        # Identifies sender signal and grabs button text
        # var to check listWidget items
        current_list = self.list_sender()
        # Add item to list only if condition passes
        if label in current_list:
            self.listWidget.item(current_list.index(label)).setSelected(True)
            print('Please enter an unique tag.')
        else:
            self.listWidget.addItem(label)
            print('Adding to list: ' + label)
        self.clear_search_box.emit()
        self.run_checker()
        self.listWidget.repaint()

    def delete_tag(self):
        """
        Clears individual list items with "Delete" button.
        Execute on `Delete` button signal.
        """
        try:
            cur_row = self.listWidget.currentRow()
            del_tag = self.listWidget.currentItem().text()
            self.listWidget.takeItem(cur_row)
            print(f"Deleted {del_tag} from processing list.")
            self.run_checker()
        # Fails silently if nothing is selected
        except AttributeError:
            logging.error(f"{AttributeError}.")
        self.listWidget.repaint()

    def clear_tag(self):
        """
        Wipes all tags listed on QList with "Clear" button.
        Execute on `Clear` button signal.
        """
        self.listWidget.clear()
        print('Cleared tag list.')
        self.run_checker()
        self.listWidget.repaint()

    def list_sender(self) -> list:
        """
        Sends user-defined list as sets for backend processing.
        Executes on `Run` operations.
        """
        tag_list = []
        for i in range(self.listWidget.count()):
            tag_list.append(self.listWidget.item(i).text())
        return tag_list

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
            with counter_location.open('r') as file:
                cur_counter = OrderedDict(yaml.load(file))
                print(f"counter.yaml history: {cur_counter}.")
        # If file doesn't exist, fail silently
        except OSError as e:
            logging.error(e)

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
            with counter_location.open('w') as file:
                yaml.dump(dict(sorted_counter), file)
                print(f"counter.yaml dump with: {sorted_counter}.")
        except OSError as e:
            logging.error(e)
            print("Couldn't write counter file.")
        # Saving favorite tags to config directory
        try:
            with favorite_location.open('w') as file:
                yaml.dump(rank_tags, file)
                print(f"favorites.yaml dump with: {rank_tags}.")
        # If file doesn't exist, fail silently
        except OSError as e:
            logging.error(e)
            print("Couldn't write favorite file.")

    def open_input_file(self):
        """
        Adds functionality to the Open Old/New File (...) button, opens the
        '/downloads' system path to find csv file.
        """
        sender = self.sender()
        destination = self.box_controls[sender]
        if re.match("\\S+", destination.text()):
            file_dir = destination.text()
        # If the target box is empty, look for a value in each of the boxes
        elif re.match("\\S+", self.oldFileNameBox.text()):
            file_dir = self.oldFileNameBox.text()
        elif re.match("\\S+", self.newFileNameBox.text()):
            file_dir = self.newFileNameBox.text()
        # If no previous location, default to Downloads folder
        else:
            file_dir = os.path.expanduser("~/Downloads")
        file_name, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, f"Select CSV file with {self.box_text[sender]} data", file_dir, "CSV (*.csv)")
        if file_name:  # Clear the box before adding the new path
            destination.clear()
            destination.insert(file_name)

    def output_file(self):
        """
        Adds functionality to the Output File (...) button, opens the
        '/downloads' system path for user to name an output file.
        """
        if re.match("\\S+", self.outputFileNameBox.text()):
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
            self.runButton.setEnabled(1)
        else:
            self.runButton.setEnabled(0)
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
        # Load field values into dict
        files = {
            'old': self.oldFileNameBox.text(),
            'new': self.newFileNameBox.text(),
            'output': self.outputFileNameBox.text()
        }
        # Check for blank values
        for k, v in files.items():
            if not v:
                self.dialog_critical(
                    f"{str.title(k)} file field is blank.",
                    "Please enter a value"
                )
                return
        # Check for spaces in file names
        space_expression = re.compile("^\\S+\\s+\\S+$")
        if space_expression.match(files['old']) or \
           space_expression.match(files['new']) or \
           space_expression.match(files['output']):
            # Popup here
            self.dialog_critical(
                "Chameleon cannot use files or folders with spaces in their names.",
                "Please rename your files and/or folders to remove spaces.")
            return
        # Wrap the file references in Path object to prepare "file not found" warning
        old_file_path = Path(files['old'])
        new_file_path = Path(files['new'])
        output_file_path = Path(files['output'])
        # Check if either old or new file/directory exists. If not, notify user.
        if not old_file_path.is_file() or not new_file_path.is_file():
            if not old_file_path.is_file() and not new_file_path.is_file():
                self.dialog_critical("File or directories not found!", "")
            elif not old_file_path.is_file():
                self.dialog_critical(
                    "Old file or directory not found!", "")
            elif not new_file_path.is_file():
                self.dialog_critical(
                    "New file or directory not found!", "")
            return
        # Check if output directory is writable
        try:
            if not os.access(output_file_path.parents[0], os.W_OK):
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
        logging.info(f"Modes to be processed: {modes}.")
        print(f"Modes to be processed: {modes}.")
        group_output = self.groupingCheckBox.isChecked()

        # instantiate progress bar class
        self.pbar_inc = 0
        self.progress_bar = ProgressBar()
        # show progress bar
        self.progress_bar.show()
        self.pbar_update.connect(self.progbar_handler)
        # Handles Worker class and QThreads for Worker
        self.work_thread = QThread()
        self.worker = Worker(modes, files, group_output)
        # Connect to progbar_counter() when 1 mode is done in Worker
        self.worker.mode_done.connect(self.progbar_counter)
        # Connect to finished() when all modes are done in Worker
        self.worker.done.connect(self.finished)
        # Connect signal from Worker to handle overwriting files
        self.worker.overwrite_confirm.connect(self.overwrite_message)
        self.worker.dialog_critical.connect(self.dialog_critical)
        self.worker.dialog_information.connect(self.dialog_information)
        self.worker.moveToThread(self.work_thread)
        self.work_thread.started.connect(self.worker.run)
        self.work_thread.start()

        # instantiate progress bar class
        # self.progress_bar = ProgressBar()
        # show progress bar
        # self.progress_bar.show()
        # for i in range(1, 100):
        # time.sleep(0.01)
        # self.progress_bar.set_value(((i + 1) / 100) * 100)
        # QApplication.processEvents()

    def progbar_counter(self, mode: str):
        """
        Tracker for completion of individual modes in Worker class.

        Parameters
        ----------
        mode : str
            str returned from mode_done.emit()
        """
        print(f"mode_done signal -> caught mode: {mode}.")
        if mode:
            # Advance index of modes by 1
            self.pbar_inc += 1
            print(f'returning True singal. pbar_inc is now {self.pbar_inc}.')
            self.pbar_update.emit()
        else:
            # print('returning False signal.')
            pass

    def progbar_handler(self):
        """
        Handles progression of progress bar in a smooth manner.
        """
        # Grabs the index of mode from modes
        pbar_inc = self.pbar_inc
        tot = len(self.list_sender())
        print(f"Tot is {tot}.")
        # Which % should the bar start at
        pbar_step = int(abs(((pbar_inc - 1) / tot) * 100))
        # Which % should the bar stop at
        pbar_stop = int((pbar_inc / tot) * 100)
        # Fixed % that the bar should move by based on modes
        inc = int((1 / tot) * 100)
        print(
            f'before pbar update, pbar_stop is {pbar_stop} and pbar_step is {pbar_step}.')
        self.progress_bar.set_value(pbar_step)
        print(f'pbar starting at {pbar_step}.')
        # Smoother increments for progress bar
        for pixel in range(inc):
            time.sleep(0.001)
            self.progress_bar.set_value(int(pbar_step + pixel / 100 * 100))
            self.progress_bar.repaint()
            QApplication.processEvents()
        print(f'progbar ends at {pbar_stop} and steps through {inc}')

    def enter_key_event(self, event):
        """
        Allows 'Return' or 'Enter' on keyboard to be pressed in lieu of
        clicking run button.

        Parameters
        ----------
        event : class
            Event which handles keystroke input
        """

        if self.runButton.isEnabled():
            if event.key() == QtCore.Qt.Key_Return:
                MainApp.run_query(self)

        # Added delete key to an action (WIP)
        if event.key() == QtCore.Qt.Key_Delete:
            print('Delete key pressed...')
            self.delete_tag()

    # Re-enable run button when function complete
    def finished(self):
        """
        Helper method finalizes run process: re-enable run button
        and notify user of run process completion.
        """
        # close the progress bar
        self.progress_bar._reset()
        self.progress_bar.close()
        # self.progress_bar = None
        # Quits work_thread and reset
        # Needs worker logging
        self.work_thread.quit()
        self.work_thread.wait()
        self.worker = None
        self.work_thread = None
        # Logging processing completion
        logging.info(f"All Chameleon 2 analysis processing completed.")
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
            self, '', f"{file_name} exists. Do you want to overwrite?",
            overwrite_prompt.No | overwrite_prompt.Yes)
        if overwrite_prompt_response == overwrite_prompt.No:
            self.worker.response = False
        elif overwrite_prompt_response == overwrite_prompt.Yes:
            self.worker.response = True
        waiting_for_input.wakeAll()

# Override closeEvent method from QWidget; for assigning custom closeEvent

# Trial 1
# def closeEvent(self, event):
#     if can_exit:
#         print("Chameleon 2 closed.")
#         event.accept()
#     else:
#         print("Closing ignored.")
#         event.ignore()

# Trial 2
# def closeEvent(self, event):
#     quit_msg = "Are you sure you want to exit the program?"
#     reply = QtGui.QMessageBox.question(self, 'Message',
#                     quit_msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
#     if self._want_to_close and reply == QtGui.QMessageBox.Yes:
#         event.accept()
#         super(MainApp, self).closeEvent(event)
#     else:
#         event.ignore()
#         self.setWindowState(QtCore.Qt.WindowMinimized)


def main():
    """
    Creates a new instance of the QtWidget application, sets the form to be
    out MainWIndow (design) and executes the application.
    """
    app = QtWidgets.QApplication(sys.argv)
    # Enable High DPI display with PyQt5
    QtWidgets.QApplication.setAttribute(
        QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    form = MainApp()
    form.show()
    # app.aboutToQuit.connect(form.closeEvent(event)) # callable innate to PyQt (Trial 1)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
