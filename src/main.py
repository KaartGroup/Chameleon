#!/usr/bin/env python3

import errno
import os
import os.path
import re
import sys
import tempfile
import time
from pathlib import Path

# Loads and saves settings to YAML
# from ruamel.yaml import YAML
import yaml
# Finds the right place to save config and log files on each OS
from appdirs import user_config_dir  # , user_log_dir
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QMessageBox

import src.design  # Import generated UI file
from src.ProgressBar import ProgressBar
# Does the processing
from src.q import QInputParams, QOutputParams, QOutputPrinter, QTextAsData

# Required by the yaml module b/c of namespace conflicts
# yaml = YAML(typ='safe')

mutex = QtCore.QMutex()
waiting_for_input = QtCore.QWaitCondition()


CONFIG_DIR = Path(user_config_dir(
    "Chameleon 2", "Kaart"))
HISTORY_LOCATION = CONFIG_DIR.joinpath("history.yaml")


class Worker(QObject):
    """

    Worker class, code inside slot should execute in a separate thread.
    Displays file paths, executes comparison function, writes and saves file.

    """
    done = pyqtSignal()
    overwrite_confirm = pyqtSignal(str)

    def __init__(self, modes, files, group_output):
        super().__init__()
        # Define set of selected modes
        self.modes = modes
        self.files = files
        self.group_output = group_output
        self.response = None
    # modes = set()
    # def __init__(self, parent=None):
    #     super().__init__()

    # @pyqtSlot()
    # def mode_loop(self):
    # Create a file for each chosen mode
    @pyqtSlot()
    def run(self):
        """
        Runs when thread started, saves history to file and calls other functions to write files.
        """
        # Saving paths to config for future loading
        # Make directory if it doesn't exist
        if not CONFIG_DIR.is_dir():
            try:
                CONFIG_DIR.mkdir()
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
        if self.files:
            with HISTORY_LOCATION.open('w') as f:
                yaml.dump(self.files, f)
                # f.write("oldFileName: " +
                #                     self.old_file_value + "\n")
                # f.write("newFileName: " +
                #                     self.new_file_value + "\n")
                # f.write("outputFileName: " +
                #                     self.output_file_value + "\n")
        for mode in self.modes:
            self.execute_query(mode, self.files, self.group_output)
        # Signal the main thread that this thread is complete
        self.done.emit()

    def execute_query(self, mode, files, group_output):
        """
        Saves file path for future loading, create a directory if one does not
        already exist. Groups JOSM tags with SQL and generates suitable output.

        Raises
        ------
        OSError
            If history path does not exist and returns a system-related error.
        """
        # Creating SQL snippets
        if group_output:
                # Generating temporary output files (max size 100 MB)
            tempf = tempfile.NamedTemporaryFile(
                mode='w', buffering=-1, encoding=None, newline=None,
                suffix=".csv", prefix=None, dir=None, delete=True)
            print(f'Temporary file generated at {tempf.name}.')
        sql = self.build_query(mode, files, group_output)
        # Generate variable for output file path
        if group_output:
            print(f"Writing to temp file.")
            input_params = QInputParams(
                skip_header=True,
                delimiter='\t'
            )
            output_params = QOutputParams(
                delimiter='\t',
                output_header=True
            )
            q_engine = QTextAsData()
            q_output = q_engine.execute(
                sql, input_params)
            q_output_printer = QOutputPrinter(
                output_params)
            q_output_printer.print_output(
                tempf, sys.stderr, q_output)

            print(
                f"Completed intermediate processing for {mode}.")
            # Grouping function with q
            sql = ("SELECT ('http://localhost:8111/load_object?new_layer=true&objects=' || "
                   "group_concat(id)) AS url, count(id) AS count,"
                   "group_concat(distinct user) AS users,max(timestamp) AS latest_timestamp,"
                   "min(version) AS version, ")
            if mode != "highway":
                sql += "highway,"
            sql += (f"old_{mode},new_{mode}, group_concat(DISTINCT action) AS actions, "
                    f"NULL AS \"notes\" FROM {tempf.name} "
                    f"GROUP BY old_{mode},new_{mode},action;")
            # print(sql)

        # Proceed with generating tangible output for user
        file_name = files['output'] + "_" + mode + ".csv"
        if os.path.isfile(file_name):
            mutex.lock()
            self.overwrite_confirm.emit(file_name)
            waiting_for_input.wait(mutex)
            mutex.unlock()
            if self.response:
                # mutex.unlock()
                self.write_file(sql, file_name)
            elif self.response is False:
                # mutex.unlock()
                return
            else:
                raise Exception("Chameleon didn't get an answer")
        else:
            self.write_file(sql, file_name)
        if group_output:
            tempf.close()

    def build_query(self, mode, files, group_output):
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
        if mode != "highway":
            sql += "ifnull(new.highway,old.highway) AS highway, "
        if mode != "name":
            sql += "ifnull(new.name,old.name) AS name, "
        sql += (f"ifnull(old.{mode},'') AS old_{mode}, ifnull(new.{mode},'') AS new_{mode}, "
                "CASE WHEN new.\"@id\" LIKE old.\"@id\" THEN \"modified\" "
                "ELSE \"deleted\" END \"action\" ")
        if not group_output:
            # Differentiate between objects that are modified and deleted
            sql += ", NULL AS \"notes\" "
        sql += (f"FROM {files['old']} AS old "
                f"LEFT OUTER JOIN {files['new']} AS new ON old.\"@id\" = new.\"@id\" "
                f"WHERE old_{mode} NOT LIKE new_{mode} ")

        # UNION FULL LEFT OUTER JOIN to isolated instances of new objects
        sql += "UNION ALL SELECT (substr(new.\"@type\",1,1) || new.\"@id\") AS id, "
        if not group_output:
            sql += ("('http://localhost:8111/load_object?new_layer=true&objects=' || "
                    "substr(new.\"@type\",1,1) || new.\"@id\") AS url, ")
        sql += ("new.\"@user\" AS user, substr(new.\"@timestamp\",1,10) AS timestamp, "
                "new.\"@version\" AS version, ")
        if mode != "highway":
            sql += "new.highway AS highway, "
        if mode != "name":
            sql += "new.name AS name, "
        sql += (f"ifnull(old.{mode},'') AS old_{mode}, ifnull(new.{mode},'') AS new_{mode}, "
                "\"new\" AS \"action\" ")
        if not group_output:
            # 'action' defaults to 'new' to capture 'added' and 'split' objects
            sql += ", NULL AS \"notes\" "
        sql += (f"FROM {files['new']} AS new "
                f"LEFT OUTER JOIN {files['old']} AS old ON new.\"@id\" = old.\"@id\" "
                f"WHERE old.\"@id\" IS NULL AND length(ifnull(new_{mode},'')) > 0")
        # print(sql)
        return sql

    def write_file(self, sql, file_name):
        """
        Handles writing formatted file using data grabbed by SQL query.

        Parameters
        ----------
        sql : str
            Query that selects JOSM URL for tag grouping
        file_name : str
            File name in csv format
        """
        try:
            with open(file_name, "w") as output_file:
                print(f"Writing {file_name}")
                input_params = QInputParams(
                    skip_header=True,
                    delimiter='\t'
                )
                output_params = QOutputParams(
                    delimiter='\t',
                    output_header=True
                )
                q_engine = QTextAsData()
                q_output = q_engine.execute(
                    sql, input_params)
                q_output_printer = QOutputPrinter(
                    output_params)
                q_output_printer.print_output(
                    output_file, sys.stderr, q_output)
        except PermissionError:
            return False
        else:
            print("Complete")
            return True
            # Insert completion feedback here


