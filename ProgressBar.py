from PyQt5 import QtCore, QtGui, QtWidgets
import sys

from ProgressBarUI import UIForm

class ProgressBar(QtWidgets.QDialog, UIForm):
    """

    Class representing Chameleon progress bar, initiating UI and functionality.

    """
    def __init__(self, desc=None, parent=None):
        """
        Parameters
        ----------
        desc : str
            The title of the progress bar window (default is None)
        """
        super(ProgressBar, self).__init__(parent)
        self.setup_UI(self)
        self.show()
        if desc != None:
            self.set_description(desc)

    def set_value(self, val):
        """
        Sets the value for the stepping necessary to move the progress bar.

        Parameters
        ----------
        val : int
            The int value to be set on the progress bar
        """
        self.progressBar.setProperty("value", val)

    def set_description(self, desc):
        """
        Sets the title for the progress bar window

        Parameters
        ----------
        desc : str
            The title of the progress bar window
        """
        self.setWindowTitle(desc)


def main():
    """
    Creates a new instance of the QtWidget application, sets the form to be
    out MainWIndow (design) and executes the application.
    """
    # A new instance of QApplication
    app = QtWidgets.QApplication(sys.argv)
    # We set the form to be our MainWindow (design)
    form = ProgressBar('pbar')
    app.exec_()                                 # and execute the app


if __name__ == '__main__':
     """ Executes only if we're running file directly and not importing it. """
     main()
