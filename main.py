#!/usr/bin/env python3

import errno
import os
import re
import sys
import tempfile
# Finds the right place to save config and log files on each OS
from appdirs import user_config_dir  # , user_log_dir
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, QObject, pyqtSlot
# Loads and saves settings to YAML
from ruamel.yaml import YAML
# Does the processing
from q import QTextAsData, QInputParams, QOutputParams, QOutputPrinter
import design  # Import generated UI file
# Required by the yaml module b/c of namespace conflicts
yaml = YAML(typ='safe')

mutex = QtCore.QMutex()
waiting_for_input = QtCore.QWaitCondition()

history_location = user_config_dir(
    "Chameleon 2", "Kaart") + "/history.yaml"


class Worker(QObject):
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
        # Saving paths to config for future loading
        # Make directory if it doesn't exist
        if not os.path.exists(os.path.dirname(history_location)):
            try:
                os.makedirs(os.path.dirname(history_location))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
        with open(history_location, 'w') as history_write:
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
                    mode='w', buffering=-1, encoding=None, newline=None, suffix=".csv", prefix=None, dir=None, delete=True)
                print(f'Temporary file generated at {tempf.name}.')
                # Creating SQL snippets
                # Added based ID SQL to ensure Object ID output
                sql = "SELECT substr(new.\"@type\",1,1) || new.\"@id\" AS id, "
                sql += "new.\"@user\" AS user, substr(new.\"@timestamp\",1,10) AS timestamp, "
                if mode != "highway":
                    sql += "new.highway AS new_highway, "
                elif mode == "highway":
                    sql += "new.name AS new_name, "
                sql += f"old.{mode} AS old_{mode}, new.{mode} AS new_{mode} "
                sql += f"FROM {self.oldFileValue} AS old LEFT OUTER JOIN {self.newFileValue} AS new ON new.\"@id\" = old.\"@id\" WHERE old.{mode} NOT LIKE new.{mode} "

                # Union all full left outer join SQL statements
                sql += "UNION ALL SELECT substr(new.\"@type\",1,1) || new.\"@id\" AS id, "
                sql += "new.\"@user\" AS user, substr(new.\"@timestamp\",1,10) AS timestamp, "
                if mode != "highway":
                    sql += "new.highway AS new_highway, "
                elif mode == "highway":
                    sql += "new.name AS new_name, "
                sql += f"old.{mode} AS old_{mode}, new.{mode} AS new_{mode} "
                sql += f"FROM {self.newFileValue} AS new LEFT OUTER JOIN {self.oldFileValue} AS old ON new.\"@id\" = old.\"@id\" WHERE old.\"@id\" IS NULL"
                print(sql)
                # Generate variable for output file path

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
                sql = "SELECT ('http://localhost:8111/load_object?new_layer=true&objects=' || "
                sql += "group_concat(id)) AS url, count(id) AS count, group_concat(distinct user) AS users, max(timestamp) AS latest_timestamp, "
                if mode != "highway":
                    sql += "new_highway, "
                sql += f"(old_{mode} || \"→\" || new_{mode}) AS {mode}_change, "
                sql += f"NULL AS \"notes\" FROM {tempf.name} AS new"
                sql += f" GROUP BY (old_{mode} || \"→\" || new_{mode})"
                print(sql)

                # Proceed with generating tangible output for user
                fileName = self.outputFileValue + "_" + mode + ".csv"
                if os.path.isfile(fileName):
                    mutex.lock()
                    self.overwrite_confirm.emit(fileName)
                    waiting_for_input.wait(mutex)
                    mutex.unlock()
                    if self.response:
                        # mutex.unlock()
                        self.write_file(sql, fileName)
                    elif self.response == False:
                        # mutex.unlock()
                        continue
                    else:
                        raise Exception("Chameleon didn't get an answer")
                    tempf.close()
                else:
                    self.write_file(sql, fileName)
                    tempf.close()

            # Proceed with normal file processing when grouping is not selected
            else:
                # Creating SQL snippets
                # Added based ID SQL to ensure Object ID output
                sql = "SELECT substr(new.\"@type\",1,1) || new.\"@id\" AS id, "
                sql += "('http://localhost:8111/load_object?new_layer=true&objects=' || "
                sql += "substr(new.\"@type\",1,1) || new.\"@id\""
                sql += ") AS url, new.\"@user\" AS user,substr(new.\"@timestamp\",1,10) AS timestamp, "
                if mode != "highway":
                    sql += "new.highway AS new_highway, "
                else:
                    if mode == "highway":
                        sql += "new.name AS new_name, "
                    sql += f"old.{mode} AS old_{mode}, new.{mode} AS new_{mode}, "
                sql += f"NULL AS \"notes\" FROM {self.oldFileValue} AS old LEFT OUTER JOIN {self.newFileValue} AS new ON new.\"@id\" = old.\"@id\" WHERE old.{mode} NOT LIKE new.{mode}"

                # Union all full left outer join SQL statements
                sql += " UNION ALL SELECT substr(new.\"@type\",1,1) || new.\"@id\" AS id, "
                sql += "('http://localhost:8111/load_object?new_layer=true&objects=' || "
                sql += "substr(new.\"@type\",1,1) || new.\"@id\""
                sql += ") AS url, new.\"@user\" AS user,substr(new.\"@timestamp\",1,10) AS timestamp, "
                if mode != "highway":
                    sql += "new.highway, "
                else:
                    if mode == "highway":
                        sql += "new.name, "
                    sql += f"old.{mode} AS old_{mode}, new.{mode} AS new_{mode}, "
                sql += f"NULL AS \"notes\" FROM {self.newFileValue} AS new LEFT OUTER JOIN {self.oldFileValue} AS old ON new.\"@id\" = old.\"@id\" WHERE old.\"@id\" IS NULL"

                print(sql)
                fileName = self.outputFileValue + "_" + mode + ".csv"
                if os.path.isfile(fileName):
                    mutex.lock()
                    self.overwrite_confirm.emit(fileName)
                    waiting_for_input.wait(mutex)
                    if self.response == False:
                        continue
                    elif self.response:
                        self.write_file(sql, fileName)
                    mutex.unlock()
                else:
                    self.write_file(sql, fileName)
        # Signal the main thread that this thread is complete
        self.done.emit()

    def write_file(self, sql, fileName):
        with open(fileName, "w") as outputFile:
            print(f"Writing {fileName}")
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

    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)

        # defaults for debugging
        # self.oldFileNameBox.insert(
        #     "/Users/primaryuser/Downloads/algeria_old.csv")
        # self.newFileNameBox.insert(
        #     "/Users/primaryuser/Downloads/algeria_cur.csv")
        # self.outputFileNameBox.insert("/Users/primaryuser/Desktop/test")
        # self.refBox.setChecked(1)
        # end debugging
        oldFileName = ''
        newFileName = ''
        outputFileName = ''

        # Check for history file and load if exists
        try:
            with open(history_location, 'r') as history_read:
                loaded = yaml.load(history_read)
                oldFileName = loaded.get('oldFileName')
                newFileName = loaded.get('newFileName')
                outputFileName = loaded.get('outputFileName')
                self.oldFileNameBox.insert(oldFileName)
                self.newFileNameBox.insert(newFileName)
                self.outputFileNameBox.insert(outputFileName)
        # If file doesn't exist, fail silently
        except:
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

    def open_old_file(self):
        if re.match("\\S+", self.oldFileNameBox.text()):
            oldFileDir = self.oldFileNameBox.text()
        else:
            oldFileDir = os.path.expanduser("~/Downloads")
        oldFileName, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select CSV file with old data", oldFileDir, "CSV (*.csv)")
        if oldFileName:
            self.oldFileNameBox.clear()
            self.oldFileNameBox.insert(oldFileName)

    def open_new_file(self):
        if re.match("\\S+", self.newFileNameBox.text()):
            newFileDir = self.newFileNameBox.text()
        else:
            newFileDir = os.path.expanduser("~/Downloads")
        newFileName, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select CSV file with new data", newFileDir, "CSV (*.csv)")
        if newFileName:
            self.newFileNameBox.clear()
            self.newFileNameBox.insert(newFileName)

    def output_file(self):
        if re.match("\\S+", self.newFileNameBox.text()):
            outputFileDir = os.path.dirname(self.outputFileNameBox.text())
        else:
            outputFileDir = os.path.expanduser("~/Documents")
        outputFileName, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self, "Enter output file prefix", outputFileDir)
        if outputFileName:
            if ".csv" in outputFileName:
                outputFileName = outputFileName.replace('.csv', '')
            self.outputFileNameBox.clear()
            self.outputFileNameBox.insert(outputFileName)

    def checkbox_checker(self):
        if not self.refBox.isChecked() and not self.int_refBox.isChecked() and not self.nameBox.isChecked() and not self.highwayBox.isChecked():
            self.runButton.setEnabled(0)
        else:
            self.runButton.setEnabled(1)

    def run_query(self):
        self.work_thread = QThread()
        self.worker = Worker()
        self.worker.done.connect(self.finished)
        # try:
        # Disable run button while running
        self.runButton.setEnabled(0)
        self.worker.oldFileValue = self.oldFileNameBox.text()
        self.worker.newFileValue = self.newFileNameBox.text()
        self.worker.outputFileValue = self.outputFileNameBox.text()
        # Check for spaces in file names
        spaceExpression = re.compile("^\\S+\\s+\\S+$")
        if spaceExpression.match(self.worker.oldFileValue) or spaceExpression.match(self.worker.newFileValue) or spaceExpression.match(self.worker.outputFileValue):
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
        else:
            # Define set of selected modes
            self.worker.modes = set()
            if self.refBox.isChecked():
                self.worker.modes |= {"ref"}
            if self.int_refBox.isChecked():
                self.worker.modes |= {"int_ref"}
            if self.nameBox.isChecked():
                self.worker.modes |= {"name"}
            # Handle highway separately
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

        # finally:
        # Re-enable run button when function complete,
        # even if it doesn't complete successfully

    def finished(self):
        self.runButton.setEnabled(1)
        self.work_thread.quit()
        self.work_thread.wait()

    def overwrite_message(self, fileName):
        mutex.lock()
        overwritePrompt = QtWidgets.QMessageBox()
        overwritePrompt.setIcon(QMessageBox.Question)
        overwritePromptResponse = overwritePrompt.question(
            self, '', f"{fileName} exists. Do you want to overwrite?", overwritePrompt.No | overwritePrompt.Yes)
        if overwritePromptResponse == overwritePrompt.No:
            self.worker.response = False
        elif overwritePromptResponse == overwritePrompt.Yes:
            self.worker.response = True
        waiting_for_input.wakeAll()
        mutex.unlock()


def main():
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
