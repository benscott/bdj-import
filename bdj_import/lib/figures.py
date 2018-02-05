

from bdj_import.lib.file import File
from bdj_import.lib.helpers import normalize


class Figures(object):
    """
    Extract data from the exported image files
    """
    _data = {}

    def __init__(self):
        for row in File('image-export.csv'):
            self._data.setdefault(row['TID'], []).append(
                {
                    'description': row['Description'],
                    'path': row['Path'].replace('/files/', '/files/styles/large/public/'),
                })

    def __getitem__(self, tid):
        return self._data[tid]
