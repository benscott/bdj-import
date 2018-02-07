
import os
import csv
from bdj_import.lib.helpers import normalize
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from sortedcontainers import SortedDict
import logging

from bdj_import.lib.file import File
from bdj_import.lib.species_descriptions import SpeciesDescriptions
from bdj_import.lib.figures import Figures
from bdj_import.lib.family_treatment import FamilyTreatment
from bdj_import.lib.species_treatment import SpeciesTreatment


logger = logging.getLogger()


class TaxonTreatments():

    def __init__(self):
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
        species_descriptions = SpeciesDescriptions()
        figures = Figures()
        dwca = File('falklands-utf8.dwca.csv')

        for row in dwca:

            # We are only interested in voucher specimens
            type_status = row.get('typeStatus', None)

            if type_status and type_status.lower() == 'voucher':

                family = normalize(row.get('family'))

                # Ensure the family exists
                try:
                    self._data[family]
                except KeyError:
                    self._data[family] = FamilyTreatment(
                        taxon=family,
                        description=species_descriptions.get_family(family)
                    )

                normalized_taxon = normalize(row['taxonConceptID'])

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
                        row.get(col)) for fld, col in treatment_taxonomy_fields}

                    species = SpeciesTreatment(
                        taxon=normalized_taxon,
                        description=treatment_description,
                        taxonomy=treatment_taxonomy,
                        figures=treatment_figures,
                    )

                    self._data[family].add_species(species)

                # Add material
                species.add_material(row)
