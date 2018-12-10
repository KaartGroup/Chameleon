#!/usr/bin/env python3
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox
import sys
import os
import re
# Import generated UI file
import design
from q import QTextAsData, QInputParams, QOutputParams, QOutputPrinter


class MainApp(QtWidgets.QMainWindow, design.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        # defaults for debugging
        self.oldFileNameBox.insert(
            "/Users/primaryuser/Downloads/algeria_old.csv")
        self.newFileNameBox.insert(
            "/Users/primaryuser/Downloads/algeria_cur.csv")
        self.outputFileNameBox.insert("/Users/primaryuser/Desktop/test")
        self.refBox.setChecked(1)
        # end debugging
        self.oldFileSelectButton.clicked.connect(self.open_old_file)
        self.newFileSelectButton.clicked.connect(self.open_new_file)
        self.outputFileSelectButton.clicked.connect(self.output_file)
        self.runButton.clicked.connect(self.run_query)

    def open_old_file(self):
        oldFileName, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select CSV file with old data", os.path.expanduser("~/Downloads"), "CSV (*.csv)")
        if oldFileName:
            self.oldFileNameBox.clear()
            self.oldFileNameBox.insert(oldFileName)

    def open_new_file(self):
        newFileName, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select CSV file with new data", os.path.expanduser("~/Downloads"), "CSV (*.csv)")
        if newFileName:
            self.newFileNameBox.clear()
            self.newFileNameBox.insert(newFileName)

    def output_file(self):
        outputFileName, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self, "Enter output file prefix", os.path.expanduser("~/Documents"))
        if outputFileName:
            if ".csv" in outputFileName:
                outputFileName = outputFileName.replace('.csv', '')
            self.outputFileNameBox.clear()
            self.outputFileNameBox.insert(outputFileName)

    def run_query(self):
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

            # Disable run button while running
            self.runButton.setEnabled(0)
            # Cancel button logic goes here
            # self.cancelButton.setEnabled(1)

            # Create a file for each chosen mode
            for mode in modes:
                # Creating SQL snippets
                sql = "SELECT ('http://localhost:8111/load_object?new_layer=true&objects=' ||"
                if self.groupingCheckBox.isChecked():
                    sql += " group_concat("
                sql += "substr(new.\"@type\",1,1) || new.\"@id\""
                if self.groupingCheckBox.isChecked():
                    sql += ")) AS url,group_concat(distinct new.\"@user\") AS users,max(substr(new.\"@timestamp\",1,10)) AS latest_timestamp, "
                else:
                    sql += ") AS url,new.\"@user\" AS user,substr(new.\"@timestamp\",1,10) AS timestamp, "
                if mode != "highway":
                    sql += "new.highway, "
                if self.groupingCheckBox.isChecked():
                    # print("Checked")
                    sql += f"(old.{mode} || \"→\" || new.{mode}) AS {mode}_change, "
                else:
                    if mode == "highway":
                        sql += "new.name, "
                    sql += f"old.{mode} AS old_{mode}, new.{mode} AS new_{mode}, "

                sql += f"NULL AS \"notes\" FROM {oldFileValue} AS old LEFT OUTER JOIN {newFileValue} AS new ON new.\"@id\" = old.\"@id\" WHERE old.{mode} NOT LIKE new.{mode}"
                if self.groupingCheckBox.isChecked():
                    sql += f" GROUP BY (old.{mode} || \"→\" || new.{mode})"

                print(sql)
                fileName = outputFileValue + "_" + mode + ".csv"
                if os.path.isfile(fileName):
                    overwritePrompt = QtWidgets.QMessageBox()
                    overwritePrompt.setIcon(QMessageBox.Question)
                    overwritePromptResponse = overwritePrompt.question(
                        self, '', f"{fileName} exists. Do you want to overwrite?", overwritePrompt.No | overwritePrompt.Yes)
                    # Skip to the next iteration if user responds "No", continue to the `with` block otherwise
                    if overwritePromptResponse == overwritePrompt.No:
                        continue
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
            # Re-enable run button when function complete
            self.runButton.setEnabled(1)
            # self.cancelButton.setEnabled(0)


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
