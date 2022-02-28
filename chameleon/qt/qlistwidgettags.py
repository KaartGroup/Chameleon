import logging
from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget

from chameleon.core import SPECIAL_MODES, clean_for_presentation

logger = logging.getLogger(__name__)


class QListWidgetTags(QListWidget):
    """
    QListWidget that enforces unique values and has methods for removing
    or clearing entries
    """

    def __init__(self, parent=None):
        super().__init__()

    def add_tags_to_list(self, tags: str | Iterable[str]) -> None:
        if isinstance(tags, str):
            tags = [tags]

        for count, tag in enumerate(tags):
            tag = clean_for_presentation(tag)
            if existing_item := next(
                iter(self.findItems(tag, Qt.MatchExactly)),
                None,
            ):
                # Clear the prior selection on the first iteration only
                if count == 0:
                    self.selectionModel().clear()
                existing_item.setSelected(True)
                logger.warning("%s is already in the list.", tag)
            else:
                self.addItem(tag)
                logger.info("Adding to list: %s", tag)

    def delete_tag(self) -> None:
        """
        Clears selected list items with "Delete" button.
        Execute on `Delete` button signal.
        """
        try:
            # Remove selected items in user-selected Qlist
            for item in self.selectedItems():
                self.takeItem(self.row(item))
                logger.info("Deleted %s from processing list.", (item.text()))
        # Fails silently if nothing is selected
        except AttributeError:
            logger.exception()

    def clear_tag(self) -> None:
        """
        Wipes all tags listed on QList with "Clear" button.
        Execute on `Clear` button signal.
        """
        for row in (
            self.row(item)
            for item in self.findItems("*", Qt.MatchWildcard)
            if item.text() not in SPECIAL_MODES
        ):
            self.takeItem(row)
        logger.info("Cleared tag list.")

    @property
    def modes_inclusive(self) -> set:
        """
        Returns modes including the special "new" and "deleted" modes
        """
        return {item.text() for item in self.findItems("*", Qt.MatchWildcard)}

    @property
    def modes(self) -> set:
        """
        Returns the modes the user has input as a set,
        ignoring the special "new" and "deleted" modes
        """
        return {
            mode for mode in self.modes_inclusive if mode not in SPECIAL_MODES
        }
