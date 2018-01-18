
import csv
import os
import re
import unicodedata
import xml.etree.cElementTree as ET
from bdj_import.api import API
from xml.dom import minidom
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz


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

    def __init__(self, limit=None):
        self.data_dir = os.path.join(os.path.dirname(
            __file__), 'data')

        self.root = ET.Element("document")
        self.count = 0
        self.species_descriptions = self._parse_species_descriptions()
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

    def _iter_classification(self):
        # Read classification DWV
        fpath = os.path.join(self.data_dir, 'falklands_classification.csv')
        with open(fpath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield {k.lower(): v for k, v in row.items()
                       if k in self.classification_fields and v}

    def _parse_species_descriptions(self):

        # Read classification DWV
        fpath = os.path.join(
            self.data_dir, 'species-description-export.html.csv')
        species_description = {}
        re_a = re.compile(r">(.*?)</a>")
        with open(fpath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Classification']:
                    # FIXME: Multiple descriptions per taxa
                    taxon = re_a.search(row['Classification']).group(1)
                    species_description[taxon] = row['Body']

        return species_description

    def _get_species_description(self, classification):
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

        for classification in self._iter_classification():
            description = self._get_species_description(classification)
            print(description)

    @property
    def xml(self):
        return ET.tostring(self.root)
