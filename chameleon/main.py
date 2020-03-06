#!/usr/bin/env python3
"""
Opens a window with fields for input and selectors, which in turn opens
a worker object to process the input files with `q` and create output
in .csv format.
"""
import errno
import logging
import os
import shlex
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import oyaml as yaml
import pandas as pd
import requests
# Finds the right place to save config and log files on each OS
from appdirs import user_config_dir, user_log_dir
from lxml import etree
from PyQt5 import QtCore, QtGui, QtWidgets
# from PyQt5.QtGui import QKeyEvent
from PyQt5.QtCore import QObject, QThread
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtWidgets import (QAction, QApplication, QCompleter, QMessageBox,
                             QProgressDialog)

# Import generated UI file
from chameleon import design
from chameleon.core import ChameleonDataFrame, ChameleonDataFrameSet

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
    # __file__.parent is chameleon, .parents[1] is chameleon-2
    RESOURCES_DIR = Path(__file__).parents[1] / "resources"

logger = logging.getLogger()

try:
    with (RESOURCES_DIR / 'version.txt').open('r') as version_file:
        APP_VERSION = version_file.read()
except OSError:
    APP_VERSION = ''
    logger.warning("No version number detected")


def logger_setup(log_dir: Path):
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Setup console logging output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    # Setup file logging output
    # Generate log file directory
    if not log_dir.is_dir():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            if e.errno != errno.EEXIST:
                logger.error("Cannot create log directory.")
    if log_dir.is_dir():
        try:
            # Initialize Worker class logging
            log_path = str(log_dir / f"Chameleon_{datetime.now().date()}.log")
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            logger.error("Log file could not be generated at %s.", log_path)
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
                        logger.info("removing...%s", str(f))
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
    logger.debug('VSCode debug library successful.')


