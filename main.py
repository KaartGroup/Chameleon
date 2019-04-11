#!/usr/bin/env python3

import errno
import os
import os.path
import re
import sys
import tempfile
import time
from pathlib import Path

# Finds the right place to save config and log files on each OS
from appdirs import user_config_dir  # , user_log_dir
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QMessageBox
# Loads and saves settings to YAML
from ruamel.yaml import YAML

import design  # Import generated UI file
from ProgressBar import ProgressBar
# Does the processing
from q import QInputParams, QOutputParams, QOutputPrinter, QTextAsData

# Required by the yaml module b/c of namespace conflicts
yaml = YAML(typ='safe')

mutex = QtCore.QMutex()
waiting_for_input = QtCore.QWaitCondition()

HISTORY_LOCATION = user_config_dir(
    "Chameleon 2", "Kaart") + "/history.yaml"


class Worker(QObject):
    """

    Worker class, code inside slot should execute in a separate thread.
    Displays file paths, executes comparison function, writes and saves file.

    """
    done = pyqtSignal()
    overwrite_confirm = pyqtSignal(str)
    # modes = set()
    # def __init__(self, parent=None):
    #     super().__init__()

    # @pyqtSlot()
    # def mode_loop(self):
    # Create a file for each chosen mode
    @pyqtSlot()
    def firstwork(self):
        """
        Saves file path for future loading, create a directory if one does not
        already exist. Groups JOSM tags with SQL and generates suitable output.

        Raises
        ------
        OSError
            If history path does not exist and returns a system-related error.
        """
        # Saving paths to config for future loading
        # Make directory if it doesn't exist
        if not os.path.exists(os.path.dirname(HISTORY_LOCATION)):
            try:
                os.makedirs(os.path.dirname(HISTORY_LOCATION))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
        with open(HISTORY_LOCATION, 'w') as history_write:
            history_write.write("oldFileName: " +
                                self.oldFileValue + "\n")
            history_write.write("newFileName: " +
                                self.newFileValue + "\n")
            history_write.write("outputFileName: " +
                                self.outputFileValue + "\n")
        for mode in self.modes:
            if self.group_output:
                # Generating temporary output files (max size 100 MB)
                tempf = tempfile.NamedTemporaryFile(
                    mode='w', buffering=-1, encoding=None, newline=None,
                    suffix=".csv", prefix=None, dir=None, delete=True)
                print(f'Temporary file generated at {tempf.name}.')
            # Creating SQL snippets
            # Added based ID SQL to ensure Object ID output
            # LEFT OUTER JOIN to isolate instances of old NOT LIKE new
            sql = ("SELECT (substr(ifnull(new.\"@type\",old.\"@type\"),1,1) || "
                   "ifnull(new.\"@id\",old.\"@id\")) AS id, ")
            if not self.group_output:
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
            if not self.group_output:
                # Differentiate between objects that are modified and deleted
                sql += ", NULL AS \"notes\" "
            sql += (f"FROM {self.oldFileValue} AS old "
                    f"LEFT OUTER JOIN {self.newFileValue} AS new ON old.\"@id\" = new.\"@id\" "
                    f"WHERE old_{mode} NOT LIKE new_{mode} ")

            # UNION FULL LEFT OUTER JOIN to isolated instances of new objects
            sql += "UNION ALL SELECT (substr(new.\"@type\",1,1) || new.\"@id\") AS id, "
            if not self.group_output:
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
            if not self.group_output:
                # 'action' defaults to 'new' to capture 'added' and 'split' objects
                sql += ", NULL AS \"notes\" "
            sql += (f"FROM {self.newFileValue} AS new "
                    f"LEFT OUTER JOIN {self.oldFileValue} AS old ON new.\"@id\" = old.\"@id\" "
                    f"WHERE old.\"@id\" IS NULL AND length(ifnull(new_{mode},'')) > 0 ")

            print(sql)
            # Generate variable for output file path
            if self.group_output:
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
                print(sql)

            # Proceed with generating tangible output for user
            file_name = self.outputFileValue + "_" + mode + ".csv"
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
                    continue
                else:
                    raise Exception("Chameleon didn't get an answer")
            else:
                self.write_file(sql, file_name)
            if self.group_output:
                tempf.close()
        # Signal the main thread that this thread is complete
        self.done.emit()

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
        with open(file_name, "w") as outputFile:
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
                outputFile, sys.stderr, q_output)
            print("Complete")
            # Insert completion feedback here