class MainApp(QtWidgets.QMainWindow, src.design.Ui_MainWindow):
    """

    Main PyQT window class that allows communication between UI and backend.
    Passes QMainWindow parameter to provide main application window, establish
    event handling with signal/slot connection.

    """

    def __init__(self, parent=None):
        """
        Loads history file path, establish event handling with signal/slot
        connection.
        """
        super().__init__()
        self.setupUi(self)
        self.work_thread = QThread()

        # Check for history file and load if exists
        try:
            with HISTORY_LOCATION.open('r') as f:
                loaded = yaml.load(f)
                if isinstance(loaded, dict):
                    self.oldFileNameBox.insert(loaded.get('old', ''))
                    self.newFileNameBox.insert(loaded.get('new', ''))
                    self.outputFileNameBox.insert(loaded.get('output', ''))
        # If file doesn't exist, fail silently
        except FileNotFoundError:
            pass
        self.checkbox_checker()
        # Connecting signals to slots
        self.oldFileSelectButton.clicked.connect(self.open_input_file)
        self.newFileSelectButton.clicked.connect(self.open_input_file)
        self.outputFileSelectButton.clicked.connect(self.output_file)
        self.runButton.clicked.connect(self.run_query)
        self.refBox.stateChanged.connect(self.checkbox_checker)
        self.int_refBox.stateChanged.connect(self.checkbox_checker)
        self.nameBox.stateChanged.connect(self.checkbox_checker)
        self.highwayBox.stateChanged.connect(self.checkbox_checker)

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

    def checkbox_checker(self):
        """
        Only enables run button if atleast one Tags box is checked.
        """
        is_checked = [self.refBox.isChecked(), self.int_refBox.isChecked(),
                      self.nameBox.isChecked(), self.highwayBox.isChecked()]
        self.runButton.setEnabled(0)
        if any(is_checked):
            self.runButton.setEnabled(1)

    def dialog_critical(self, text, info):
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
        if not os.access(output_file_path.parents[0], os.W_OK):
            self.dialog_critical(
                "Output directory not writeable!", ""
            )
            return
        modes = set()
        if self.refBox.isChecked():
            modes |= {"ref"}
        if self.int_refBox.isChecked():
            modes |= {"int_ref"}
        if self.nameBox.isChecked():
            modes |= {"name"}
        if self.highwayBox.isChecked():
            modes |= {"highway"}
        print(modes)
        if self.groupingCheckBox.isChecked():
            group_output = True
        else:
            group_output = False
        self.worker = Worker(modes, files, group_output)
        self.worker.done.connect(self.finished)
        self.worker.overwrite_confirm.connect(self.overwrite_message)
        self.worker.moveToThread(self.work_thread)
        self.work_thread.start()
        self.work_thread.started.connect(self.worker.run)

        # instantiate progress bar class
        self.progress_bar = ProgressBar()
        # show progress bar
        self.progress_bar.show()
        # loop to step through bar
        for i in range(0, 100):
            time.sleep(0.01)
            self.progress_bar.set_value(((i + 1) / 100) * 100)
            QApplication.processEvents()

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

    # Re-enable run button when function complete
    def finished(self):
        """
        Helper method finalizes run process: re-enable run button, uncheck
        box_text, and notify user of run process completion.
        """
        self.runButton.setEnabled(1)
        self.work_thread.quit()
        self.work_thread.wait()
        # close the progress bar
        self.progress_bar.close()

        # untoggle all radio buttons
        self.refBox.setChecked(False)
        self.int_refBox.setChecked(False)
        self.nameBox.setChecked(False)
        self.highwayBox.setChecked(False)
        self.groupingCheckBox.setChecked(False)
        QMessageBox.information(self, "Message", "Complete!")

    def overwrite_message(self, file_name):
        """
        Display user notification box for overwrite file option.

        Parameters
        ----------
        file_name : str
            File (named by user) to be saved and written.
        """
        mutex.lock()
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
        mutex.unlock()


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
    app.exec_()


if __name__ == '__main__':
    main()
