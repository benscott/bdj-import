import re
import logging

from bdj_import.lib.file import File
from bdj_import.lib.scratchpads.description import Description
from bdj_import.lib.helpers import normalize


logger = logging.getLogger()


class Descriptions(object):

    file_name = 'scratchpads/species-description-export.csv'
    term_mappings_file_name = 'scratchpads/term_mappings.csv'

    def __init__(self):
        self.scratchpad_term_mappings = self._get_term_mappings()
        self.descriptions = []
        self._parse_data()

    def _get_term_mappings(self):
        # Build a dictionary of term mappings, from DWCA file taxon
        # concepts to their equivalent on scratchpads
        mappings = {}
        for row in File(self.term_mappings_file_name):
            if row['Scratchpad']:
                mappings[row['taxonConcept']] = row['Scratchpad']
        return mappings

    def _parse_data(self):

        for row in File(self.file_name):

            # If this is of rank family, index by family name
            # Otherwise index by title /classification
            # (which does actually includes species, genus & unranked)

            rank = row.get('Rank', 'species').lower()

            if rank == 'family':
                family = self._extract_family(row['Classification'])
                idx = [
                    family,
                    normalize(row['Classification']),
                    normalize(row['Title']),
                ]
            else:
                idx = [
                    # Matching taxon can be either title or classification
                    normalize(row['Title']),
                    normalize(row['Classification'])
                ]

            desc = Description(
                body=row['Body'],
                tid=row['Term ID'],
                index=set([self._normalize_index(i) for i in idx]),
                scientific_name=row['Classification'],
                rank=rank
            )
            self.descriptions.append(desc)

    @staticmethod
    def _extract_family(scientific_name):
        """
        Extract the family part from a scientific name
        """
        m = re.match(r'([^\s]+)', scientific_name)
        return m.group(1)

    def get_family(self, taxon):
        return self._get(taxon, 'family')

    def __getitem__(self, taxon):
        return self._get(taxon)

    @staticmethod
    def _normalize_index(term):
        """
        To help fix typos etc., remove all white space and dots
        Before indexing / lookup
        """
        return term.replace(' ', '').replace('.', '')

    def _get(self, taxon, rank=None):

        # Does the taxon map to a different one on Scratchpads?
        try:
            scratchpad_taxon = self.scratchpad_term_mappings[taxon]
        except KeyError:
            pass
        else:
            logger.warning('Using alternative term mapping %s => %s',
                           taxon, scratchpad_taxon)
            taxon = scratchpad_taxon

        for description in self.descriptions:
            if description.matches(self._normalize_index(taxon), rank):
                return description
