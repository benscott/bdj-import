
import click
import click_log
import logging
from xml.dom import minidom

from bdj_import.api import API
from bdj_import.doc import Doc

logger = logging.getLogger()
click_log.basic_config(logger)


@click.command()
@click.option('--limit', '-l', default=None, help='Number of classifications.', type=int)
@click.option('--validate', '-v', is_flag=True)
@click.option('--skip-images', '-i', is_flag=True, help="Do not import images - useful for testing.")
@click.option('--output', '-o', default=None, type=click.Choice(['console', 'file', 'bdj']))
@click.option('--family', '-f', default=None, help='Import specific family and child taxa.')
@click.option('--taxon', '-t', default=None, help='Import specific taxon.')
@click_log.simple_verbosity_option(logger)
def main(limit, validate, output, family, taxon, skip_images):

    response = None
    doc = Doc('Marine Fauna and Flora of the Falkland Islands',
              limit, taxon, family, skip_images)
    api = API()

    if validate and not output == 'bdj':
        logger.info("Validating XML.")
        response = api.validate_document(doc.xml)

    pretty_xml = minidom.parseString(doc.xml).toprettyxml(indent="   ")

    if output:
        if output == 'file':
            fpath = '/tmp/publication.xml'
            with click.open_file(fpath, 'w') as f:
                f.write(pretty_xml)
            logger.info('Output to %s', fpath)
        elif output == 'console':
            print(pretty_xml)
        else:
            logger.warning("Exporting to BDJ.")
            response = api.import_document(doc.xml)

    if response:
        print(response)

if __name__ == '__main__':
    main()
