
import csv
import os
import re
import unicodedata
import xml.etree.cElementTree as ET
from bdj_import.api import API
from xml.dom import minidom
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from collections import OrderedDict


class Doc:

    classification_fields = [
        'scientificName',
        'kingdom',
        'phylum',
        'class',
        'genus',
        'subgenus',
        'specificEpithet',
        'scientificNameAuthorship',
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

    family_descriptions = {}
    species_descriptions = {}

    def __init__(self, limit=None):
        self.data_dir = os.path.join(os.path.dirname(
            __file__), 'data')

        self.root = ET.Element("document")
        self.limit = limit

        self.classification = self._parse_dwca()
        self._parse_species_descriptions()
        self._add_document_info()
        self._add_authors()
        self._add_objects()
        self._add_taxon_treatments()

    def _add_document_info(self):
        # Create document info
        document_info = ET.SubElement(self.root, "document_info")

        ET.SubElement(
            document_info, "document_type").text = 'Taxonomic Paper'
        ET.SubElement(
            document_info, "journal_name").text = 'Biodiversity Data Journal'

    def _add_authors(self):
        # Add authors
        authors = ET.SubElement(self.root, "authors")
        ET.SubElement(authors, "author", first_name='Ben',
                               last_name='Scott', co_author='1', email='ben@benscott.co.uk', right='1', submitting_author='1')

    def _add_objects(self):
        # Add the main document objects - these are all required to pass document
        # validation
        objects = ET.SubElement(self.root, "objects")
        article_metadata = ET.SubElement(objects, "article_metadata")
        ET.SubElement(objects, "introduction")
        ET.SubElement(objects, "materials_and_methods")
        ET.SubElement(objects, "data_resources")
        self.taxon_treatments = ET.SubElement(objects, "taxon_treatments")
        ET.SubElement(objects, "checklists")
        ET.SubElement(objects, "identification_keys")
        ET.SubElement(objects, "results")
        ET.SubElement(objects, "discussion")
        ET.SubElement(objects, "acknowledgements")
        ET.SubElement(objects, "author_contributions")
        ET.SubElement(objects, "references")
        ET.SubElement(objects, "supplementary_files")
        ET.SubElement(objects, "figures")
        ET.SubElement(objects, "tables")
        ET.SubElement(objects, "endnotes")

    def _parse_dwca(self):
        classification = {}
        fpath = os.path.join(self.data_dir, 'falklands-utf8.dwca.csv')
        with open(fpath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # If this is a voucher specimen, we want to include it
                # otherwise skip it
                type_status = row.get('typeStatus').strip()
                if type_status.lower() != 'voucher':
                    continue

                family = row['family'].strip()

                classification.setdefault(family, {})

                taxon = row.get('taxonConceptID')
                normalized_taxon = unicodedata.normalize("NFKD", taxon).strip()

                # We only want certain fields included
                data = {k.lower(): v for k, v in row.items()
                        if k in self.classification_fields and v}

                classification[family].setdefault(
                    normalized_taxon, []).append(data)

        return OrderedDict(sorted(classification.items()))

    def _parse_species_descriptions(self):

        # Read classification DWV
        fpath = os.path.join(
            self.data_dir, 'species-description-export.csv')

        with open(fpath, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:

                taxon = row['Classification']
                rank = row['Rank']

                # If this is family rank, then add to family_descriptions dict,
                # keyed by family name
                if rank == 'Family':
                    # Get the first part of the name
                    family_name = taxon.split(' ', 1)[0]

                    self.family_descriptions[family_name] = row['Body']

                else:
                    self.species_descriptions[taxon] = row['Body']

    @staticmethod
    def _species_description_strip_taxonomy(description):
        # Remove all of the extra taxonomy included in the body
        description_field_names = ['voucher', 'diagnosis', 'remarks']
        soup = BeautifulSoup(description, "html.parser")
        body = []

        is_body = False
        for p in soup.find_all("p"):
            # The body contains the taxonomy in headers at the top
            # Which needs to be stripped out, otherwise will duplicate data in
            # publication proper - so match the strong content
            # If we match on classification, we end up stripping out content from later in the
            # process e.g. tables with taxonomy in the description
            # instead we wait until the first paragraph matching Voucher, Diagnosis or Remarks
            # and discard all previous paragraphs

            if not is_body:

                # Loop through all of the strong tags, and see if it's voucher, diagnosis etc.,
                # This denotes the start of the main body
                for strong in p.find_all("strong"):
                    for description_field_name in description_field_names:
                        fuzz_ratio = fuzz.partial_ratio(
                            description_field_name, strong.getText().lower())
                        if fuzz_ratio > 99:
                            is_body = True

            if is_body:
                body.append(str(p))
        return ''.join(body)

    def _get_species_descriptions(self, classification):
        for taxon_field in ['taxonconceptid', 'scientificname']:
            try:
                taxon = classification[taxon_field]
            except KeyError:
                continue

            # Get rid of any odd characters and white space
            normalized_taxon = unicodedata.normalize("NFKD", taxon).strip()
            try:
                return self.species_descriptions[normalized_taxon]
            except KeyError:
                pass

    def _add_taxon_treatments(self):
        count = 0

        # description = self._species_description_strip_taxonomy(row[
        #     'Body'])
        # species_description.setdefault(
        #     taxon, []).append(description)

        print(self.family_descriptions)
        # As per Adrian's request, we want to structure the doc so
        # family are included
        for family, taxa in self.classification.items():

            print(family)
            print(self.family_descriptions[family])

            # try:

            # except KeyError:

            #     print(family)

        # for classification in self._iter_classification():
        #     if count >= self.limit:
        #         break
        #     # Ensure classification contains some terms we want
        #     # bool(empty dict) = False)
        #     if(bool(classification)):
        # descriptions = self._get_species_descriptions(classification)

        #         treatment = ET.SubElement(self.taxon_treatments, "treatment")
        #         # Add taxonomy fields
        #         treatment_fields = ET.SubElement(treatment, "fields")

        #         el = ET.Element('classification')
        #         ET.SubElement(el, "value").text = classification.get(
        #             'taxonconceptid')
        #         treatment_fields.append(el)

        #         el = ET.Element('rank')
        #         ET.SubElement(el, "value").text = 'Species'
        #         treatment_fields.append(el)

        #         el = ET.Element('type_of_treatment')
        #         ET.SubElement(el, "value").text = 'New taxon'
        #         treatment_fields.append(el)

        #         materials = ET.SubElement(treatment, "materials")
        #         material = ET.SubElement(materials, "material")
        #         material_fields = ET.SubElement(material, "fields")

        #         el = ET.Element('type_status')
        #         ET.SubElement(el, "value").text = 'Other material'
        #         material_fields.append(el)

        #         for fn, value in classification.items():
        #             el = ET.Element(fn)
        #             ET.SubElement(el, "value").text = value
        #             material_fields.append(el)

        #         if descriptions:
        #             treatment_descriptions = ET.SubElement(
        #                 treatment, "description")
        #             description_fields = ET.SubElement(
        #                 treatment_descriptions, "fields")
        #             for description in descriptions:

        #                 description_el = ET.SubElement(
        #                     description_fields, "description")
        #                 ET.SubElement(description_el,
        #                               "value").text = description

        #     count += 1

    @property
    def xml(self):
        return ''
        return ET.tostring(self.root)
