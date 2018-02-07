import re
from fuzzywuzzy import fuzz

from bdj_import.lib.treatment import Treatment
from bdj_import.lib.helpers import strip_parenthesis, normalize


class SpeciesTreatment(Treatment):

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
        super(SpeciesTreatment, self).__init__(**kwargs)

    def add_material(self, data):
        self.materials.append({
            k.lower(): normalize(v) for k, v in data.items() if k in self.material_fields and v
        })

    @property
    def species(self):
        # We do not want to include the specific_epithet if it's sp.
        # as then it will be italicized - it will be added to the authors
        species = self.taxonomy.get('specific_epithet', None)
        if not self._is_abbreviated_specific_name():
            if 'cf.' in self.taxon:
                species = 'cf. {}'.format(species)
            return species

    @property
    def genus(self):
        genus = self.taxonomy.get('genus', None)
        # We have no genus - so if the species name is just sp 1. it will
        # look incorrect - so try and get the genus from the scientific name
        if not genus and self.specific_epithet == 'sp. 1':
            genus = self.taxon.replace(self.specific_epithet, '')
        return genus

    @property
    def subgenus(self):
        subgenus = self.taxonomy.get('subgenus', None)
        if subgenus:
            # Replace any parenthesis - these are added in the BDJ
            subgenus = strip_parenthesis(subgenus)
        return subgenus

    @property
    def taxon_authors(self):

        # Some taxonomic concepts include sub-specific(?) epithets
        # E.G. Aphelochaeta sp. 5fA, Aphelochaeta sp. 5fb
        # Which need to be included in the taxonomic treatment
        # So we'll try and extract the subspecific epithet from the
        # taxon concept id
        if self._is_abbreviated_specific_name():
            specific_epithet = self.taxonomy.get('specific_epithet')
            pattern = r'({}\s?\w+)'.format(specific_epithet)
            m = re.search(pattern, self.taxon)

            try:
                return m.group(0)
            except AttributeError:
                return specific_epithet

        taxon_authors = self.taxonomy.get('taxon_authors', None)

        if taxon_authors:
            # Strip and re-wrap taxon authors in parenthesis
            taxon_authors = '({0})'.format(
                strip_parenthesis(taxon_authors).strip()
            )

        return taxon_authors

    @property
    def notes(self):
        return self.fields.get('remarks', [])

    @property
    def diagnosis(self):
        return self.fields.get('diagnosis')

    def _is_abbreviated_specific_name(self):
        return self.taxonomy.get('specific_epithet') == 'sp.'

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
