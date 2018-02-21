import csv
import os
import pkg_resources


class File(object):

    def __init__(self, file_name):
        dir = os.path.abspath(
            pkg_resources.resource_filename('bdj_import', 'data'))

        f = open(os.path.join(dir, file_name), 'r')
        self.reader = csv.DictReader(f)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.reader)
