import abc


class Taxon(object):

    def __init__(self, taxon_concept_id, scientific_name, description, figures=[]):

        self.taxon_concept_id = taxon_concept_id
        self.scientific_name = scientific_name
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
