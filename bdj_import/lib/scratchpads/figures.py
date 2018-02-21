

from bdj_import.lib.file import File


class Figures(object):
    """
    Extract data from the exported image files
    """
    _data = {}
    file_name = 'scratchpads/image-export.csv'

    def __init__(self):
        for row in File(self.file_name):
            self._data.setdefault(row['TID'], []).append(
                {
                    'description': row['Description'],
                    'path': row['Path'].replace('/files/', '/files/styles/large/public/'),
                })

    def __getitem__(self, tid):
        try:
            return self._data[tid]
        except KeyError:
            return None
