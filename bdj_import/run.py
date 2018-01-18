
import csv
import os
import re
import unicodedata
import xml.etree.cElementTree as ET

from xml.dom import minidom
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
import click


from bdj_import.api import API
from bdj_import.doc import Doc


def get_description_field_name(p):
    """Get field name

    Args:
        p (soup): Description

    Returns:
        TYPE: Description
    """

    description_field_names = ['voucher', 'diagnosis', 'remarks']
    for strong in p.find_all("strong"):
        label = strong.getText().lower()
        for description_field_name in description_field_names:
            if description_field_name in label:
                return (description_field_name, strong)


def get_species_descriptions():

    # Read classification DWV
    fpath = os.path.join(os.path.dirname(
        __file__), 'data', 'species-description-export.html.csv')
    species_description = {}
    re_a = re.compile(r">(.*?)</a>")
    with open(fpath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Classification']:
                taxon = re_a.search(row['Classification']).group(1)
                species_description[taxon] = row['Body']

    return species_description


def is_taxon_description_body(p):

    description_field_names = ['voucher', 'diagnosis', 'remarks']
    strongs = p.find_all("strong")

    for strong in strongs:

        for description_field_name in description_field_names:

            fuzz_ratio = fuzz.partial_ratio(
                description_field_name, strong.getText().lower())

            if fuzz_ratio > 99:
                return True


def main():

    species_descriptions = get_species_descriptions()

    api = API()

    doc = ET.Element("document")
    # Create document info
    document_info = ET.SubElement(doc, "document_info")

    ET.SubElement(
        document_info, "document_type").text = 'Taxonomic Paper'
    ET.SubElement(
        document_info, "journal_name").text = 'Biodiversity Data Journal'

    # Add authors
    authors = ET.SubElement(doc, "authors")
    author = ET.SubElement(authors, "author", first_name='Ben',
                           last_name='Scott', co_author='1', email='ben@benscott.co.uk', right='1', submitting_author='1')
    # Add required child objects - these are all required to pass document
    # validation
    objects = ET.SubElement(doc, "objects")
    article_metadata = ET.SubElement(objects, "article_metadata")
    ET.SubElement(objects, "introduction")
    ET.SubElement(objects, "materials_and_methods")
    ET.SubElement(objects, "data_resources")
    taxon_treatments = ET.SubElement(objects, "taxon_treatments")
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

    count = 0

    material_fields = [
        # "occurrencedetails",
        # "catalognumber",
        # "occurrenceremarks",
        # "recordnumber",
        # "recordedby",
        # "individualid",
        # "individualcount",
        # "sex",
        # "lifestage",
        # "reproductivecondition",
        # "behavior",
        # "establishmentmeans",
        # "occurrencestatus",
        # "preparations",
        # "disposition",
        # "othercatalognumbers",
        # "previousidentifications",
        # "associatedmedia",
        # "associatedreferences",
        # "associatedoccurrences",
        # "associatedsequences",
        # "occurrenceid",
        # "taxonid",
        # "scientificnameid",
        # "acceptednameusageid",
        # "parentnameusageid",
        # "originalnameusageid",
        # "nameaccordingtoid",
        # "namepublishedinid",
        # "taxonconceptid",
        # "scientificname",
        # "acceptednameusage",
        # "parentnameusage",
        # "originalnameusage",
        # "nameaccordingto",
        # "namepublishedin",
        # "higherclassification",
        # "kingdom",
        # "phylum",
        # "class",
        # "order",
        # "family",
        # "genus",
        # "subgenus",
        # "specificepithet",
        # "infraspecificepithet",
        # "taxonrank",
        # "verbatimtaxonrank",
        # "scientificnameauthorship",
        # "vernacularname",
        # "nomenclaturalcode",
        # "taxonomicstatus",
        # "nomenclaturalstatus",
        # "taxonremarks",
        # "locationid",
        # "highergeographyid",
        # "highergeography",
        # "continent",
        # "waterbody",
        # "islandgroup",
        # "island",
        # "country",
        # "countrycode",
        # "stateprovince",
        # "county",
        # "municipality",
        # "locality",
        # "verbatimlocality",
        # "verbatimelevation",
        # "minimumelevationinmeters",
        # "maximumelevationinmeters",
        # "verbatimdepth",
        # "minimumdepthinmeters",
        # "maximumdepthinmeters",
        # "minimumdistanceabovesurfaceinmeters",
        # "maximumdistanceabovesurfaceinmeters",
        # "locationaccordingto",
        # "locationremarks",
        # "verbatimcoordinates",
        # "verbatimlatitude",
        # "verbatimlongitude",
        # "verbatimcoordinatesystem",
        # "verbatimsrs",
        # "decimallatitude",
        # "decimallongitude",
        # "geodeticdatum",
        # "coordinateuncertaintyinmeters",
        # "coordinateprecision",
        # "pointradiusspatialfit",
        # "footprintwkt",
        # "footprintsrs",
        # "footprintspatialfit",
        # "georeferencedby",
        # "georeferenceprotocol",
        # "georeferencesources",
        # "georeferenceverificationstatus",
        # "georeferenceremarks",
        # "identificationid",
        # "identifiedby",
        # "dateidentified",
        # "identificationreferences",
        # "identificationremarks",
        # "identificationqualifier",
        # "geologicalcontextid",
        # "earliesteonorlowesteonothem",
        # "latesteonorhighesteonothem",
        # "earliesteraorlowesterathem",
        # "latesteraorhighesterathem",
        # "earliestperiodorlowestsystem",
        # "latestperiodorhighestsystem",
        # "earliestepochorlowestseries",
        # "latestepochorhighestseries",
        # "earliestageorloweststage",
        # "latestageorhigheststage",
        # "lowestbiostratigraphiczone",
        # "highestbiostratigraphiczone",
        # "lithostratigraphicterms",
        # "group",
        # "formation",
        # "member",
        # "bed",
        # "eventid",
        # "samplingprotocol",
        # "samplingeffort",
        # "eventdate",
        # "eventtime",
        # "startdayofyear",
        # "enddayofyear",
        # "year",
        # "month",
        # "day",
        # "verbatimeventdate",
        # "habitat",
        # "fieldnumber",
        # "fieldnotes",
        # "eventremarks",
        # "type",
        # "modified",
        # "language",
        # "rights",
        # "rightsholder",
        # "accessrights",
        # "bibliographiccitation",
        # "institutionid",
        # "collectionid",
        # "datasetid",
        # "institutioncode",
        # "collectioncode",
        # "datasetname",
        # "ownerinstitutioncode",
        # "basisofrecord",
        # "informationwithheld",
        # "datageneralizations",
        # "dynamicproperties",
        # "source",
    ]

    # Loop through the classifications
    for classification in iter_classification():

        if count > 2:
            break

        taxa = []
        description = None

        if description:

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
                    is_body = is_taxon_description_body(p)

                if is_body:
                    body.append(str(p))

        # Ensure classification contains some terms we want
        if(bool(classification)):
            count += 1
            treatment = ET.SubElement(taxon_treatments, "treatment")
            # Add taxonomy fields
            treatment_fields = ET.SubElement(treatment, "fields")

            el = ET.Element('classification')
            ET.SubElement(el, "value").text = classification.get(
                'taxonconceptid')
            treatment_fields.append(el)

            el = ET.Element('rank')
            ET.SubElement(el, "value").text = 'Species'
            treatment_fields.append(el)

            el = ET.Element('type_of_treatment')
            ET.SubElement(el, "value").text = 'New taxon'
            treatment_fields.append(el)

            materials = ET.SubElement(treatment, "materials")
            material = ET.SubElement(materials, "material")
            material_fields = ET.SubElement(material, "fields")

            el = ET.Element('type_status')
            ET.SubElement(el, "value").text = 'Other material'
            material_fields.append(el)

            # for fn, value in classification.items():
            #     el = ET.Element(fn)
            #     ET.SubElement(el, "value").text = value
            #     fields.append(el)

            # ET.SubElement(fields, "fn").append(

            # <xsd:
            #     element name = "kingdom" type = "fieldEmpty" minOccurs = "0" / >
            # <xsd:
            #     element name = "phylum" type = "fieldEmpty" minOccurs = "0" / >
            # <xsd:
            #     element name = "class" type = "fieldEmpty" minOccurs = "0" / >
            # <xsd:
            #     element name = "order" type = "fieldEmpty" minOccurs = "0" / >
            # <xsd:
            #     element name = "family" type = "fieldEmpty" minOccurs = "0" / >
            # <xsd:
            #     element name = "genus" type = "fieldEmpty" minOccurs = "0" / >
            # <xsd:
            # element name = "subgenus" type = "fieldEmpty" minOccurs = "0" / >

            #     for material_field in ['kingdom', 'phylum', 'class']

           # # Add the metadata
           # front = ET.SubElement(article, "front")
           # journal_meta = ET.SubElement(front, "journal-meta")
           # ET.SubElement(journal_meta, "journal-id",
           #               **{'journal-id-type': 'pmc'}
           #               ).text = 'Biodiversity Data Journal'

           # ET.register_namespace('tp', 'www.example.com')
           # body = ET.SubElement(article, "body")
           # attr = {
           #     'sec-type': 'Taxon treatments'
           # }
           # taxon_treatments = ET.SubElement(body, "sec", **attr)

    xml = ET.tostring(doc)
    # print(xml)
    print(minidom.parseString(ET.tostring(doc)).toprettyxml(indent="   "))
    # api.validate_document(xml)

    # taxon_treatment = ET.SubElement(taxon_treatments, "taxon-treatment")
    # nomenclature = ET.SubElement(taxon_treatment, "nomenclature")
    # # Add Classification
    # ET.SubElement(taxon_treatment, "taxon-name-part",
    #     **{'taxon-name-part-type': "genus"}
    #     ).text='Crinoidea'
    # ET.SubElement(taxon_treatment, "taxon-name-part",
    #     **{'taxon-name-part-type': "species"}
    #     ).text='sp. \'NHM_008\''
    # # Add materials
    # materials = ET.SubElement(taxon_treatment, "materials")
    # ET.SubElement(materials, "title").text = 'Materials'
    # materials.text = 'Hello there'

    # treatment-sec

    # <tp:taxon-name-part taxon-name-part-type="genus">Crinoidea</tp:taxon-name-part>

    # ET.SubElement(body, "field2", name="asdfasd").text = "some vlaue2"

    # tree = ET.ElementTree(article)
    # print(ET.tostring(article))

    # print(tree.print)


def authenticate():

    doc = Doc(5)
    print(doc.xml)

    # api = API()
    # xml = '<article xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:tp="http://www.plazi.org/taxpub" article-type="research-article"></article>'
    # api.validate_document(xml)
    # print(api)


if __name__ == "__main__":
    authenticate()