class MainApp(QtWidgets.QMainWindow, design.Ui_MainWindow):
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

        # Check for history file and load if exists
        try:
            with open(HISTORY_LOCATION, 'r') as history_read:
                loaded = yaml.load(history_read)
                self.oldFileNameBox.insert(loaded.get('oldFileName', ''))
                self.newFileNameBox.insert(loaded.get('newFileName', ''))
                self.outputFileNameBox.insert(loaded.get('outputFileName', ''))
        # If file doesn't exist, fail silently
        except FileNotFoundError:
            pass
        self.checkbox_checker()
        # Connecting signals to slots
        self.oldFileSelectButton.clicked.connect(self.open_old_file)
        self.newFileSelectButton.clicked.connect(self.open_new_file)
        self.outputFileSelectButton.clicked.connect(self.output_file)
        self.runButton.clicked.connect(self.run_query)
        self.refBox.stateChanged.connect(self.checkbox_checker)
        self.int_refBox.stateChanged.connect(self.checkbox_checker)
        self.nameBox.stateChanged.connect(self.checkbox_checker)
        self.highwayBox.stateChanged.connect(self.checkbox_checker)

    # These next two functions could probably be consolidated into one,
    # taking the calling box as an argument
    def open_old_file(self):
        """
        Adds functionality to the Open Old File (...) button, opens the
        '/downloads' system path to find csv file.
        """
        if re.match("\\S+", self.oldFileNameBox.text()):
            old_file_dir = self.oldFileNameBox.text()
        else:
            # If no previous location, default to Downloads folder
            old_file_dir = os.path.expanduser("~/Downloads")
        old_file_name, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select CSV file with old data", old_file_dir, "CSV (*.csv)")
        if old_file_name:  # Clear the box before adding the new path
            self.oldFileNameBox.clear()
            self.oldFileNameBox.insert(old_file_name)

    def open_new_file(self):
        """
        Adds functionality to the Open New File (...) button, opens the
        '/downloads' system path to find csv file.
        """
        if re.match("\\S+", self.newFileNameBox.text()):
            new_file_dir = self.newFileNameBox.text()
        else:
            # If no previous location, default to Downloads folder
            new_file_dir = os.path.expanduser("~/Downloads")
        new_file_name, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select CSV file with new data", new_file_dir, "CSV (*.csv)")
        if new_file_name:  # Clear the box before adding the new path
            self.newFileNameBox.clear()
            self.newFileNameBox.insert(new_file_name)

    def output_file(self):
        """
        Adds functionality to the Output File (...) button, opens the
        '/downloads' system path for user to name an output file.
        """
        if re.match("\\S+", self.newFileNameBox.text()):
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
        """ Only enables run button if atleast one Tags box is checked. """
        is_checked = [self.refBox.isChecked(), self.int_refBox.isChecked(),
                      self.nameBox.isChecked(), self.highwayBox.isChecked()]
        self.runButton.setEnabled(0)
        if any(is_checked):
            self.runButton.setEnabled(1)

    def run_query(self):
        """
        Allows run button to execute based on selected tag parameters.
        Also Enables/disables run button while executing function and allows
        progress bar functionality. Checks for file/directory validity and spacing.
        """
        self.work_thread = QThread()
        self.worker = Worker()
        self.worker.done.connect(self.finished)
        # try:
        # Disable run button while running
        self.worker.oldFileValue = self.oldFileNameBox.text()
        self.worker.newFileValue = self.newFileNameBox.text()
        self.worker.outputFileValue = self.outputFileNameBox.text()
        # Check for spaces in file names
        space_expression = re.compile("^\\S+\\s+\\S+$")
        if space_expression.match(self.worker.oldFileValue) or \
           space_expression.match(self.worker.newFileValue) or \
           space_expression.match(self.worker.outputFileValue):
            # Popup here
            self.spaceWarning = QtWidgets.QMessageBox()
            self.spaceWarning.setIcon(QMessageBox.Critical)
            self.spaceWarning.setText(
                "Chameleon cannot use files or folders with spaces in their names.")
            self.spaceWarning.setInformativeText(
                "Please rename your files and/or folders to remove spaces.")
            self.spaceWarning.setEscapeButton(QMessageBox.Ok)
            self.spaceWarning.exec()
            return

        # Wrap the file references in Path object to prepare "file not found" warning
        old_file_path = Path(self.worker.oldFileValue)
        new_file_path = Path(self.worker.newFileValue)
        # Check if either old or new file/directory exists. If not, notify user.
        if not old_file_path.is_file() or not new_file_path.is_file():
            self.file_warning = QtWidgets.QMessageBox()
            self.file_warning.setIcon(QMessageBox.Critical)
            if not old_file_path.is_file() and not new_file_path.is_file():
                self.file_warning.setText(
                    "File or directories not found!")
            elif not old_file_path.is_file():
                self.file_warning.setText(
                    "Old file or directory\n%s\nnot found!"
                    % (self.oldFileNameBox.text()))
            elif not new_file_path.is_file():
                self.file_warning.setText(
                    "New file or directory\n%s\nnot found!"
                    % (self.newFileNameBox.text()))
            self.file_warning.setInformativeText(
                "Check if your file or directory(s) exists.")
            self.file_warning.exec()
            return
        # Define set of selected modes
        self.worker.modes = set()
        if self.refBox.isChecked():
            self.worker.modes |= {"ref"}
        if self.int_refBox.isChecked():
            self.worker.modes |= {"int_ref"}
        if self.nameBox.isChecked():
            self.worker.modes |= {"name"}
        if self.highwayBox.isChecked():
            self.worker.modes |= {"highway"}
        print(self.worker.modes)
        if self.groupingCheckBox.isChecked():
            self.worker.group_output = True
        else:
            self.worker.group_output = False
        self.worker.overwrite_confirm.connect(self.overwrite_message)
        self.worker.moveToThread(self.work_thread)
        self.work_thread.start()
        self.work_thread.started.connect(self.worker.firstwork)

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
        boxes, and notify user of run process completion.
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

    def overwrite_message(self, fileName):
        """
        Display user notification box for overwrite file option.

        Parameters
        ----------
        fileName : str
            File (named by user) to be saved and written.
        """
        mutex.lock()
        overwrite_prompt = QtWidgets.QMessageBox()
        overwrite_prompt.setIcon(QMessageBox.Question)
        overwrite_prompt_response = overwrite_prompt.question(
            self, '', f"{fileName} exists. Do you want to overwrite?",
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
