

from bs4 import BeautifulSoup, Tag


class Description(object):
    """
    Class for storing species description
    Text will be separated out into tables and paragraphs
    """

    def __init__(self, tid, body, index, scientific_name, rank):
        self.tables = []
        self.paragraphs = []
        self.tid = tid
        self.index = index
        self.scientific_name = scientific_name
        self.rank = rank
        self._parse_body(body)

    def matches(self, lookup, rank=None):
        """
        Does this description match lookup term (taxon)
        """
        if rank and rank != self.rank:
            return False
        for idx in self.index:
            if lookup in idx:
                return True
        return False

    def _parse_body(self, body):
        """
        Loop through the raw body text
        If it's a table move it into _tables property,other add to _paragraphs
        """
        soup = BeautifulSoup(body, "html.parser")
        for el in soup.find_all(["p", "table"], recursive=False):
            l = self.tables if el.name == 'table' else self.paragraphs
            # Remove all embedded images - these cannot be included in the xml
            [x.extract() for x in el.findAll('img')]
            l.append(el)
