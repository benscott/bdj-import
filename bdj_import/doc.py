
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
from bdj_import.lib import normalize


class Doc:

    classification_fields = [
        'scientificName',
        'kingdom',
        'phylum',
        'class',
        # 'genus',
        # 'scientificNameAuthorship',
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

    def __init__(self, title, limit=None):
        self.title = title
        self.data_dir = os.path.join(os.path.dirname(
            __file__), 'data')

        self.root = ET.Element("document")
        self.limit = limit

        self.figures = self._read_images_export_csv()

        self.classification = self._read_dwca_export_csv()

        self._read_species_descriptions_export_csv()
        self._add_document_info()
        self._add_authors()
        self._add_objects()

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
        article_metadata = ET.SubElement(objects, "article_metadata")
        ET.SubElement(objects, "introduction")
        ET.SubElement(objects, "materials_and_methods")
        ET.SubElement(objects, "data_resources")
        taxon_treatments = ET.SubElement(objects, "taxon_treatments")
        checklists = ET.SubElement(objects, "checklists")
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

        # After the objects (general structure has been created), we can
        # add the dependent metadata and treatments
        self._add_metadata(article_metadata)
        self._add_taxon_treatments(taxon_treatments)
        self._add_checklists(checklists)

    def _read_dwca_export_csv(self):
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

                family = normalize(row['family'])

                classification.setdefault(family, {})

                taxon = row.get('taxonConceptID')
                normalized_taxon = normalize(taxon)

                # We only want certain fields included
                material = {k.lower(): v for k, v in row.items()
                            if k in self.classification_fields and v}

                taxon_name_fields = [
                    ('genus', 'genus'),
                    ('subgenus', 'subgenus'),
                    ('taxon_authors', 'scientificNameAuthorship')
                ]
                taxon_name = {n: normalize(row[m])
                              for n, m in taxon_name_fields if row.get(m, None)}

                classification[family].setdefault(
                    normalized_taxon, {
                        'taxon_name': taxon_name,
                        'materials': []
                    })

                classification[family][normalized_taxon][
                    'materials'].append(material)

        return OrderedDict(sorted(classification.items()))

    def _read_images_export_csv(self):
        # Create a dict of images, keyed by taxonomic name
        images = {}
        fpath = os.path.join(self.data_dir, 'image-export.csv')
        with open(fpath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                taxon = normalize(row['Name'])
                images.setdefault(taxon, []).append({
                    'path': row['Path'],
                    'description': normalize(row['Description'])
                })
        return images

    def _read_species_descriptions_export_csv(self):

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
                    self.species_descriptions[taxon] = self._parse_species_description(row[
                                                                                       'Body'])

    @staticmethod
    def _parse_species_description(species_description):
        # Parse species description, splitting into voucher diagnosis & remarks
        description_field_names = ['voucher', 'diagnosis', 'remarks']
        soup = BeautifulSoup(species_description, "html.parser")
        # Create a data dict, keyed by the description field name
        data = {}

        current_field = None
        for p in soup.find_all("p"):
            # The body contains the taxonomy in headers at the top
            # Which needs to be stripped out, otherwise will duplicate data in
            # publication proper - so match the strong content
            # If we match on classification, we end up stripping out content from later in the
            # process e.g. tables with taxonomy in the description
            # instead we wait until the first paragraph matching Voucher, Diagnosis or Remarks
            # and discard all previous paragraphs

            # Loop through all of the strong tags, and see if it's voucher, diagnosis etc.,
            # If it is, then set the current field - used to key
            for strong in p.find_all("strong"):
                for description_field_name in description_field_names:
                    fn = strong.getText().lower()
                    fuzz_ratio = fuzz.partial_ratio(
                        description_field_name, strong.getText().lower())
                    if fuzz_ratio > 99:
                        current_field = description_field_name
                        p = str(p).replace(str(strong), '')

            if current_field:
                data.setdefault(current_field, []).append(normalize(str(p)))

        # Flatten the data values
        data = {i: ''.join(j) for i, j in data.items()}

        return data

    # def _get_species_descriptions(self, classification):
    #     for taxon_field in ['taxonconceptid', 'scientificname']:
    #         try:
    #             taxon = classification[taxon_field]
    #         except KeyError:
    #             continue

    #         # Get rid of any odd characters and white space
    #         normalized_taxon = unicodedata.normalize("NFKD", taxon).strip()
    #         try:
    #             return self.species_descriptions[normalized_taxon]
    #         except KeyError:
    #             pass

    def _add_taxon_treatments(self, taxon_treatments):
        count = 0

        # As per Adrian's request, we want to structure the doc so
        # family are included - not possible as a tree but at least in order
        for family, taxa in self.classification.items():

            if self.limit and count >= self.limit:
                break

            for name, taxon in taxa.items():

                # Do we have figures for this taxon treatment?
                try:
                    self._add_figures(self.figures[name])
                except KeyError:
                    pass
                else:
                    # No key error - we have figures for this taxon treatment
                    # So we need to attach the figure to the treatment
                    pass
                    # FIXME: Add figures
                    # print(self.figures[name])

                treatment = self._build_taxon_treatment(name, taxon)
                # Do we have species description for this treatment

                # print(species_description)

                # print(self.species_descriptions.keys())
                # print(self.species_descriptions[name])

                try:
                    pass
                    # self._add_figures(self.figures[name])
                except KeyError:
                    pass
                else:
                    # No key error - we have figures for this taxon treatment
                    # So we need to attach the figure to the treatment
                    pass
                    # FIXME: Add figures
                    # print(self.figures[name])

                taxon_treatments.append(treatment)

            #     print('-----')

            #     for material in materials:

            #         print(material.get('genus', None))
            # print(classification)
            # print(classification.get('genus', None))

            # print(taxa['genus'])

            # self._add_family(family)

            # self._add_family(family)

            # try:

            # except KeyError:

            #     print(family)

            # for classification in self._iter_classification():

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

            count += 1

    def _build_taxon_treatment(self, name, taxon):

        treatment = ET.Element('treatment')

        # Add taxonomy fields
        treatment_fields = ET.SubElement(treatment, "fields")

        el = ET.Element('classification')
        ET.SubElement(el, "value").text = name

        treatment_fields.append(el)

        el = ET.Element('type_of_treatment')
        ET.SubElement(el, "value").text = 'New taxon'
        treatment_fields.append(el)

        el = ET.Element('rank')
        ET.SubElement(el, "value").text = 'Species'
        treatment_fields.append(el)

        el = ET.Element('species')
        ET.SubElement(el, "value").text = name
        treatment_fields.append(el)

        # for taxon_name_field, taxon_name_value in taxon['taxon_name'].items():
        #     el = ET.Element(taxon_name_field)
        #     ET.SubElement(el, "value").text = taxon_name_value
        #     treatment_fields.append(el)

        # Add material fields
        materials = ET.SubElement(treatment, "materials")

        for material in taxon.get('materials'):

            material_el = ET.SubElement(materials, "material")
            material_fields = ET.SubElement(material_el, "fields")

            el = ET.Element('type_status')
            ET.SubElement(el, "value").text = 'Other material'
            material_fields.append(el)

            for fn, value in material.items():
                el = ET.Element(fn)
                ET.SubElement(el, "value").text = value
                material_fields.append(el)

        try:
            species_description = self.species_descriptions[name]
        except KeyError:
            pass
        else:

            # Change our field name to the corresponding one in the XML
            for fn, el_name in [('diagnosis', 'diagnosis'), ('remarks', 'notes')]:

                try:
                    description = species_description[fn]
                except KeyError:
                    continue
                else:
                    species_description_el = ET.SubElement(treatment, el_name)
                    species_description_el_fields = ET.SubElement(
                        species_description_el, "fields")

                    el = ET.SubElement(species_description_el_fields, el_name)
                    ET.SubElement(el, "value").text = description

        return treatment

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
                    taxon_name, 'species', **taxon.get('taxon_name'))
                checklists.append(checklist_el)

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

        if kwargs.get('taxon_authors', None):
            el = ET.Element('taxon_authors_and_year')
            ET.SubElement(el, "value").text = kwargs.get('taxon_authors')
            checklist_taxon_fields.append(el)

        el = ET.Element('rank')
        ET.SubElement(el, "value").text = rank
        return checklist

    def _add_figures(self, figures):

        object_figures = self.root.find('objects/figures')

        # We need to specify an id, so lets find out how many
        # figures we've added, and then use count as identifier
        figure_count = len(object_figures.findall('figure'))

        for i, figure in enumerate(figures):

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

            figures[i]['id'] = figure_id

    @property
    def xml(self):
        return ET.tostring(self.root)
