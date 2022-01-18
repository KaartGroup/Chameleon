"""
Extension of QLineEdit that accepts files dragged onto it from the system's file browser and
extracts their paths
"""

import logging
from pathlib import Path

from PySide6.QtWidgets import QLineEdit, QToolTip

logger = logging.getLogger(__name__)


class QLineEditDragDrop(QLineEdit):
    """
    Promoted QLineEdit widget to allow for drag and drop option
    using MIME object.
    """

    def __init__(self, parent=None):
        super().__init__()

    # Overriding default dragEnterEvent()
    def dragEnterEvent(self, event):
        """
        Overriding default dragEnterEvent from QEvent to only accept
        text data from MIME object.
        """
        # Grab filepath from MIME object (Q's drag&drop data type)
        # If more than one file is selected, only the first will be used
        file_path = Path(event.mimeData().urls()[0].toLocalFile())
        if file_path.suffix == ".csv":
            logger.debug(f"Drag enter accepted, {file_path}")
            event.accept()
        else:
            # Error prompt for when dragged object is not valid type
            error_prompt = "Please provide a .csv file."
            QToolTip.showText(
                self.mapToGlobal(self.rect().topRight()),
                error_prompt,
                self,
                self.rect(),
                1000,
            )
            event.ignore()

    # Overriding default dropEvent()
    def dropEvent(self, event):
        """
        Overriding default dropEvent from QEvent to perform setText()
        on QLineEdit object on MainApp form.

        Raises
        ------
        FileTypeError
            If dropped file is not ".csv" type.
        """
        # If more than one file is dragged in, we will only accept the first selected
        file_path = Path(event.mimeData().urls()[0].toLocalFile())
        logger.debug("data: ", str(file_path))
        if file_path.suffix == ".csv":  # Check to see if file is .csv
            logger.debug(f"Text to enter is {file_path}")
            # Accept dropEvent
            event.accept()
            logger.debug(f"setting text to new box, {file_path}")
            # Inherits QLineEdit from main.py (self)
            self.selectAll()
            self.insert(str(file_path))
        else:
            # Silently ignore the dropEvent()
            event.ignore()
