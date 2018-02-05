import re

from bdj_import.lib.file import File
from bdj_import.lib.description import Description
from bdj_import.lib.helpers import normalize


class SpeciesDescriptions(object):

    descriptions = []
    families = {}

    def __init__(self):
        self._parse_data()

    def _parse_data(self):

        for row in File('species-description-export.csv'):

            # If this is of rank family, index by family name
            # Otherwise index by title /classification
            # (which does actually includes species, genus & unranked)
            if row['Rank'] and row['Rank'].lower() == 'family':
                family = self._extract_family(row['Classification'])
                idx = [family]
            else:
                idx = [
                    # Matching taxon can be either title or classification
                    normalize(row['Title']),
                    normalize(row['Classification'])
                ]
            desc = Description(
                body=row['Body'],
                tid=row['TID'],
                index=set(idx),
                scientific_name=row['Classification']
            )
            self.descriptions.append(desc)

    @staticmethod
    def _extract_family(scientific_name):
        """
        Extract the family part from a scientific name
        """
        m = re.match(r'([^\s]+)', scientific_name)
        return m.group(1)

    def __getitem__(self, taxon):
        for description in self.descriptions:
            if description.matches(taxon):
                return description
