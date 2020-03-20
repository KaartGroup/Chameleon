from pathlib import Path as _Path


class Path(_Path):
    """
    Adding a method to the standard Path
    """

    def __init__(self):
        super().__init__()

    def dir_uri(self) -> str:
        """
        Return the URI of the nearest directory,
        which can be self if it is a directory
        or else the parent
        """
        if not self.is_dir():
            return self.parent.as_uri()
        else:
            return self.as_uri()
