import re
from fuzzywuzzy import fuzz

from bdj_import.lib.dwca.taxon import Taxon
from bdj_import.lib.helpers import normalize, strip_parenthesis


class SpeciesTaxon(Taxon):

    # Fields to include in material detail
    material_fields = [
        # 'country',
        # 'family',
        # 'locality',
        # 'taxonConceptID',
        # 'waterBody',
        'catalogNumber',
        # 'class',
        'decimalLatitude',
        'decimalLongitude',
        'eventDate',
        'eventTime',
        # 'fieldNotes',
        'fieldNumber',
        # 'geodeticDatum',
        'individualCount',
        # 'kingdom',
        # 'locationRemarks',
        'maximumDepthInMeters',
        # 'phylum',
        # 'preparations',
        'samplingProtocol',
        # 'scientificName',
        # 'stateProvince',
        # 'verbatimLocality',
    ]

    def __init__(self, **kwargs):
        self.fields = self._parse_species_description(
            kwargs.get('description'))
        super(SpeciesTaxon, self).__init__(**kwargs)
        self.re = re.compile(r'(sp.\s?[0-9][a-zA-Z]{0,2})$')
        self.materials = []

    def add_material(self, data):

        # Prepend 'sample' to field number
        data['fieldNumber'] = 'Sample {}'.format(data['fieldNumber'])
        material = {
            k.lower(): normalize(v) for k, v in data.items() if k in self.material_fields and v
        }
        material['type_status'] = self._get_type_status(data)
        self.materials.append(material)

    def get_materials_ordered_by_type(self):
        """
        Return a list of materials ordered by type status:
            Holotype
            Paratypes
            Other material
        """
        type_status_order = [
            'Holotype',
            'Paratype',
            'Other material'
        ]
        return sorted(self.materials, key=lambda k: type_status_order.index(k['type_status']))

    @staticmethod
    def _get_type_status(data):
        return data.get('typeStatus').capitalize()

    @property
    def species(self):
        return self.re.sub('', self.taxon_concept_id).strip()

    @property
    def specific_epithet(self):
        m = self.re.search(self.taxon_concept_id)
        try:
            return m.group(1)
        except AttributeError:
            # Not all scientific names include specific epithet
            return None

    @property
    def taxon_authors(self):
        """
        We don't want sp.x italicised, so add sp 1. as taxon authors
        """
        if self.specific_epithet:
            return self.specific_epithet
        else:
            return self._get_authority_from_scientific_name()

    def _get_authority_from_scientific_name(self):
        """
        Scientific name includes authority, so extract
        By replacing the entire taxon concept part
        """
        # Some taoxn concept / scientific names have non-matching
        # parenthesis - so strip them out before doing the re
        scientific_name_without_parenthesis = strip_parenthesis(
            self.scientific_name)
        taxon_concept_id_without_parenthesis = strip_parenthesis(
            self.taxon_concept_id)
        # Only strip if the taxon concept string exists in the scientific name string
        # If it doesn't we return the whole scientific name which is wrong
        if taxon_concept_id_without_parenthesis in scientific_name_without_parenthesis:
            authority = scientific_name_without_parenthesis.replace(
                taxon_concept_id_without_parenthesis, '')
            return strip_parenthesis(authority.strip())

    @property
    def notes(self):
        return self.fields.get('remarks', [])

    @property
    def diagnosis(self):
        return self.fields.get('diagnosis')

    def _parse_species_description(self, description):
        """
        Parse body text, splitting into voucher diagnosis & remarks
        """
        fields = {}
        field_names = ['voucher', 'diagnosis', 'remarks']
        # The body contains the taxonomy in headers at the top
        # Which needs to be stripped out, otherwise will duplicate data in
        # publication proper - so match the strong content
        # If we match on classification, we end up stripping out content from later in the
        # process e.g. tables with taxonomy in the description
        # instead we wait until the first paragraph matching Voucher, Diagnosis or Remarks
        # and discard all previous paragraphs

        # Loop through all of the strong tags, and see if it's voucher, diagnosis etc.,
        # If it is, then set the current field - used to key
        current_field = None
        if description:
            for p in description.paragraphs:
                for strong in p.find_all("strong"):
                    for field_name in field_names:
                        strong_text = strong.getText().lower()
                        fuzz_ratio = fuzz.partial_ratio(
                            field_name, strong_text)
                        if fuzz_ratio > 99:
                            current_field = field_name
                            # Remove the strong label text
                            strong.extract()

                if current_field:
                    fields.setdefault(current_field, []).append(p)

        return fields

    def __repr__(self):
        return 'Species ({})'.format(self.taxon_concept_id)
