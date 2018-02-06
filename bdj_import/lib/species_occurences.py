
import os
import csv
from bdj_import.lib.helpers import normalize
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from collections import OrderedDict
from sortedcontainers import SortedDict


from bdj_import.lib.file import File
from bdj_import.lib.species_descriptions import SpeciesDescriptions
from bdj_import.lib.figures import Figures


class SpeciesOccurences():

    _occurences = OrderedDict()

    occurence_fields = [
        'subgenus',
        'genus',
        'family',
        'scientificName',
        'scientificNameAuthorship',
        'specificEpithet',
        'typeStatus'
    ]

    # Fields to include in material detail
    material_fields = [
        'family',
        'scientificName',
        'kingdom',
        'phylum',
        'class',
        'waterBody',
        'stateProvince',
        'locality',
        'verbatimLocality',
        'maximumDepthInMeters',
        'locationRemarks',
        'decimalLatitude',
        'decimalLongitude',
        'geodeticDatum',
        'samplingProtocol',
        'eventDate',
        'eventTime',
        'fieldNumber',
        'fieldNotes',
        'individualCount',
        'preparations',
        'catalogNumber',
        'taxonConceptID',
        'country',
        'stateProvince',
    ]

    def __init__(self):
        self.species_descriptions = SpeciesDescriptions()
        self.figures = Figures()
        self._parse_data()

    def __iter__(self):
        return iter(self._occurences)

    def keys(self):
        return self._occurences.keys()

    def items(self):
        return self._occurences.items()

    def values(self):
        return self._occurences.values()

    @property
    def tree(self):
        tree = {}
        for taxon, occurence in self.items():
            family = occurence.get('family')
            if family not in tree:
                tree[family] = {
                    # Don't need to sort  -  _occurences is already sorted
                    # alphabetically
                    'taxa': [],
                    'species_description': self.species_descriptions[family]
                }
            # We're only using taxon concept id - do we want to include
            # family & genus at this point?
            tree[family]['taxa'].append(taxon)

        return SortedDict(tree)

    def _parse_data(self):
        dwca = File('falklands-utf8.dwca.csv')

        for row in dwca:

            # We are only interested in
            type_status = row.get('typeStatus', None)
            if type_status and type_status.lower() == 'voucher':

                normalized_taxon = normalize(row['taxonConceptID'])
                try:
                    self._occurences[normalized_taxon]
                except KeyError:
                    self._occurences[normalized_taxon] = {
                        k.lower(): normalize(v) for k, v in row.items() if k in self.occurence_fields and v
                    }
                    # Add the species description
                    self._occurences[normalized_taxon][
                        'species_description'] = self.species_descriptions[normalized_taxon]

                    # Add figures
                    if self._occurences[normalized_taxon]['species_description']:
                        tid = self._occurences[normalized_taxon][
                            'species_description'].tid
                        self._occurences[normalized_taxon][
                            'figures'] = self.figures[tid]

                finally:
                    # Add material details
                    self._occurences[normalized_taxon].setdefault('materials', []).append({
                        k.lower(): v for k, v in row.items() if k in self.material_fields and v
                    })
