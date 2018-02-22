
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

            # Ensure the family exists
            try:
                self._data[family]
            except KeyError:
                family_species_description = species_descriptions.get_family(
                    family)

                self._data[family] = FamilyTaxon(
                    taxon_concept_id=family,
                    # In the DWCA we have no details for the family
                    # So retrieve the scientific name from the species
                    # description
                    scientific_name=family_species_description.scientific_name,
                    description=family_species_description
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

                scientific_name = normalize(row.get('scientificName')) if row.get(
                    'scientificName') else normalized_taxon
                species = SpeciesTaxon(
                    taxon_concept_id=normalized_taxon,
                    scientific_name=scientific_name,
                    description=treatment_description,
                    figures=treatment_figures,
                )

                self._data[family].add_species(species)

            # Add material
            species.add_material(row)
