
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
        print(minidom.parseString(doc.xml).toprettyxml(indent="   "))
        api.validate_document(doc.xml)
    else:
        # api.validate_document(doc.xml)
        pass

if __name__ == '__main__':
    main()
