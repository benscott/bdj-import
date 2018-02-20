import re
from fuzzywuzzy import fuzz

from bdj_import.lib.dwca.taxon import Taxon
from bdj_import.lib.helpers import normalize


class SpeciesTaxon(Taxon):

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

    def __init__(self, **kwargs):
        self.fields = self._parse_species_description(
            kwargs.get('description'))
        super(SpeciesTaxon, self).__init__(**kwargs)
        self.re = re.compile(r'(sp.\s?[0-9])$')

    def add_material(self, data):
        self.materials.append({
            k.lower(): normalize(v) for k, v in data.items() if k in self.material_fields and v
        })

    @property
    def species(self):
        return self.re.sub('', self.scientific_name).strip()

    @property
    def taxon_authors(self):
        """
        We don't want sp.x italicised, so add as taxon authors
        """

        m = self.re.search(self.scientific_name)
        return m.group(1)

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
        return 'Species ({})'.format(self.scientific_name)
