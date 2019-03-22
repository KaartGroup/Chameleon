# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets

class UIForm(object):
    """

    UI class for the progress bar.

    """
    def setup_ui(self, Form):
        """
        Builds the widget tree on the parent widget.
        Sets up the appearance for progress bar box; 
        dimensions, text, and GUI form.

        Parameters
        ---------
        Form : QObject
            PyQt object for UI functionality
        """
        Form.setObjectName("Form")
        Form.resize(250, 84)
        self.progressBar = QtWidgets.QProgressBar(Form)
        self.progressBar.setGeometry(QtCore.QRect(30, 30, 250, 60))
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.progressBar.sizePolicy().hasHeightForWidth())
        self.progressBar.setSizePolicy(sizePolicy)
        self.progressBar.setMinimumSize(QtCore.QSize(200, 60))
        self.progressBar.setMaximumSize(QtCore.QSize(200, 60))
        self.progressBar.setProperty("value", 0)
        self.progressBar.setObjectName("progressBar")
        self.retranslate_ui(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslate_ui(self, Form):
        """
        Member function that handles translation of string 
        properties of form.

        Parameters
        ---------
        Form : QObject
            PyQt object for UI functionality
        """
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Processing..."))
