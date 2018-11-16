#!/usr/bin/env python3
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
import os
# Import generated UI file
import design
from q import QTextAsData, QInputParams, QOutputParams, QOutputPrinter

class MainApp(QtWidgets.QMainWindow, design.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        # defaults for debugging
        self.oldFileNameBox.insert("/Users/primaryuser/Downloads/china_old.csv")
        self.newFileNameBox.insert("/Users/primaryuser/Downloads/china_cur.csv")
        self.outputFileNameBox.insert("/Users/primaryuser/Desktop/test")
        self.refBox.setChecked(1)
        # end debugging
        self.oldFileSelectButton.clicked.connect(self.open_old_file)
        self.newFileSelectButton.clicked.connect(self.open_new_file)
        self.outputFileSelectButton.clicked.connect(self.output_file)
        self.runButton.clicked.connect(self.run_query)
    def open_old_file(self):
        oldFileName, _filter = QtWidgets.QFileDialog.getOpenFileName(self, "Select CSV file with old data", os.path.expanduser("~/Downloads"), "CSV (*.csv)")
        if oldFileName:
            self.oldFileNameBox.clear()
            self.oldFileNameBox.insert(oldFileName)
    def open_new_file(self):
        newFileName, _filter = QtWidgets.QFileDialog.getOpenFileName(self, "Select CSV file with new data", os.path.expanduser("~/Downloads"), "CSV (*.csv)")
        if newFileName:
            self.newFileNameBox.clear()
            self.newFileNameBox.insert(newFileName)
    def output_file(self):
        outputFileName, _filter = QtWidgets.QFileDialog.getSaveFileName(self, "Enter output file prefix", os.path.expanduser("~/Documents"))
        if outputFileName:
            if ".csv" in outputFileName:
                outputFileName = outputFileName.replace('.csv', '')
            self.outputFileNameBox.clear()
            self.outputFileNameBox.insert(outputFileName)
    def run_query(self):
        oldFileValue = self.oldFileNameBox.text()
        newFileValue = self.newFileNameBox.text()
        outputFileValue = self.outputFileNameBox.text()
        groupingstmt = ""

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
        for mode in modes:
            # Creating SQL snippets
            selectid = "substr(new.\"@type\",1,1) || new.\"@id\""
            if self.groupingCheckBox.isChecked():
                # print("Checked")
                selectid = f"group_concat({selectid}) AS id,group_concat(distinct new.\"@user\") AS users,max(substr(new.\"@timestamp\",1,10)) AS latest_timestamp, "
                if mode != "highway":
                    selectid += "new.highway,"
                selectid += f"(old.{mode} || \"→\" || new.{mode}) AS {mode}_change"
                groupingstmt = f" GROUP BY (old.{mode} || \"→\" || new.{mode})"
            else:
                # print("Unchecked")
                selectid += " AS id,('http://localhost:8111/import?url=https://www.openstreetmap.org/' || new.\"@type\" || '/' || new.\"@id\") AS url,new.\"@user\" AS user,substr(new.\"@timestamp\",1,10) AS timestamp,"
                if mode != "highway":
                    selectid += "new.highway, "
                if mode == "highway":
                    selectid += "new.name, "
                selectid += f"old.{mode} AS old_{mode}, new.{mode} AS new_{mode}"

            # Construct the query
            sql = f"SELECT {selectid}, NULL AS \"notes\" FROM {oldFileValue} AS old LEFT OUTER JOIN {newFileValue} AS new ON new.\"@id\" = old.\"@id\" WHERE old.{mode} NOT LIKE new.{mode}{groupingstmt}"
            print(sql)

            with open(outputFileValue + "_" + mode + ".csv", "w") as outputFile:
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
                    sql,input_params)
                q_output_printer = QOutputPrinter(
                    output_params)
                q_output_printer.print_output(outputFile,sys.stderr,q_output)
                print("Complete")
                # Insert completion feedback here

def main():
    app = QtWidgets.QApplication(sys.argv)
    # Enable High DPI display with PyQt5
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    form = MainApp()
    form.show()
    app.exec_()



if __name__ == '__main__':
    main()
