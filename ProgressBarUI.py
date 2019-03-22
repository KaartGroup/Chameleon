# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets

class UIForm(object):
    def setup_UI(self, Form):
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
        self.retranslate_UI(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslate_UI(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Processing..."))
