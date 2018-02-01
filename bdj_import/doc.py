
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

from bdj_import.lib.helpers import normalize, file_exists
from bdj_import.lib.species_descriptions import SpeciesDescriptions
from bdj_import.lib.figures import Figures


class Doc:

    nomenclature_fields = [
        'genus',
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

    def __init__(self, title, limit=None):
        self.title = title
        self.data_dir = os.path.join(os.path.dirname(
            __file__), 'data')

        self.root = ET.Element("document")
        self.limit = limit

        self.figures = Figures('image-export.csv')

        self.species_descriptions = SpeciesDescriptions(
            'species-description-export.csv'
        )

        self.occurences = self._read_dwca_export_csv()

        self._add_document_info()
        self._add_authors()
        self._add_objects()
        # After the objects (general structure has been created), we can
        # add the dependent metadata and treatments
        # self._add_metadata(article_metadata)
        self._add_taxon_treatments()
        # self._add_checklists(checklists)

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
                               last_name='Scott', co_author='1', email='b.scott@nhm.ac.uk', right='1', submitting_author='1')

    def _add_metadata(self, article_metadata):
        # Add authors
        title_and_authors = ET.SubElement(
            article_metadata, "title_and_authors")

        title_and_authors_fields = ET.SubElement(title_and_authors, "fields")

        el = ET.Element('title')
        ET.SubElement(el, "value").text = self.title
        title_and_authors_fields.append(el)

    def _add_objects(self):
        # Add the main document objects - these are all required to pass document
        # validation
        objects = ET.SubElement(self.root, "objects")
        ET.SubElement(objects, "article_metadata")
        ET.SubElement(objects, "introduction")
        ET.SubElement(objects, "materials_and_methods")
        ET.SubElement(objects, "data_resources")
        ET.SubElement(objects, "taxon_treatments")
        ET.SubElement(objects, "checklists")
        ET.SubElement(objects, "identification_keys")
        ET.SubElement(objects, "results")
        ET.SubElement(objects, "discussion")
        ET.SubElement(objects, "acknowledgements")
        ET.SubElement(objects, "author_contributions")
        ET.SubElement(objects, "references")
        ET.SubElement(objects, "supplementary_files")
        ET.SubElement(objects, "figures")
        tables = ET.SubElement(objects, "tables")

        ET.SubElement(objects, "endnotes")
        # Add citations
        ET.SubElement(self.root, "citations")

    def _read_dwca_export_csv(self):
        voucher_specimens = OrderedDict()
        fpath = os.path.join(self.data_dir, 'falklands-utf8.dwca.csv')
        with open(fpath, 'r') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                # If this is a voucher specimen, we want to include it
                # otherwise we'll skip it
                type_status = row.get('typeStatus').strip()

                if type_status.lower() != 'voucher':
                    continue

                # Get the nomenclature fields
                nomenclature = {k.lower(): v for k, v in row.items()
                                if k in self.nomenclature_fields and v}

                # Create a new entry for this taxon
                normalized_taxon = normalize(row['taxonConceptID'])
                voucher_specimens.setdefault(normalized_taxon, {
                    'nomenclature': nomenclature,
                    'materials': [],
                    'species_description': None
                })

                # If we don';t have the species description yet, try and add it
                if not voucher_specimens[normalized_taxon]['species_description']:

                    for fn in ['taxonConceptID', 'scientificName']:
                        taxon = normalize(row.get(fn))
                        try:
                            voucher_specimens[normalized_taxon]['species_description'] = self.species_descriptions.get(
                                taxon)
                        except KeyError:
                            continue
                        else:
                            break

                # We only want certain fields included in the material details
                # field
                material_details = {k.lower(): v for k, v in row.items()
                                    if k in self.material_fields and v}

                voucher_specimens[taxon]['materials'].append(material_details)

        return voucher_specimens

    def _add_taxon_treatments(self):

        taxon_treatments = self.root.find('objects/taxon_treatments')

        count = 0

        # As per Adrian's request, we want to structure the doc so
        # family are included - not possible as a tree but at least in order
        for taxon, occurence in self.occurences.items():

            # if taxon != 'Amphitritides sp. 1':
            #     continue

            # print(taxon)

            if self.limit and count >= self.limit:
                break

            citation_refs = []
            # Do we have figures for this taxon treatment?

            try:
                tid = occurence['species_description']['tid']
            except (KeyError, TypeError):
                pass
            else:
                citation_refs = self._add_figures(self.figures.get(tid))

            treatment = self._build_taxon_treatment(
                taxon, occurence, citation_refs)

            taxon_treatments.append(treatment)

            count += 1

    def _build_taxon_treatment(self, taxon, occurence, citation_refs):

        treatment = ET.Element('treatment')

        # Add taxonomy fields
        treatment_fields = ET.SubElement(treatment, "fields")

        el = ET.Element('classification')
        ET.SubElement(el, "value").text = taxon

        treatment_fields.append(el)

        el = ET.Element('type_of_treatment')
        # FIXME
        ET.SubElement(
            el, "value").text = 'Redescription or species observation'
        treatment_fields.append(el)

        el = ET.Element('rank')
        ET.SubElement(el, "value").text = 'Species'
        treatment_fields.append(el)

        nomenclature = occurence.get('nomenclature')

        # Use the specific epithet as species name
        el = ET.Element('species')
        ET.SubElement(el, "value").text = nomenclature.get('specificepithet')
        treatment_fields.append(el)

        if occurence['nomenclature'].get('genus', None):
            el = ET.Element('genus')
            ET.SubElement(el, "value").text = occurence[
                'nomenclature'].get('genus')

            treatment_fields.append(el)

        # print(nomenclature.get('specificepithet'))

        if occurence['nomenclature'].get('scientificnameauthorship', None):
            authorship = occurence[
                'nomenclature'].get('scientificnameauthorship')
            print(nomenclature)
            print(authorship)
            m = re.search(
                r'([\w\-]+)[,\s]{0,2}([\d]{4})', authorship, re.IGNORECASE |
                re.UNICODE)

            try:
                author = m.group(1)
            except AttributeError:
                pass
            else:
                taxon_authors_el = ET.Element('taxon_authors')
                ET.SubElement(taxon_authors_el, "value").text = author
                treatment_fields.append(el)

            try:
                year = m.group(2)
            except AttributeError:
                pass
            else:
                taxon_year_el = ET.Element('taxon_year')
                ET.SubElement(taxon_year_el, "value").text = year
                treatment_fields.append(el)

        # Add material fields
        materials = ET.SubElement(treatment, "materials")

        for material in occurence.get('materials'):

            material_el = ET.SubElement(materials, "material")
            material_fields = ET.SubElement(material_el, "fields")

            el = ET.Element('type_status')
            ET.SubElement(el, "value").text = 'Other material'
            material_fields.append(el)

            for fn, value in material.items():
                el = ET.Element(fn)
                ET.SubElement(el, "value").text = value
                material_fields.append(el)

        if occurence.get('species_description'):

            parsed_species_description = self._parse_species_description(
                occurence['species_description'].get('body')
            )

            if parsed_species_description.get('diagnosis', None):
                treatment.append(
                    self._add_material_detail(
                        'diagnosis', parsed_species_description.get('diagnosis'))
                )

            notes = parsed_species_description.get('remarks', [])

            # FIXME: Just adding references to figures as text. BDJ does not
            # support inline refs
            if citation_refs:
                notes.append(
                    ' '.join(['[Fig. %s]' % ref for ref in citation_refs]))

            treatment.append(
                self._add_material_detail(
                    'notes', notes)
            )

            # if citation_id:
            #     material_detail_el=ET.Element('notes')
            #     fields=ET.SubElement(material_detail_el, "fields")
            #     el=ET.SubElement(fields, 'notes')
            #     value_el=ET.SubElement(el, "value")
            #     # ET.SubElement(value_el, "inline_citation",
            #     # {'citation_id': str(citation_id)})

            #     ET.SubElement(value_el, "p").text="Test"
            #     ET.SubElement(value_el, "inline_citation", {
            #                   'citation_id': str(citation_id)}).text='Fig 1'
            #     ET.SubElement(value_el, "inline_citation", {
            #                   'citation_id': '0'}).text='Fig 0'

            #     treatment.append(material_detail_el)

        # if citation_id:
        #     print(citation_id)
        #     print('---')
        # treatment.append(
        #     self._add_material_detail(
        #         'notes', '|||')
        # )

        return treatment

    @staticmethod
    def _add_material_detail(name, value):
        material_detail_el = ET.Element(name)
        fields = ET.SubElement(material_detail_el, "fields")
        el = ET.SubElement(fields, name)
        value_el = ET.SubElement(el, "value")
        for p in value:
            ET.SubElement(value_el, "p").text = p

        return material_detail_el

    def _parse_species_description(self, species_description):
        # Parse species description, splitting into voucher diagnosis & remarks
        description_field_names = ['voucher', 'diagnosis', 'remarks']
        soup = BeautifulSoup(species_description, "html.parser")
        # Create a data dict, keyed by the description field name
        data = {}

        current_field = None
        for el in soup.find_all(["p", "table"], recursive=False):
            # The body contains the taxonomy in headers at the top
            # Which needs to be stripped out, otherwise will duplicate data in
            # publication proper - so match the strong content
            # If we match on classification, we end up stripping out content from later in the
            # process e.g. tables with taxonomy in the description
            # instead we wait until the first paragraph matching Voucher, Diagnosis or Remarks
            # and discard all previous paragraphs

            # Loop through all of the strong tags, and see if it's voucher, diagnosis etc.,
            # If it is, then set the current field - used to key

            if el.name == 'p':
                for strong in el.find_all("strong"):
                    for description_field_name in description_field_names:
                        fn = strong.getText().lower()
                        fuzz_ratio = fuzz.partial_ratio(
                            description_field_name, strong.getText().lower())
                        if fuzz_ratio > 99:
                            current_field = description_field_name
                            el = el.getText().replace(str(strong), '')

            if current_field:
                # Try and get just the text - but handle errors if we've all
                # ready converted to string
                try:
                    if el.name == 'table':
                        # FIXME: String encoding is buggered at this point
                        table_id = self._add_table(str(el))
                        el = '[Table. %s]' % table_id
                    else:
                        el = el.getText()
                except AttributeError:
                    pass
                finally:
                    el = normalize(el)

                data.setdefault(current_field, []).append(el)

        # print(data)
        return data

    def _add_checklists(self, checklists):
        count = 0
        for family, taxa in self.classification.items():

            # checklist = ET.Element('checklist')

            # # Add taxonomy fields
            # checklist_fields = ET.SubElement(checklist, "fields")

            # el = ET.Element('classification')
            # ET.SubElement(el, "value").text = family
            # checklist_fields.append(el)

            # el = ET.Element('title')
            # ET.SubElement(el, "value").text = family
            # checklist_fields.append(el)

            # checklist_taxon = ET.SubElement(checklist, 'checklist_taxon')

            # # Add taxonomy fields
            # checklist_taxon_fields = ET.SubElement(checklist_taxon, "fields")

            # el = ET.Element('taxon_authors_and_year')
            # ET.SubElement(el, "value").text = family

            # checklist_taxon_fields.append(el)

            # el = ET.Element('rank')
            # ET.SubElement(el, "value").text = 'family'

            # checklist_taxon_fields.append(el)
            # checklists.append(checklist)

            checklist_el = self._build_checklist(family, 'family')
            checklists.append(checklist_el)

            for taxon_name, taxon in taxa.items():
                checklist_el = self._build_checklist(
                    taxon_name, 'family', **taxon.get('taxon_name'))
                # checklists.append(checklist_el)

            if count and count >= self.limit:
                break

            count += 1

    @staticmethod
    def _build_checklist(taxon_name, rank, **kwargs):
        checklist = ET.Element('checklist')

        # Add taxonomy fields
        checklist_fields = ET.SubElement(checklist, "fields")

        el = ET.Element('classification')
        ET.SubElement(el, "value").text = taxon_name
        checklist_fields.append(el)

        el = ET.Element('title')
        ET.SubElement(el, "value").text = taxon_name
        checklist_fields.append(el)

        checklist_taxon = ET.SubElement(checklist, 'checklist_taxon')

        # Add taxonomy fields
        checklist_taxon_fields = ET.SubElement(checklist_taxon, "fields")

        # if kwargs.get('taxon_authors', None):
        #     el = ET.Element('taxon_authors_and_year')
        #     ET.SubElement(el, "value").text = kwargs.get('taxon_authors')
        #     checklist_taxon_fields.append(el)

        el = ET.Element('rank')
        ET.SubElement(el, "value").text = rank
        return checklist

    def _add_table(self, table_str):

        tables = self.root.find('objects/tables')

        table_count = len(tables.findall('table'))
        table_id = table_count + 1

        table = ET.SubElement(tables, "table", {'id': str(table_id)})
        table_fields = ET.SubElement(table, "fields")

        table_caption = ET.SubElement(table_fields, "table_caption")
        ET.SubElement(table_caption, "value").text = ""

        table_editor = ET.SubElement(table_fields, "table_editor")
        ET.SubElement(table_editor, "value").append(ET.fromstring(table_str))
        return table_id

    def _add_figures(self, figures):
        return []

        citations = self.root.find('citations')

        object_figures = self.root.find('objects/figures')

        # We need to specify an id, so lets find out how many
        # figures we've added, and then use count as identifier
        figure_count = len(object_figures.findall('figure')) + 1

        figure_refs = []

        for i, figure in enumerate(figures):

            # Check path is accessible
            if not file_exists(figure['path']):
                continue

            figure_id = figure_count + i
            figure_el = ET.Element('figure', {'id': str(figure_id)})

            # Add figure fields
            figure_fields = ET.SubElement(figure_el, "fields")
            figure_type = ET.SubElement(figure_fields, 'figure_type')
            ET.SubElement(figure_type, "value").text = 'Image'

            # Add figure fields
            image = ET.SubElement(figure_el, "image")
            image_fields = ET.SubElement(image, "fields")
            # Add image caption
            figure_caption = ET.SubElement(image_fields, 'figure_caption')
            ET.SubElement(figure_caption, "value").text = figure.get(
                'description', None
            )
            # And image URL
            image_url = ET.SubElement(image_fields, 'image_url')
            ET.SubElement(image_url, "value").text = figure['path']

            # Add the figure element to the figures
            object_figures.append(figure_el)

            # One citation per figure
            citation_el = ET.SubElement(citations, 'citation', {
                'id': str(figure_id)
            })
            ET.SubElement(citation_el, "object_id").text = str(figure_id)
            ET.SubElement(citation_el, "citation_type").text = 'figs'

            figure_refs.append(figure_id)

        return figure_refs

    @property
    def xml(self):
        return ET.tostring(self.root, method='xml')
