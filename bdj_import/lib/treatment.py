import abc


class Treatment(object):

    def __init__(self, taxon, description, taxonomy=[], figures=[]):

        self.taxon = taxon
        self.taxonomy = taxonomy
        self.description = description
        self.figures = figures
        self.materials = []

    def __repr__(self):
        return 'Treatment ({})'.format(self.taxon)

    @abc.abstractproperty
    def diagnosis(self):
        return None

    @abc.abstractproperty
    def notes(self):
        return None
