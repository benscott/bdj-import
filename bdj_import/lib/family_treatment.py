from bdj_import.lib.treatment import Treatment
from sortedcontainers import SortedDict


class FamilyTreatment(Treatment):

    def __init__(self, **kwargs):
        self.species_treatments = SortedDict()
        super(FamilyTreatment, self).__init__(**kwargs)

    def add_species(self, species):
        self.species_treatments[species.taxon] = species

    def get_species(self, taxon):
        return self.species_treatments.get(taxon, None)

    def list_species(self):
        return self.species_treatments.values()

    @property
    def taxon_authors(self):
        """
        Include the full scientific name in the taxon authors field
        So that it is completely unitalicized
        """
        return self.description.scientific_name

    @property
    def notes(self):
        return self.description.paragraphs
