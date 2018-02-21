import abc


class Taxon(object):

    def __init__(self, scientific_name, description, taxonomy=[], figures=[]):

        self.scientific_name = scientific_name
        self.taxonomy = taxonomy
        self.description = description
        self.figures = figures
        self.materials = []

    @property
    def tid(self):
        try:
            return self.description.tid
        except AttributeError:
            return None

    @abc.abstractproperty
    def diagnosis(self):
        return None

    @abc.abstractproperty
    def notes(self):
        return None
