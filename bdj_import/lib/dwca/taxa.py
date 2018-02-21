
from bdj_import.lib.helpers import normalize
from sortedcontainers import SortedDict
import logging

from bdj_import.lib.file import File

from bdj_import.lib.scratchpads.descriptions import Descriptions
from bdj_import.lib.scratchpads.figures import Figures


from bdj_import.lib.dwca.family import FamilyTaxon
from bdj_import.lib.dwca.species import SpeciesTaxon


logger = logging.getLogger()


class DWCATaxa():

    # List of taxa to exlude
    excluded_taxa = [
        'Sigambra sp. 1',
        'Phylo cf. felix juv.',
        'Ilyphagus sp.'
    ]

    def __init__(self, file_name):
        self.file_name = file_name
        self._data = SortedDict()
        self._parse_data()

    def __iter__(self):
        return iter(self._data)

    def keys(self):
        return self._data.keys()

    def items(self):
        return self._data.items()

    def values(self):
        return self._data.values()

    def _parse_data(self):
        species_descriptions = Descriptions()
        figures = Figures()
        dwca = File(self.file_name)

        for row in dwca:

            family = normalize(row.get('family'))
            # If there's no family (often EOF) then skip
            if not family:
                continue

            normalized_taxon = normalize(row['taxonConceptID'])

            # If this is a taxon to be excluded continue to next
            if normalized_taxon in self.excluded_taxa:
                continue

            # Ensure the family exists
            try:
                self._data[family]
            except KeyError:
                self._data[family] = FamilyTaxon(
                    scientific_name=family,
                    description=species_descriptions.get_family(family)
                )

            species = self._data[family].get_species(normalized_taxon)

            if not species:

                treatment_description = species_descriptions[
                    normalized_taxon]

                if treatment_description:
                    treatment_figures = figures[treatment_description.tid]
                else:
                    treatment_figures = None
                    logger.warning('No species description for %s',
                                   normalized_taxon)

                treatment_taxonomy_fields = [
                    ('genus', 'genus'),
                    ('subgenus', 'subgenus'),
                    ('family', 'family'),
                    ('taxon_authors', 'scientificNameAuthorship'),
                    ('specific_epithet', 'specificEpithet'),
                ]

                treatment_taxonomy = {fld: normalize(
                    row.get(col)) for fld, col in treatment_taxonomy_fields if row.get(col, None)}

                species = SpeciesTaxon(
                    scientific_name=normalized_taxon,
                    description=treatment_description,
                    taxonomy=treatment_taxonomy,
                    figures=treatment_figures,
                )

                self._data[family].add_species(species)

            # Add material
            species.add_material(row)
