import re
import logging

from bdj_import.lib.file import File
from bdj_import.lib.scratchpads.description import Description
from bdj_import.lib.helpers import normalize


logger = logging.getLogger()


class Descriptions(object):

    # Some Scratchpad species descriptions are tagged with different terms
    # These provide mappings from DWCA => Scratchpad Term
    scratchpad_term_mappings = {
        'Amage scultpa': 'Amage Malmgren, 1866',
        'Ancistrosyllis cf groenlandica': 'Pilargidae de Saint-Joseph, 1899',
        'Apistobranchus sp. 1': 'Apistobranchidae Mesnil and Caullery, 1898',
        'Aricidea (Aedicira) antarctica': 'Aricidea (Allia) antarctica Hartmann-Schröder & Rosenfeldt, 1988',
        'Cirrophorus cf. furcatus': 'Cirrophorus Ehlers, 1908',
        'Cossura sp. 1': 'Cossuridae Day, 1963',
        'Desdemona? sp. 1': 'Desdemona Banse, 1957',
        'Eucranta mollis': 'Eucranta Malmgren, 1866',
        'Galathowenia sp. 1': 'Oweniidae Rioja, 1917',
        'Jasmineira cf. regularis': 'Jasmineira regularis form 2 Hartman, 1978',
        'Jasmineira cf. regularis (form 1)': 'Jasmineira regularis form 1 Hartman, 1978',
        'Jasmineira (Claviramus?) sp. 5': 'Claviramus Fitzhugh, 2002',
        'Myxicola cf. sulcata': 'Myxicola Koch in Renier, 1847',
        'Neoleanira magellanica': 'Sigalionidae (Neoleanira?) sp. 1',
        'Nichomache cf. lumbricalis': 'Nichomache Malmgren, 1865',
        'Paramphinome australis': 'Amphinomidae Lamarck, 1818',
        'Parexogone cf. wolfi': 'Exogone (Paraexogone) cf. wolfi San Martín, 1991',
        'Potamethus sp. 1': 'Potamethus Chamberlin, 1919',
        'Schistomeringos sp 1': 'Dorvilleidae Chamberlin, 1919',
        'Scolelepis sp. 1': 'Scololepis sp. 1',
        'Sternaspis sp. 1': 'Sternaspidae Carus, 1863'
    }

    file_name = 'scratchpads/species-description-export.csv'

    def __init__(self):
        self.descriptions = []
        self._parse_data()

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
