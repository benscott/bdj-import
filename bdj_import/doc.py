
import os
import logging
import xml.etree.cElementTree as ET

from bdj_import.lib.helpers import normalize, file_exists, ensure_list

from bdj_import.lib.dwca.taxa import DWCATaxa


logger = logging.getLogger()


class Doc:

    def __init__(self, title, limit=None, taxon=None, family=None, skip_images=False):
        self.title = title
        self.data_dir = os.path.join(os.path.dirname(
            __file__), 'data')

        self.root = ET.Element("document")
        self.limit = limit
        self.taxon = taxon
        self.skip_images = skip_images
        self.family = family

        # Parse the DWC files
        self.new_species = DWCATaxa()

        self._add_document_info()
        self._add_authors()
        self._add_objects()
        # After the objects (general structure has been created), we can
        # add the dependent metadata and treatments
        self._add_metadata()
        self._add_taxon_treatments()

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

    def _add_taxon_treatments(self):

        taxon_treatments = self.root.find('objects/taxon_treatments')
        count = 0

        for family in self.new_species.values():

            # If we have suplied a family name cli parameter, continue if
            # the fmaily scientific name does not match
            if self.family:
                if family.scientific_name.lower() != self.family.lower():
                    continue

            logger.debug("Processing family %s.", family.scientific_name)

            # treatment_el = self._build_taxon_treatment(family)
            # taxon_treatments.append(treatment_el)

            for species in family.list_species():
                if self.limit and count >= self.limit:
                    return
                if self.taxon:
                    if species.scientific_name != self.taxon:
                        continue

                logger.debug("Processing species %s.", species.scientific_name)

                treatment_el = self._build_taxon_treatment(species)
                taxon_treatments.append(treatment_el)
                count += 1

    def _build_taxon_treatment(self, treatment):

        treatment_el = ET.Element('treatment')
        treatment_fields_el = self._add_elements(
            treatment_el, 'fields'
        )

        self._add_nested_elements(treatment_fields_el,
                                  ['classification', 'value'], treatment.scientific_name)
        self._add_nested_elements(treatment_fields_el,
                                  ['type_of_treatment', 'value'],
                                  'Redescription or species observation'
                                  )

        self._add_nested_elements(
            treatment_fields_el, ['rank', 'value'], 'Species')

        # Loop through all the taxonomic fields, and add them if they have a
        # value
        for taxonomic_field in ['species', 'genus', 'subgenus', 'taxon_authors']:
            if hasattr(treatment, taxonomic_field) and getattr(treatment, taxonomic_field):
                self._add_nested_elements(treatment_fields_el, [
                    taxonomic_field, 'value'], getattr(treatment, taxonomic_field))

        if treatment.materials:
            # Add material fields
            materials_el = ET.SubElement(treatment_el, "materials")

            for material in treatment.materials:
                material_fields_el = self._add_nested_elements(
                    materials_el, ['material', 'fields']
                )
                self._add_nested_elements(material_fields_el,
                                          ['type_status', 'value'], 'Other material'
                                          )

                self._add_nested_elements(material_fields_el, [
                    'scientificname', 'value'], treatment.species)

                for fn, value in material.items():
                    self._add_nested_elements(
                        material_fields_el, [fn, 'value'], value)

        notes = treatment.notes

        citation_ids = []

        # Add any figures
        if treatment.figures and not self.skip_images:
            figure_citation_ids = self._add_figures(treatment.figures)
            citation_ids.extend(figure_citation_ids)

        # Add any table references
        if treatment.description:
            table_citation_ids = self._add_tables(treatment.description)
            citation_ids.extend(table_citation_ids)

        if treatment.diagnosis:
            self._add_material_detail(treatment_el,
                                      'diagnosis', treatment.diagnosis)

        # Always add notes, do we can add the inline citations
        notes_el = self._add_material_detail(treatment_el, 'notes', notes)

        for citation_id in citation_ids:
            notes_el.append(ET.Element("inline_citation",
                                       citation_id=str(citation_id)))

        return treatment_el

    def _add_material_detail(self, root, element_name, paragraphs):
        el = self._add_nested_elements(
            root, [element_name, 'fields', element_name, 'value'])
        for p in paragraphs:
            self._add_elements(el, 'p', normalize(p.getText()))
        return el

    def _add_tables(self, species_description):
        refs = []
        for table in species_description.tables:
            citation_id = self._add_table(table)
            refs.append(citation_id)
        return refs

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

    def _add_figures(self, figures):
        refs = []
        for figure in figures:
            citation_id = self._add_figure(figure)
            refs.append(citation_id)
        return refs

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


        Args:
            object_id (TYPE): Description
            citation_type (TYPE): Description

        Returns:
            inline citation id
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
