#!/usr/bin/env python3

import errno
import os
import re
import sys
# Finds the right place to save config and log files on each OS
from appdirs import user_config_dir  # , user_log_dir
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal
# Loads and saves settings to YAML
from ruamel.yaml import YAML
# Does the processing
from q import QTextAsData, QInputParams, QOutputParams, QOutputPrinter
import design  # Import generated UI file
# Required by the yaml module b/c of namespace conflicts
yaml = YAML(typ='safe')


class AThread(QThread):
    signal = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)

    def run(self):

        # Create a file for each chosen mode
        for mode in self.modes:
            # Creating SQL snippets
            sql = "SELECT ('http://localhost:8111/load_object?new_layer=true&objects=' ||"
            if self.group_output:
                sql += " group_concat("
            sql += "substr(new.\"@type\",1,1) || new.\"@id\""
            if self.group_output:
                sql += ")) AS url, count(new.\"@id\") AS way_count, group_concat(distinct new.\"@user\") AS users,max(substr(new.\"@timestamp\",1,10)) AS latest_timestamp, "
            else:
                sql += ") AS url,new.\"@user\" AS user,substr(new.\"@timestamp\",1,10) AS timestamp, "
            if mode != "highway":
                sql += "new.highway, "
            if self.group_output:
                # print("Checked")
                sql += f"(old.{mode} || \"→\" || new.{mode}) AS {mode}_change, "
            else:
                if mode == "highway":
                    sql += "new.name, "
                sql += f"old.{mode} AS old_{mode}, new.{mode} AS new_{mode}, "

            sql += f"NULL AS \"notes\" FROM {self.oldFileValue} AS old LEFT OUTER JOIN {self.newFileValue} AS new ON new.\"@id\" = old.\"@id\" WHERE old.{mode} NOT LIKE new.{mode}"
            if self.group_output:
                sql += f" GROUP BY (old.{mode} || \"→\" || new.{mode})"

            print(sql)
            fileName = self.outputFileValue + "_" + mode + ".csv"
            # if os.path.isfile(fileName):
            # send a signal and get the return
            # if response no
            #   continue
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
            # Saving paths to cache for future loading
            # Make directory if it doesn't exist
            if not os.path.exists(os.path.dirname(self.history_location)):
                try:
                    os.makedirs(os.path.dirname(self.history_location))
                except OSError as exc:
                    if exc.errno != errno.EEXIST:
                        raise
            with open(self.history_location, 'w') as history_write:
                history_write.write("oldFileName: " +
                                    self.oldFileValue + "\n")
                history_write.write("newFileName: " +
                                    self.newFileValue + "\n")
                history_write.write("outputFileName: " +
                                    self.outputFileValue + "\n")
        self.signal.emit()


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
        self.work_thread = AThread()
        self.work_thread.signal.connect(self.finished)
        self.work_thread.history_location = user_config_dir(
            "Chameleon 2", "Kaart") + "/history.yaml"
        oldFileName = ''
        newFileName = ''
        outputFileName = ''

        # Check for history file and load if exists
        try:
            with open(self.work_thread.history_location, 'r') as history_read:
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

    def overwrite_confirm(self):
        overwritePrompt = QtWidgets.QMessageBox()
        overwritePrompt.setIcon(QMessageBox.Question)
        overwritePromptResponse = overwritePrompt.question(
            MainApp, '', f"{fileName} exists. Do you want to overwrite?", overwritePrompt.No | overwritePrompt.Yes)
        # Skip to the next iteration if user responds "No",
        # continue to the `with` block otherwise
        # if overwritePromptResponse == overwritePrompt.No:
        #     continue

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
        # try:
        # Disable run button while running
        self.runButton.setEnabled(0)
        self.work_thread.oldFileValue = self.oldFileNameBox.text()
        self.work_thread.newFileValue = self.newFileNameBox.text()
        self.work_thread.outputFileValue = self.outputFileNameBox.text()
        # Check for spaces in file names
        spaceExpression = re.compile("^\\S+\\s+\\S+$")
        if spaceExpression.match(self.work_thread.oldFileValue) or spaceExpression.match(self.work_thread.newFileValue) or spaceExpression.match(self.work_thread.outputFileValue):
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
            self.work_thread.modes = set()
            if self.refBox.isChecked():
                self.work_thread.modes |= {"ref"}
            if self.int_refBox.isChecked():
                self.work_thread.modes |= {"int_ref"}
            if self.nameBox.isChecked():
                self.work_thread.modes |= {"name"}
            # Handle highway separately
            if self.highwayBox.isChecked():
                self.work_thread.modes |= {"highway"}
            # print(modes)
            if self.groupingCheckBox.isChecked():
                self.work_thread.group_output = True
            else:
                self.work_thread.group_output = False
            self.work_thread.start()

        # finally:
        # Re-enable run button when function complete,
        # even if it doesn't complete successfully
    def finished(self):
        self.runButton.setEnabled(1)


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
