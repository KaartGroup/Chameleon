#!/usr/bin/env python3
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
import design
import os
import subprocess

class ExampleApp(QtWidgets.QMainWindow, design.Ui_MainWindow):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__()
        self.setupUi(self)
        self.oldFileSelectButton.clicked.connect(self.open_old_file)
        self.newFileSelectButton.clicked.connect(self.open_new_file)
        self.outputFileSelectButton.clicked.connect(self.output_file)
        # self.groupingCheckBox.clicked.connect(self.)
        self.runButton.clicked.connect(self.run_query)
    def open_old_file(self):
        oldFileName, _filter = QtWidgets.QFileDialog.getOpenFileName(self, "Select CSV file with old data", os.path.expanduser("~/Documents"), "CSV (*.csv)")
        if oldFileName:
            self.oldFileNameBox.insert(oldFileName)
    def open_new_file(self):
        newFileName, _filter = QtWidgets.QFileDialog.getOpenFileName(self, "Select CSV file with new data", os.path.expanduser("~/Documents"), "CSV (*.csv)")
        if newFileName:
            self.newFileNameBox.insert(newFileName)
    def output_file(self):
        outputFileName, _filter = QtWidgets.QFileDialog.getSaveFileName(self, "Save output file", os.path.expanduser("~/Documents"), "CSV (*.csv)")
        if outputFileName:
            self.outputFileNameBox.insert(outputFileName)
    def run_query(self):
        oldFileValue = self.oldFileNameBox.text()
        newFileValue = self.newFileNameBox.text()
        outputFileValue = self.outputFileNameBox.text()
        # Begin code that I actually wrote
        # Get just the input filenames (with extensions) from the full path
        # oldNameExt = os.path.basename(oldFileName)
        # newNameExt = os.path.basename(newFileName)
        #
        # # Get the filenames *without* extensions
        # oldName = os.path.splitext(oldFileName)
        # newName = os.path.splitext(newFileName)

        # Creating SQL snippets
        selectid = "substr(new.\"@type\",1,1) || new.\"@id\""

        # if groupingenabled:
        #     selectid = "group_concat($selectid) AS id, new.highway, (old.ref || \"→\" || new.ref) AS ref_change"
        #     groupingstmt = " GROUP BY (old.ref || \"→\" || new.ref)"
        # else:
        selectid += " AS id,('www.openstreetmap.org/' || new.\"@type\" || '/' || new.\"@id\") AS url,new.highway, old.ref AS old_ref, new.ref AS new_ref"

        # Construct the query
        sql = "SELECT " + selectid + " FROM " + oldFileValue + " AS old LEFT OUTER JOIN " + newFileValue + " AS new ON new.\"@id\" = old.\"@id\" WHERE old.ref NOT LIKE new.ref"

        outputFile = open(outputFileValue, "w")
        subprocess.call(['q', '-H', '-O', '-t', sql], stdout=outputFile)
        outputFile.close()

def main():
    app = QtWidgets.QApplication(sys.argv)
    form = ExampleApp()
    form.show()
    app.exec_()



if __name__ == '__main__':
    main()