class Worker(QObject):
    """

    Worker class, code inside slot should execute in a separate thread.
    Displays file paths, executes comparison function, writes and saves file.

    """
    done = Signal()
    mode_start = Signal(str)
    mode_complete = Signal()
    scale_with_api_items = Signal(int)
    increment_progbar_api = Signal()
    overwrite_confirm = Signal(str)
    dialog = Signal(str, str, str)

    def __init__(self, parent, modes: set, files: dict, group_output=False,
                 use_api=False, file_format='csv'):
        super().__init__()
        # Define set of selected modes
        self.modes = modes
        self.files = files
        self.group_output = group_output
        self.use_api = use_api
        self.parent = parent
        self.response = None
        self.format = file_format
        self.deleted_way_members = {}
        self.overpass_result_attribs = {}
        self.error_list = []
        self.successful_items = {}

    @Slot()
    def run(self):
        """
        Runs when thread started, saves history to file and calls other functions to write files.
        """
        # For debugging in VSCode only
        try:
            ptvsd.debug_this_thread()
        except (ModuleNotFoundError, NameError):
            logger.debug('Worker thread not exposed to VSCode')
        else:
            logger.debug('Worker thread successfully exposed to debugger.')
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
        # print(f"Before run: {self.modes} with {type(self.modes)}.")
        try:
            mode = None
            dataframe_set = ChameleonDataFrameSet(
                self.files['old'], self.files['new'], use_api=self.use_api)
            if self.use_api:
                self.check_api_deletions(dataframe_set.source_data)
                dataframe_set.separate_special_dfs()
            for mode in self.modes:
                logger.debug("Executing processing for %s.", (mode))
                self.mode_start.emit(mode)
                # sanitized_mode = mode.replace(":", "_")
                try:
                    result = ChameleonDataFrame(dataframe_set.source_data,
                                                mode=mode,
                                                grouping=self.group_output).query()
                except KeyError as e:
                    # File reading failed, usually because a nonexistent column
                    logger.exception(e)
                    self.error_list += mode
                    continue
                dataframe_set[mode] = result
            if self.format == 'csv':
                self.write_csv(dataframe_set)
            elif self.format == 'excel':
                self.write_excel(dataframe_set)
            # print(f"After run: {self.modes} with {type(self.modes)}.")
        finally:
            # print(f"End run: {self.modes} with {type(self.modes)}.")
            # print(f"Before clear: {self.modes} with {type(self.modes)}.")

            # If any modes aren't in either list,
            # the process was cancelled before they could be completed
            cancelled_list = self.modes.difference(
                set(self.error_list) | set(self.successful_items.keys()))
            dialog_icon = 'information'
            if self.error_list:  # Some tags failed
                dialog_icon = 'critical'
                if len(self.error_list) == 1:
                    headline = "A tag could not be queried"
                    summary = self.error_list[0]
                else:
                    headline = "Tags could not be queried"
                    summary = "\n".join(self.error_list)
                if self.successful_items:
                    headline = "Some tags could not be queried"
                    summary += "\nThe following tags completed successfully:\n"
                    summary += "\n".join(list(self.successful_items.values()))
            elif self.successful_items:  # Nothing failed, everything suceeded
                headline = "Success"
                summary = "All tags completed!\n"
                summary += "\n".join(list(self.successful_items.values()))
            # Nothing succeeded and nothing failed, probably because user declined to overwrite
            else:
                headline = "Nothing saved"
                summary = "No files saved"
            if cancelled_list:
                summary += '\nThe process was cancelled before the following tags completed:\n'
                summary += '\n'.join(cancelled_list)
            self.dialog.emit(headline, summary, dialog_icon)
            self.modes.clear()
            logger.info(list(self.successful_items.values()))
            # Signal the main thread that this thread is complete
            self.done.emit()

    def history_writer(self):
        staged_history_dict = {k: str(v)
                               for k, v in self.files.items()}
        staged_history_dict['use_api'] = self.use_api
        staged_history_dict['file_format'] = self.format
        try:
            with HISTORY_LOCATION.open('w') as history_file:
                yaml.dump(staged_history_dict, history_file)
        except OSError:
            logger.exception("Couldn't write history.yaml.")
        else:
            # In some rare cases (like testing) MainApp may not exist
            try:
                self.parent.history_dict = staged_history_dict
            except NameError:
                pass

    def write_csv(self, dataframe_set: ChameleonDataFrameSet):
        for mode, result in dataframe_set.items():
            row_count = len(result)
            file_name = Path(
                f"{self.files['output']}_{mode}.csv")
            logger.info("Writing %s", (file_name))
            try:
                with file_name.open('x') as output_file:
                    result.to_csv(output_file, sep='\t', index=False)
            except FileExistsError:
                # Prompt and wait for confirmation before overwriting
                try:  # This block ensures the mutex is unlocked even in the worst case
                    self.overwrite_confirm.emit(str(file_name))
                    self.parent.mutex.lock()
                    # Don't check for a response until after the user has a chance to give one
                    self.parent.waiting_for_input.wait(
                        self.parent.mutex)
                    if not self.response:
                        logger.info("Skipping %s.", (mode))
                        continue
                    else:
                        with file_name.open('w') as output_file:
                            result.to_csv(
                                output_file, sep='\t', index=False)
                finally:
                    self.parent.mutex.unlock()
            except OSError:
                logger.exception("Write error.")
                self.error_list += mode
                continue
            if not row_count:
                # Empty dataframe
                success_message = (f"{mode} has no change.")
            else:
                # Exclude the header row from the row count
                s = ''
                if row_count > 1:
                    s = 's'
                success_message = (
                    f"{mode} output with {row_count} row{s}.")
            self.successful_items.update({mode: success_message})
            logger.info(
                "Processing for %s complete. %s written.", mode, file_name)
            self.mode_complete.emit()

    def write_excel(self, dataframe_set: ChameleonDataFrameSet):
        file_name = Path(f"{self.files['output']}.xlsx")
        if file_name.is_file():
            self.overwrite_confirm.emit(str(file_name))
            self.parent.mutex.lock()
            # Don't check for a response until after the user has a chance to give one
            self.parent.waiting_for_input.wait(
                self.parent.mutex)
            if not self.response:
                logger.info("Not writing output")
                return
        with pd.ExcelWriter(file_name) as writer:
            for mode, result in dataframe_set.items():
                row_count = len(result)
                result.to_excel(writer, sheet_name=mode, index=False)
                if not row_count:
                    # Empty dataframe
                    success_message = (f"{mode} has no change.")
                else:
                    s = ''
                    if row_count > 1:
                        s = 's'
                    success_message = (
                        f"{mode} output with {row_count} row{s}.")
                self.successful_items.update({mode: success_message})

    def write_geojson(self):
        # Placeholder for future development
        pass

    def check_api_deletions(self, df: pd.DataFrame):
        # How long to wait between API calls
        request_interval = 1
        if APP_VERSION:
            formatted_app_version = f" {APP_VERSION}"
        else:
            formatted_app_version = ''
        deleted_ids = list((df.loc[df['action'] == 'deleted']).index)
        self.scale_with_api_items.emit(len(deleted_ids))
        # TODO Add while loop to allow for early cancel
        # For use in split/merge detection
        for feature_id in deleted_ids:
            self.increment_progbar_api.emit()
            if feature_id in self.overpass_result_attribs:
                element_attribs = self.overpass_result_attribs[feature_id]
            else:
                try:
                    r = requests.get(
                        f'https://www.openstreetmap.org/api/0.6/way/{feature_id}/history', timeout=2,
                        headers={'user-agent': f'Kaart Chameleon{formatted_app_version}'})
                    r.raise_for_status()
                except ConnectionError as e:
                    # Couldn't contact the server, could be client-side
                    logger.exception(e)
                    continue
                except r.HTTPError:
                    if str(r.status_code) == '429':
                        retry_after = r.headers.get('retry-after', '')

                        logger.error(
                            "The OSM server says you've made too many requests."
                            "You can retry after %s seconds.", retry_after)
                        break
                    else:
                        logger.error(
                            'Server replied with a %s error', r.status_code)
                    continue
                except etree.XMLSyntaxError:
                    logger.error(
                        'No OSM feature recieved for id %s.', feature_id)
                    continue
                else:
                    root = etree.fromstring(r.content)
                    # TODO Generalize for nodes and relations
                    latest_version = root.findall(f"way")[-1]
                    element_attribs = {
                        'user_new': latest_version.attrib['user'],
                        'changeset_new': latest_version.attrib['changeset'],
                        'version_new': latest_version.attrib['version'],
                        'timestamp_new': latest_version.attrib['timestamp']
                    }

                    if latest_version.attrib['visible'] == "false":
                        # The most recent way version has the way deleted
                        # element_attribs.update({
                        #     'url': ''
                        # })
                        prior_version_num = str(
                            int(element_attribs['version_new']) - 1)
                        prior_version = root.find(
                            f"way[@version=\"{prior_version_num}\"]")
                        member_nodes = [int(el.attrib['ref'])
                                        for el in prior_version.findall("nd")]
                        # Save last members of the deleted way
                        # for later use in detecting splits/merges
                        self.deleted_way_members[feature_id] = member_nodes
                    elif latest_version.attrib['visible'] == 'true':
                        # The way was not deleted, just dropped from the latter dataset
                        element_attribs.update({
                            'action': 'dropped'
                        })
                    self.overpass_result_attribs[feature_id] = element_attribs

            for attribute, value in element_attribs.items():
                df.at[feature_id, attribute] = value
                pass

            # Wait between iterations to avoid ratelimit problems
            time.sleep(request_interval)

    # def stop(self):
    #     self._isRunning = False


