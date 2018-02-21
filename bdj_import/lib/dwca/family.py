from bdj_import.lib.dwca.taxon import Taxon
from sortedcontainers import SortedDict


class FamilyTaxon(Taxon):

    FAMILY = 0
    TAXON_AUTHORS = 1

    def __init__(self, **kwargs):
        self.species_treatments = SortedDict()
        super(FamilyTaxon, self).__init__(**kwargs)
        self._scientific_name_parts = self._split_scientific_name()

    def add_species(self, species):
        self.species_treatments[species.scientific_name] = species

    def get_species(self, taxon):
        return self.species_treatments.get(taxon, None)

    def list_species(self):
        return self.species_treatments.values()

    @property
    def taxon_authors(self):
        """
        Return the taxon author part of the scientific name string (after
        the first space)
        """
        return self._scientific_name_parts[self.TAXON_AUTHORS]

    @property
    def family_name(self):
        """
        Return first part of the scientifc name (before space)
        """
        return self._scientific_name_parts[self.FAMILY]

    def _split_scientific_name(self):
        """
        Split species description scientific name on first space
        Everyting after first space will be taxon author part        
        Returns:
            TYPE: Description
        """
        return self.description.scientific_name.split(' ', 1)

    @property
    def notes(self):
        return self.description.paragraphs

    def __repr__(self):
        return 'Family ({})'.format(self.scientific_name)
