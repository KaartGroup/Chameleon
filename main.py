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
# Loads and saves settings to YAML
from ruamel.yaml import YAML
# Does the processing
from q import QTextAsData, QInputParams, QOutputParams, QOutputPrinter
import design  # Import generated UI file
# Required by the yaml module b/c of namespace conflicts
yaml = YAML(typ='safe')


class MainApp(QtWidgets.QMainWindow, design.Ui_MainWindow):

    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.history_location = user_config_dir(
            "Chameleon 2", "Kaart") + "/history.yaml"
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
            with open(self.history_location, 'r') as history_read:
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
            oldFileDir = os.path.dirname(self.oldFileNameBox.text())
        else:
            oldFileDir = os.path.expanduser("~/Downloads")
        oldFileName, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select CSV file with old data", oldFileDir, "CSV (*.csv)")
        if oldFileName:
            self.oldFileNameBox.clear()
            self.oldFileNameBox.insert(oldFileName)

    def open_new_file(self):
        if re.match("\\S+", self.newFileNameBox.text()):
            newFileDir = os.path.dirname(self.newFileNameBox.text())
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
        try:
            # Disable run button while running
            self.runButton.setEnabled(0)
            # Need to fix the threading here
            oldFileValue = self.oldFileNameBox.text()
            newFileValue = self.newFileNameBox.text()
            outputFileValue = self.outputFileNameBox.text()
            # Check for spaces in file names
            spaceExpression = re.compile("^\\S+\\s+\\S+$")
            if spaceExpression.match(oldFileValue) or spaceExpression.match(newFileValue) or spaceExpression.match(outputFileValue):
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
                modes = set()
                if self.refBox.isChecked():
                    modes |= {"ref"}
                if self.int_refBox.isChecked():
                    modes |= {"int_ref"}
                if self.nameBox.isChecked():
                    modes |= {"name"}
                # Handle highway separately
                if self.highwayBox.isChecked():
                    modes |= {"highway"}
                print(modes)

                # Create a file for each chosen mode
                # First block provides virtual file processing for grouping option
                if self.groupingCheckBox.isChecked():
                    for mode in modes:
                        # Generating temporary output files
                        tempPath = os.path.dirname(outputFileValue) # Check with Evan
                        tempf = tempfile.mkstemp(suffix=mode, prefix='temp', dir=tempPath, text=True)
                        print(f'Temporary file generated at {tempf[1]}.')
                        # Getting just the file name of temp files
                        # os.path.basename(tempf[1]) -> countryhighway
                        # Getting base directory of path
                        # os.path.dirname(tempf[1]) -> /Users/primaryuser/Documents'

                        # Creating SQL snippets
                        # Added based ID SQL to ensure Object ID output
                        sql = "SELECT substr(new.\"@type\",1,1) || new.\"@id\" AS id, "
                        sql += "('http://localhost:8111/load_object?new_layer=true&objects=' || "
                        sql += "substr(new.\"@type\",1,1) || new.\"@id\""
                        sql += ") AS url, new.\"@user\" AS user,substr(new.\"@timestamp\",1,10) AS timestamp, "
                        if mode != "highway":
                            sql += "new.highway, "
                        else:
                            if mode == "highway":
                                sql += "new.name, "
                            sql += f"old.{mode} AS old_{mode}, new.{mode} AS new_{mode}, "
                        sql += f"NULL AS \"notes\" FROM {oldFileValue} AS old LEFT OUTER JOIN {newFileValue} AS new ON new.\"@id\" = old.\"@id\" WHERE old.{mode} NOT LIKE new.{mode}"

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
                        sql += f"NULL AS \"notes\" FROM {newFileValue} AS new LEFT OUTER JOIN {oldFileValue} AS old ON new.\"@id\" = old.\"@id\" WHERE old.\"@id\" IS NULL"
                        
                        # Generate variable for output file path
                        fileName = tempf[1] + ".csv"
                        # Removing temporary files
                        print(f"Deleting {tempf[1]}")
                        os.remove(tempf[1])
                        # Writing initial Chameleon output to temporary file
                        if os.path.isfile(fileName):
                            overwritePrompt = QtWidgets.QMessageBox()
                            overwritePrompt.setIcon(QMessageBox.Question)
                            overwritePromptResponse = overwritePrompt.question(
                                self, '', f"{fileName} exists. Do you want to overwrite?", overwritePrompt.No | overwritePrompt.Yes)
                            # Skip to the next iteration if user responds "No",
                            # continue to the `with` block otherwise
                            if overwritePromptResponse == overwritePrompt.No:
                                continue
                        with open(fileName, "w") as outputFile:
                            print(f"Writing to {fileName}")
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
                            print(f"Completed intermediate processing for {mode}.")

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
                                                oldFileValue + "\n")
                            history_write.write("newFileName: " +
                                                newFileValue + "\n")
                            history_write.write("outputFileName: " +
                                                outputFileValue + "\n")
                        # Clearing temp files
                        # print(f"Deleting {fileName}")
                        # os.remove(fileName)
                # Proceed with normal file processing when grouping is not selected
                else:
                    for mode in modes:
                        # Creating SQL snippets
                        # Added based ID SQL to ensure Object ID output
                        sql = "SELECT substr(new.\"@type\",1,1) || new.\"@id\" AS id, "
                        sql += "('http://localhost:8111/load_object?new_layer=true&objects=' || "
                        sql += "substr(new.\"@type\",1,1) || new.\"@id\""
                        sql += ") AS url, new.\"@user\" AS user,substr(new.\"@timestamp\",1,10) AS timestamp, "
                        if mode != "highway":
                            sql += "new.highway, "
                        else:
                            if mode == "highway":
                                sql += "new.name, "
                            sql += f"old.{mode} AS old_{mode}, new.{mode} AS new_{mode}, "
                        sql += f"NULL AS \"notes\" FROM {oldFileValue} AS old LEFT OUTER JOIN {newFileValue} AS new ON new.\"@id\" = old.\"@id\" WHERE old.{mode} NOT LIKE new.{mode}"

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
                        sql += f"NULL AS \"notes\" FROM {newFileValue} AS new LEFT OUTER JOIN {oldFileValue} AS old ON new.\"@id\" = old.\"@id\" WHERE old.\"@id\" IS NULL"
                        # Processing output file without grouping
                        fileName = outputFileValue + "_" + mode + ".csv"
                        if os.path.isfile(fileName):
                            overwritePrompt = QtWidgets.QMessageBox()
                            overwritePrompt.setIcon(QMessageBox.Question)
                            overwritePromptResponse = overwritePrompt.question(
                                self, '', f"{fileName} exists. Do you want to overwrite?", overwritePrompt.No | overwritePrompt.Yes)
                            # Skip to the next iteration if user responds "No",
                            # continue to the `with` block otherwise
                            if overwritePromptResponse == overwritePrompt.No:
                                continue
                        with open(fileName, "w") as outputFile:
                            print(f"Writing to {fileName}")
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
                            print(f"Completed file processing for {mode}.")
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
                                                oldFileValue + "\n")
                            history_write.write("newFileName: " +
                                                newFileValue + "\n")
                            history_write.write("outputFileName: " +
                                                outputFileValue + "\n")
        finally:
            # Re-enable run button when function complete,
            # even if it doesn't complete successfully
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