class MainApp(QtWidgets.QMainWindow, QtGui.QKeyEvent, design.Ui_MainWindow):
    """

    Main PyQT window class that allows communication between UI and backend.
    Passes QMainWindow parameter to provide main application window, establish
    event handling with signal/slot connection.

    """
    clear_search_box = Signal()

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
        self.mutex = QtCore.QMutex()
        self.waiting_for_input = QtCore.QWaitCondition()

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
        logger.info("Chameleon started at %s.", (datetime.now()))

        # Sets run button to not enabled
        self.run_checker()
        # OSM tag resource file, construct list from file
        autocomplete_source = RESOURCES_DIR / "OSMtag.yaml"

        try:
            with autocomplete_source.open() as read_file:
                self.auto_completer(yaml.safe_load(read_file))
        except OSError:
            logger.exception("Couldn't read the autocomplete source file.")
        except (TypeError, NameError):
            logger.exception("Could not load any autocomplete tags.")

        # YAML file loaders
        # Load file paths into boxes from previous session

        self.history_loader()

        # List all of our buttons to populate so we can iterate through them
        self.fav_btn = [self.popTag1, self.popTag2,
                        self.popTag3, self.popTag4, self.popTag5]

        # Populate the buttons defined above
        self.fav_btn_populate()

        # Connecting signals to slots within init
        self.oldFileSelectButton.clicked.connect(self.open_input_file)
        self.newFileSelectButton.clicked.connect(self.open_input_file)
        self.outputFileSelectButton.clicked.connect(self.output_file)
        # Changes the displayed file name template depending on the selected file format
        self.excelRadio.clicked.connect(self.suffix_updater)
        self.csvRadio.clicked.connect(self.suffix_updater)
        self.runButton.clicked.connect(self.run_query)
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
        """
        logo = QtGui.QIcon(QtGui.QPixmap(self.logo))

        if APP_VERSION:
            formatted_version = f"<p><center>Version {APP_VERSION}</center></p>"
        else:
            formatted_version = ''
        about = QMessageBox(self, icon=logo, textFormat=QtCore.Qt.RichText)
        about.setWindowTitle("About Chameleon")
        about.setIconPixmap(QtGui.QPixmap(
            self.logo).scaled(160, 160, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        about.setText(
            f"<h2><center>Chameleon</center></h2>{formatted_version}"
            "<p>This application compares OSM snapshot data from "
            "<a href=\"https://overpass-turbo.eu/\">Overpass Turbo</a> "
            "and returns an output of changes that occurred between the snapshots.</p>"
            "<p>Made by <a href=\"http://kaartgroup.com/\">Kaart</a>'s development team.<br>"
            "Licensed under <a href=\"https://choosealicense.com/licenses/gpl-3.0/\">GPL3</a>.</p>")
        about.setInformativeText(
            "<i>Powered by: "
            "<a href=https://www.riverbankcomputing.com/software/pyqt/download5>PyQt5</a>, "
            "<a href=https://pandas.pydata.org>pandas</a>, "
            "<a href=https://github.com/ActiveState/appdirs>appdir</a>, "
            "<a href=https://github.com/wimglenn/oyaml>oyaml</a>, "
            "and <a href=https://www.pyinstaller.org>PyInstaller</a>.</i>")
        about.show()

    def auto_completer(self, tags: list):
        """
        Autocompletion of user searches in searchBox.
        Utilizes resource file for associated autocomplete options.
        """
        # Needs to have tags reference a resource file of OSM tags
        # Check current autocomplete list
        logger.debug(
            "A total of %s tags was added to auto-complete.", len(tags))
        completer = QCompleter(tags)
        self.searchBox.setCompleter(completer)

    def history_loader(self):
        # Check for history file and load if exists
        self.history_dict = {}
        try:
            with HISTORY_LOCATION.open('r') as history_file:
                self.history_dict = yaml.safe_load(history_file)
            for k, v in self.text_fields.items():
                v.insert(self.history_dict.get(k, ''))
            self.offlineRadio.setChecked(
                ~self.history_dict.get('use_api', True))
            if self.history_dict.get('file_format', 'csv') == 'excel':
                self.excelRadio.setChecked(True)
        # If file doesn't exist, fail silently
        except FileNotFoundError:
            logger.warning(
                "History file could not be found. "
                "This is normal when running the program for the first time.")
        except PermissionError:
            logger.exception("History file found but not readable.")
        except AttributeError:
            logger.exception()

    def fav_btn_populate(self, favorite_location: Path = FAVORITE_LOCATION):
        """
        Populates the listed buttons with favorites from the given file
        """
        # Holds the button values until they are inserted
        fav_list = []
        # Check for favorite file and load if exists
        try:
            with favorite_location.open('r') as favorite_read:
                # Load in popular tags from history file
                # Default values are taken if history file does not exist
                fav_list = yaml.safe_load(favorite_read)  # dict()
        except FileNotFoundError:
            logger.warning("favorites.yaml could not be found. "
                           "This is normal when running the program for the first time.")
        except PermissionError:
            logger.exception("favorites.yaml found but could not be opened.")
        else:  # Don't bother doing anything with favorites if the file couldn't be read
            logger.debug(
                f"Fav history is: {fav_list} with type: {type(fav_list)}.")
        if len(fav_list) < len(self.fav_btn):
            # If we run out of favorites, start adding non-redundant default tags
            # We use these when there aren't enough favorites
            default_tags = ['highway', 'name', 'ref',
                            'addr:housenumber', 'addr:street']
            # Count how many def tags are needed
            def_count = len(self.fav_btn) - len(fav_list)
            # Add requisite number of non-redundant tags from the default list
            fav_list += [i for i in default_tags
                         if i not in fav_list][:def_count]
        # Loop through the buttons and apply our ordered tag values
        for index, btn in enumerate(self.fav_btn):
            try:
                # The fav_btn and set_lists should have a 1:1 correspondence
                btn.setText(fav_list[index])
            # Capture errors from the set_list not being created properly
            except IndexError as e:
                logger.exception(
                    "Index %s of fav_btn doesn't exist! Attempted to insert from %s.",
                    index, fav_list)
                raise IndexError(f"Index {index} of fav_btn doesn't exist! "
                                 f"Attempted to insert from{fav_list}.") from e

    def add_tag(self):
        """
        Adds user defined tags into processing list on QListWidget.
        """
        # Identifies sender signal and grabs button text
        if self.sender() is self.searchButton:
            # Value was typed by user
            raw_label = self.searchBox.text()
            if not raw_label.strip():  # Don't accept whitespace-only values
                logger.warning('No value entered.')
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
                if i == 0:  # Clear the prior selection on the first iteration only
                    self.listWidget.selectionModel().clear()
                # existing_item should never have more than 1 member
                existing_item[0].setSelected(True)
                logger.warning('%s is already in the list.', label)
            else:
                self.listWidget.addItem(label)
                logger.info('Adding to list: %s', label)
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
                logger.info("Deleted %s from processing list.", (item.text()))
            self.run_checker()
        # Fails silently if nothing is selected
        except AttributeError:
            logger.exception()
        self.listWidget.repaint()

    def clear_tag(self):
        """
        Wipes all tags listed on QList with "Clear" button.
        Execute on `Clear` button signal.
        """
        self.listWidget.clear()
        logger.info('Cleared tag list.')
        self.run_checker()
        self.listWidget.repaint()

    @staticmethod
    def document_tag(run_tags: set, counter_location: Path = COUNTER_LOCATION,
                     favorite_location: Path = FAVORITE_LOCATION):
        """
        Python counter for tags that are frequently chosen by user.
        Document counter and favorites using yaml file storage.
        Function parses counter.yaml and dump into favorites.yaml.
        """
        cur_counter = dict()
        # Parse counter.yaml for user tag preference
        try:
            with counter_location.open('r') as counter_read:
                cur_counter = dict(yaml.load(counter_read))
                logger.debug("counter.yaml history: %s.", (cur_counter))
        # If file doesn't exist, fail silently
        except FileNotFoundError:
            logger.warning("Couldn't read the tag count file. "
                           "This is normal if this is your first time runnning the application.")
        except OSError:
            logger.exception()

        # Casting set into dictionary with counts
        # Counter() sorts in reverse order (highest first)
        # Counter() generates a counter collections object
        dict_counter = dict(Counter(run_tags))
        # Combining history counter with new counter
        sum_counter = dict(Counter(dict_counter) + Counter(cur_counter))
        # Sorting counter collections into ordered dictionary
        sorted_counter = dict(sorted(sum_counter.items(),
                                     key=lambda x: x[1], reverse=True))
        rank_tags = list(sorted_counter.keys())
        # Saving tag counts to config directory
        try:
            with counter_location.open('w') as counter_write:
                yaml.dump(dict(sorted_counter), counter_write)
                logger.info(f"counter.yaml dump with: {sorted_counter}.")
        except OSError:
            logger.exception("Couldn't write counter file.")
        # Saving favorite tags to config directory
        try:
            with favorite_location.open('w') as favorite_write:
                yaml.dump(rank_tags, favorite_write)
                logger.info(f"favorites.yaml dump with: {rank_tags}.")
        # If file doesn't exist, fail silently
        except OSError:
            logger.exception("Couldn't write favorite file.")

    def open_input_file(self):
        """
        Adds functionality to the Open Old/New File (...) button, opens the
        '/downloads' system path to find csv file.
        """
        sender = self.sender()
        destination = sender.box_control
        # Gets first non-empty value in order
        file_dir = next(e for e in (
            destination.text().strip(),
            self.oldFileNameBox.text().strip(),
            self.newFileNameBox.text().strip(),
            os.path.expanduser("~/Downloads")
        ) if e)
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
        # If no previous location, default to Documents folder
        output_file_dir = next(e for e in (
            os.path.dirname(self.outputFileNameBox.text().strip()),
            os.path.expanduser("~/Documents")
        ) if e)
        output_file_name, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self, "Enter output file prefix", output_file_dir)
        if output_file_name:  # Clear the box before adding the new path
            # Since this is a prefix, the user shouldn't be adding their own extension
            output_file_name = output_file_name.replace('.csv', '')
            output_file_name = output_file_name.replace('.xls', '')
            output_file_name = output_file_name.replace('.xlsx', '')
            self.outputFileNameBox.clear()
            self.outputFileNameBox.insert(output_file_name)

    def run_checker(self):
        """
        Function that disable/enables run button based on list items.
        """
        list_not_empty = self.listWidget.count() > 0
        self.runButton.setEnabled(list_not_empty)
        self.repaint()

    @Slot()
    def suffix_updater(self):
        if self.excelRadio.isChecked():
            self.fileSuffix.setText('.xlsx')
        else:
            self.fileSuffix.setText(r'_{mode}.csv')
        self.repaint()

    @Slot(str, str, str)
    def dialog(self, text: str, info: str, icon: str):
        """
        Method to pop-up critical error box

        Parameters
        ----------
        text, info : str
            Optional error box text.
        """
        dialog = QMessageBox(self)
        dialog.setText(text)
        if icon == 'critical':
            dialog.setIcon(QMessageBox.Critical)
        else:
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
        for k, v in self.text_fields.items():
            if not v.text().strip():
                self.dialog(
                    f"{k.title()} file field is blank.",
                    'Please enter a value',
                    'critical'
                )
                return
        # Wrap the file references in Path object to prepare "file not found" warning
        file_paths = {k: Path(v.text())
                      for k, v in self.text_fields.items()}
        # Check if either old or new file/directory exists. If not, notify user.
        if not file_paths['old'].is_file() or not file_paths['new'].is_file():
            if not file_paths['old'].is_file() and not file_paths['new'].is_file():
                self.dialog('File or directories not found!', '', 'critical')
            elif not file_paths['old'].is_file():
                self.dialog(
                    'Old file or directory not found!', '', 'critical')
            elif not file_paths['new'].is_file():
                self.dialog(
                    'New file or directory not found!', '', 'critical')
            return
        # Check if output directory is writable
        try:
            if not os.access(file_paths['output'].parent, os.W_OK):
                self.dialog(
                    'Output directory not writeable!', '', 'critical')
                return
        except IndexError:
            # This shouldn't be reachable normally, but belt-and-suspenders...
            self.dialog(
                'Output file field is blank.',
                'Please enter a value.',
                'critical'
            )
            return
        # modes var needs to be type set()
        modes = {i.text() for i in self.listWidget.findItems(
            '*', QtCore.Qt.MatchWildcard)}
        self.document_tag(modes)  # Execute favorite tracking
        logger.info("Modes to be processed: %s.", (modes))
        group_output = self.groupingCheckBox.isChecked()
        # The offline radio button is a dummy. The online button functions as a checkbox
        # rather than as true radio buttons
        use_api = self.onlineRadio.isChecked()

        if self.excelRadio.isChecked():
            file_format = 'excel'
        else:
            file_format = 'csv'

        # Add one mode more that the length so that a full bar represents completion
        # When the final tag is started, the bar will show one increment remaining
        # Disables the system default close, minimize, maximuize buttons
        # First task of Worker is to check for highway tag in source files
        self.progress_bar = chameleonProgressDialog(len(modes), use_api)
        self.progress_bar.show()

        # Handles Worker class and QThreads for Worker
        self.work_thread = QThread(parent=self)
        self.worker = Worker(self, modes, file_paths,
                             group_output=group_output, use_api=use_api, file_format=file_format)
        # Connect to count_mode() when 1 mode begins in Worker
        self.worker.mode_start.connect(self.progress_bar.count_mode)
        self.worker.mode_complete.connect(self.progress_bar.mode_complete)
        self.worker.increment_progbar_api.connect(
            self.progress_bar.increment_progbar_api)
        self.worker.scale_with_api_items.connect(
            self.progress_bar.scale_with_api_items)
        self.progress_bar.canceled.connect(self.finished)
        # Connect to finished() when all modes are done in Worker
        self.worker.done.connect(self.finished)
        # Connect signal from Worker to handle overwriting files
        self.worker.overwrite_confirm.connect(self.overwrite_message)
        self.worker.dialog.connect(self.dialog)
        self.worker.moveToThread(self.work_thread)
        self.work_thread.started.connect(self.worker.run)
        self.work_thread.start()

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
        # self.worker.stop()
        self.work_thread.quit()
        self.work_thread.wait()
        # In theory this deletes the worker only when done
        self.worker.deleteLater()
        self.progress_bar.close()
        # Logging processing completion
        logger.info("All Chameleon analysis processing completed.")
        self.run_checker()

    @Slot(str)
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
        self.waiting_for_input.wakeAll()

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
        file_keys = {'old', 'new', 'output'}
        try:
            if {k: self.history_dict[k] for k in file_keys} != {k: files[k] for k in file_keys}:
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
            logger.warning("All Chameleon analysis processing completed.")


class chameleonProgressDialog(QProgressDialog):
    def __init__(self, length: int, use_api=False):
        self.length = length
        super().__init__('', 'Cancel', 0, self.length)
        self.mode_progress = 0
        self.use_api = use_api
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setLabelText('Beginning analysis...')
        self.setWindowFlags(
            QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.CustomizeWindowHint)

    @Slot(str)
    def count_mode(self, mode: str):
        """
        Tracker for completion of individual modes in Worker class.

        Parameters
        ----------
        mode : str
            str returned from mode_start.emit()
        """
        logger.info("mode_start signal -> caught mode: %s.", (mode))

        self.mode = mode
        if not self.use_api:
            self.setValue(self.mode_progress)
        self.label_text_base = f"Analyzing {mode} tag…"
        self.setLabelText(self.label_text_base)

    @Slot()
    def mode_complete(self):
        # Advance index of modes by 1
        self.mode_progress += 1

    @Slot(int)
    def scale_with_api_items(self, item_count: int):
        self.current_item = 0
        self.item_count = item_count
        scaled_value = self.mode_progress * self.item_count
        scaled_max = self.length * self.item_count
        self.setValue(scaled_value)
        self.setMaximum(scaled_max)

    @Slot()
    def increment_progbar_api(self):
        self.current_item += 1
        self.setValue(self.value() + 1)
        self.setLabelText(
            f"Checking deleted items on OSM server ({self.current_item} of {self.item_count})")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Enable High DPI display with PyQt5
    app.setAttribute(
        QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    form = MainApp()
    form.show()
    sys.exit(app.exec_())
