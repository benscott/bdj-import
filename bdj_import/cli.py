
import click

from xml.dom import minidom
from bdj_import.api import API
from bdj_import.doc import Doc


@click.command()
@click.option('--limit', default=None, help='Number of classifications.', type=int)
@click.option('--validate', is_flag=True)
@click.option('--console', 'output', flag_value='console')
@click.option('--file', 'output', flag_value='file')
@click.option('--bdj', 'output', flag_value='bdj')
@click.option('--taxon', default=None, help='Specific taxon.')
def main(limit, validate, output, taxon):

    response = None
    doc = Doc('Marine Fauna and Flora of the Falkland Islands', limit, None)
    api = API()

    if validate and not output == 'bdj':
        response = api.validate_document(doc.xml)

    pretty_xml = minidom.parseString(doc.xml).toprettyxml(indent="   ")

    if output:
        if output == 'file':
            with click.open_file('/tmp/publication.xml', 'w') as f:
                f.write(pretty_xml)
        elif output == 'console':
            print(pretty_xml)
        else:
            response = api.import_document(doc.xml)

    if response:
        print(response)

if __name__ == '__main__':
    main()
