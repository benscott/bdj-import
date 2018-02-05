
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

    occurences = OrderedDict()

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
        'catalogueNumber',
        'taxonConceptID',
        'country',
        'stateProvince',
    ]

    def __init__(self):
        self.species_descriptions = SpeciesDescriptions()
        self.figures = Figures()
        self._parse_data()

    def vouchers(self):
        # If this is a voucher specimen, we want to include it
        # otherwise we'll skip it
        for taxon, occurence in self.occurences.items():
            if self._is_voucher(occurence):
                yield taxon, occurence

    @staticmethod
    def _is_voucher(occurence):
        type_status = occurence.get('typestatus')
        return type_status and type_status.lower() == 'voucher'

    @property
    def tree(self):
        tree = {}
        for taxon, occurence in self.occurences.items():
            if self._is_voucher(occurence):
                family = occurence.get('family')
                if family not in tree:
                    tree[family] = {
                        'vouchers': OrderedDict(),
                        'species_description': self.species_descriptions[family]
                    }
                tree[family]['vouchers'][taxon] = occurence
        return SortedDict(tree)

    def _parse_data(self):
        dwca = File('falklands-utf8.dwca.csv')

        for row in dwca:

            occurence = {
                k.lower(): normalize(v) for k, v in row.items() if k in self.occurence_fields and v
            }

            if not self._is_voucher(occurence):
                continue

            normalized_taxon = normalize(row['taxonConceptID'])
            try:
                self.occurences[normalized_taxon]
            except KeyError:

                self.occurences[normalized_taxon] = {
                    k.lower(): normalize(v) for k, v in row.items() if k in self.occurence_fields anv
                }
                # Add the species description
                self.occurences[normalized_taxon][
                    'species_description'] = self.species_descriptions[normalized_taxon]

                # Add figures
                if self.occurences[normalized_taxon]['species_description']:
                    tid = self.occurences[normalized_taxon][
                        'species_description'].tid
                    self.occurences[normalized_taxon][
                        'figures'] = self.figures[tid]

            finally:
                # Add material details
                self.occurences[normalized_taxon].setdefault('materials', []).append({
                    k.lower(): v for k, v in row.items() if k in self.material_fields and v
                })
