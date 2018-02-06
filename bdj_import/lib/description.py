

from bs4 import BeautifulSoup, Tag
from fuzzywuzzy import fuzz


class Description(object):

    def __init__(self, tid, body, index, scientific_name):
        self._tables = []
        self._paragraphs = []
        self.tid = tid
        self.index = index
        self.scientific_name = scientific_name
        self._raw_body = body
        if body:
            self._parse_body()

    def matches(self, lookup):
        """
        Does this description match lookup term (taxon)
        """
        for idx in self.index:
            if lookup in idx:
                return True
        return False

    def _parse_body(self):
        """
        Loop through the raw body text
        If it's a table move it into _tables property,other add to _paragraphs
        """
        soup = BeautifulSoup(self._raw_body, "html.parser")
        for el in soup.find_all(["p", "table"], recursive=False):
            l = self._tables if el.name == 'table' else self._paragraphs
            # Remove all embedded images - these cannot be included in the xml
            [x.extract() for x in el.findAll('img')]
            l.append(el)

    @property
    def voucher_fields(self):
        """
        Parse body text, splitting into voucher diagnosis & remarks
        """
        field_names = ['voucher', 'diagnosis', 'remarks']
        fields = {}
        # The body contains the taxonomy in headers at the top
        # Which needs to be stripped out, otherwise will duplicate data in
        # publication proper - so match the strong content
        # If we match on classification, we end up stripping out content from later in the
        # process e.g. tables with taxonomy in the description
        # instead we wait until the first paragraph matching Voucher, Diagnosis or Remarks
        # and discard all previous paragraphs

        # Loop through all of the strong tags, and see if it's voucher, diagnosis etc.,
        # If it is, then set the current field - used to key
        current_field = None
        for p in self._paragraphs:
            for strong in p.find_all("strong"):
                for field_name in field_names:
                    strong_text = strong.getText().lower()
                    fuzz_ratio = fuzz.partial_ratio(field_name, strong_text)
                    if fuzz_ratio > 99:
                        current_field = field_name
                        # Remove the strong label text
                        strong.extract()

            if current_field:
                fields.setdefault(current_field, []).append(p)

        return fields

    @property
    def body(self):
        return self._paragraphs

    @property
    def tables(self):
        return self._tables
