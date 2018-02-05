
import csv
import os
import re
import unicodedata
import xml.etree.cElementTree as ET
from xml.dom import minidom
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from collections import OrderedDict

from bdj_import.api import API

from bdj_import.lib.helpers import normalize, file_exists, prettify_html, ensure_list
from bdj_import.lib.species_descriptions import SpeciesDescriptions
from bdj_import.lib.figures import Figures


from bdj_import.lib.data.species_occurences import SpeciesOccurences


class Doc:

    nomenclature_fields = [
        'genus',
        'family',
        'scientificNameAuthorship',
        'specificEpithet'
    ]

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

    def __init__(self, title, limit=None, taxon=None):
        self.title = title
        self.data_dir = os.path.join(os.path.dirname(
            __file__), 'data')

        self.root = ET.Element("document")
        self.limit = limit
        self.taxon = taxon

        self.occurences = SpeciesOccurences()
        self._add_document_info()
        self._add_authors()
        self._add_objects()
        # After the objects (general structure has been created), we can
        # add the dependent metadata and treatments
        self._add_metadata()
        self._add_taxon_treatments()
        # self._add_checklists()

    def _add_document_info(self):
        # Create document info

        document_info = self._add_elements(self.root, "document_info")
        self._add_elements(document_info, "document_type", 'Taxonomic Paper')
        self._add_elements(document_info, "journal_name",
                           'Biodiversity Data Journal')

    def _add_authors(self):
        # Add authors
        authors = self._add_elements(self.root, "authors")
        # We don't have many elements with lots of attributes so lets use
        # normal ET elements
        ET.SubElement(authors, "author", first_name='Ben',
                               last_name='Scott', co_author='1', email='b.scott@nhm.ac.uk', right='1', submitting_author='1')

    def _add_metadata(self):

        article_metadata = self.root.find('objects/article_metadata')
        self._add_nested_elements(article_metadata, [
            "title_and_authors",
            "fields",
            "title",
            "value"
        ]).text = self.title

    @staticmethod
    def _add_elements(root, elements, text=None):
        """
        Add list of elements
        Returns last element to be added
        """
        for element in ensure_list(elements):
            el = ET.SubElement(root, element)
        # If we have text, add it to the last element
        if text:
            el.text = text
        return el

    def _add_nested_elements(self, root, elements, text=None):
        """
        Recursively add elements
        """
        for element in ensure_list(elements):
            root = self._add_elements(root, element)
        # If we have text, add it to the last element
        if text:
            root.text = text
        return root

    def _add_objects(self):
        # Add the main document objects - these are all required to pass document
        # validation
        objects = self._add_elements(self.root, "objects")

        self._add_elements(objects, [
            "article_metadata",
            "introduction",
            "materials_and_methods",
            "data_resources",
            "taxon_treatments",
            "checklists",
            "identification_keys",
            "results",
            "discussion",
            "acknowledgements",
            "author_contributions",
            "references",
            "supplementary_files",
            "figures",
            "tables",
            "endnotes",
        ])
        # Add citations
        self._add_elements(self.root, "citations")

    # def _read_dwca_export_csv(self):
    #     voucher_specimens = OrderedDict()
    #     fpath = os.path.join(self.data_dir, 'falklands-utf8.dwca.csv')
    #     with open(fpath, 'r') as f:
    #         reader = csv.DictReader(f)
    #         count = 0
    #         for row in reader:
    #             # If this is a voucher specimen, we want to include it
    #             # otherwise we'll skip it
    #             type_status = row.get('typeStatus').strip()

    #             if type_status.lower() != 'voucher':
    #                 continue

    #             # Get the nomenclature fields
    #             nomenclature = {k.lower(): v for k, v in row.items()
    #                             if k in self.nomenclature_fields and v}

    #             # Create a new entry for this taxon
    #             normalized_taxon = normalize(row['taxonConceptID'])
    #             voucher_specimens.setdefault(normalized_taxon, {
    #                 'nomenclature': nomenclature,
    #                 'materials': [],
    #                 'species_description': None
    #             })

    #             # If we don';t have the species description yet, try and add it
    # if not voucher_specimens[normalized_taxon]['species_description']:

    #                 for fn in ['taxonConceptID', 'scientificName']:
    #                     taxon = normalize(row.get(fn))
    #                     try:
    #                         voucher_specimens[normalized_taxon]['species_description'] = self.species_descriptions.get(
    #                             taxon)
    #                     except KeyError:
    #                         continue
    #                     else:
    #                         break

    #             # We only want certain fields included in the material details
    #             # field
    #             material_details = {k.lower(): v for k, v in row.items()
    #                                 if k in self.material_fields and v}

    #             voucher_specimens[taxon]['materials'].append(material_details)

    #     return voucher_specimens

    def _add_taxon_treatments(self):

        taxon_treatments = self.root.find('objects/taxon_treatments')

        count = 0

        # As per Adrian's request, we want to structure the doc so
        # family are included - not possible as a tree but at least in order
        for taxon, occurence in self.occurences.vouchers():
            if self.limit and count >= self.limit:
                break
            if self.taxon and taxon != self.taxon:
                continue

            treatment = self._build_taxon_treatment(taxon, occurence)
            taxon_treatments.append(treatment)

            count += 1

    def _build_taxon_treatment(self, taxon, occurence):

        # citation_refs = None

        # # Add the figures
        # if occurence.get('figures', None):
        #     citation_refs = self._add_figures(
        #         occurence.get('figures'))

        treatment_el = ET.Element('treatment')

        treatment_fields_el = self._add_elements(
            treatment_el, 'fields'
        )

        self._add_nested_elements(treatment_fields_el,
                                  ['classification', 'value'], taxon)
        self._add_nested_elements(treatment_fields_el,
                                  ['type_of_treatment', 'value'],
                                  'Redescription or species observation'
                                  )

        self._add_nested_elements(
            treatment_fields_el, ['rank', 'value'], 'Species')

        if occurence.get('specificepithet', None):
            self._add_nested_elements(treatment_fields_el, [
                'species', 'value'], occurence['specificepithet'])

        if occurence.get('genus', None):
            self._add_nested_elements(treatment_fields_el, [
                'genus', 'value'], occurence['genus'])

        authorship = occurence.get('scientificnameauthorship', None)

        if authorship and occurence['specificepithet'] != 'sp.':
            self._add_nested_elements(treatment_fields_el, [
                'taxon_authors', 'value'], authorship)

        # Add material fields
        materials_el = ET.SubElement(treatment_el, "materials")

        for material in occurence.get('materials'):
            material_fields_el = self._add_nested_elements(
                materials_el, ['material', 'fields']
            )
            self._add_nested_elements(
                material_fields_el, ['type_status', 'value'], 'Other material')

            for fn, value in material.items():
                self._add_nested_elements(
                    material_fields_el, [fn, 'value'], value)

        notes = []
        # TODO: Add images at this point
        figures = occurence.get('figures', [])
        if figures:
            for figure in figures:
                citation_ref = self._add_figure(figure)

                notes.append(
                    self._soup_el('<p>[Figure {}]</p>', citation_ref)
                )

        if occurence.get('species_description'):
            voucher_fields = occurence['species_description'].voucher_fields

            # If we have actual notes, append them to the start of the notes array
            # So any image references above float to the bottom
            notes = voucher_fields.get('remarks', []) + notes

            if occurence['species_description'].tables:
                for table in occurence['species_description'].tables:
                    citation_ref = self._add_table(table)
                    notes.append(
                        self._soup_el('<p>[Table {}]</p>', citation_ref)
                    )

            if voucher_fields.get('diagnosis', None):
                self._add_material_detail(treatment_el,
                                          'diagnosis', voucher_fields['diagnosis'])

        if notes:
            self._add_material_detail(treatment_el, 'notes', notes)

        return treatment_el

    def _add_material_detail(self, root, element_name, paragraphs):
        el = self._add_nested_elements(
            root, [element_name, 'fields', element_name, 'value'])
        for p in paragraphs:
            self._add_elements(el, 'p', normalize(p.getText()))

    @staticmethod
    def _soup_el(html, vars):
        return BeautifulSoup(html.format(vars), "html.parser")

    def _add_checklists(self):

        count = 0
        checklists = self.root.find('objects/checklists')
        checklist = ET.SubElement(checklists, 'checklist')

        # Add taxonomy fields
        checklist_fields = ET.SubElement(checklist, "fields")
        classification_el = ET.SubElement(checklist_fields, 'classification')
        ET.SubElement(classification_el, "value").text = 'Lumbrineridae'

        title_el = ET.SubElement(checklist_fields, 'title')
        ET.SubElement(title_el, "value").text = 'Classification'

        for family, taxa in self._taxonomic_tree.items():
            if self.limit and count >= self.limit:
                break

            checklist_el = self._build_checklist(family, 'family')
            checklist.append(checklist_el)

            species_description = self.species_descriptions.get(family)

            if species_description:
                taxon_notes_el = ET.SubElement(checklist_el, "taxon_notes")
                taxon_notes_field_el = ET.SubElement(taxon_notes_el, "fields")
                notes_el = ET.SubElement(taxon_notes_field_el, "notes")
                notes_value_el = ET.SubElement(notes_el, "value")
                body_str = prettify_html(species_description.get('body'))
                notes_value_el.append(ET.fromstring(body_str))
                # Add notes
                for taxon in taxa:
                    checklist_el = self._build_checklist(taxon, 'species')
                    checklist.append(checklist_el)

            count += 1

    @staticmethod
    def _build_checklist(taxon, rank):

        checklist_taxon = ET.Element('checklist_taxon')

        # Add taxonomy fields
        checklist_taxon_fields = ET.SubElement(checklist_taxon, "fields")

        el = ET.Element('rank')
        ET.SubElement(el, "value").text = rank
        checklist_taxon_fields.append(el)

        el = ET.Element(rank)
        ET.SubElement(el, "value").text = taxon
        checklist_taxon_fields.append(el)

        return checklist_taxon

    def _add_table(self, table):

        object_tables = self.root.find('objects/tables')

        table_count = len(object_tables.findall('table'))
        table_id = table_count + 1

        table_el = ET.SubElement(object_tables, "table", {'id': str(table_id)})
        table_fields = ET.SubElement(table_el, "fields")

        self._add_nested_elements(table_fields, ['table_caption', 'value'])
        self._add_nested_elements(
            table_fields, ['table_editor', 'value']).append(
                ET.fromstring(str(table.prettify()))
        )
        return self._add_citation(table_id, 'tables')

    def _add_figure(self, figure):

        # Check path is accessible
        if not file_exists(figure['path']):
            return

        object_figures = self.root.find('objects/figures')

        # We need to specify an id, so lets find out how many
        # figures we've added, and then use count as identifier
        figure_id = len(object_figures.findall('figure')) + 1

        figure_el = ET.Element('figure', {'id': str(figure_id)})
        self._add_nested_elements(
            figure_el, ['fields', 'figure_type', 'value']).text = 'Image'
        image_fields = self._add_nested_elements(
            figure_el, ['image', 'fields'])
        self._add_nested_elements(
            image_fields, ['figure_caption', 'value']).text = figure['description']
        self._add_nested_elements(
            image_fields, ['image_url', 'value']).text = figure['path']

        # Add the figure element to the figures
        object_figures.append(figure_el)
        return self._add_citation(figure_id, 'figs')

    def _add_citation(self, object_id, citation_type):
        """
        Add a citation referenceG
        """
        citations_el = self.root.find('citations')
        # We need to specify an id, so count how many we have and iterate one
        citation_id = len(citations_el.findall('citation')) + 1

        # One citation per figure
        citation_el = ET.SubElement(citations_el, 'citation', {
            'id': str(citation_id)
        })
        self._add_elements(citation_el, ['object_id'], str(object_id))
        self._add_elements(citation_el, ['citation_type'], citation_type)
        return citation_id

    @property
    def xml(self):
        return ET.tostring(self.root, method='xml')
