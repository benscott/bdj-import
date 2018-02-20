from bdj_import.lib.dwca.taxon import Taxon
from sortedcontainers import SortedDict


class FamilyTaxon(Taxon):

    def __init__(self, **kwargs):
        self.species_treatments = SortedDict()
        super(FamilyTaxon, self).__init__(**kwargs)

    def add_species(self, species):
        self.species_treatments[species.scientific_name] = species

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

    def __repr__(self):
        return 'Family ({})'.format(self.scientific_name)
