
import click

from xml.dom import minidom
from bdj_import.api import API
from bdj_import.doc import Doc


@click.command()
@click.option('--limit', default=None, help='Number of classifications.', type=int)
@click.option('--debug', is_flag=True)
def main(limit, debug):
    doc = Doc(limit)
    api = API()

    if debug:
        prettty_xml = minidom.parseString(doc.xml).toprettyxml(indent="   ")
        print(prettty_xml)
        with click.open_file('publication.xml', 'w') as f:
            f.write(prettty_xml)
        api.validate_document(doc.xml)
    else:
        api.import_document(doc.xml)

if __name__ == '__main__':
    main()
