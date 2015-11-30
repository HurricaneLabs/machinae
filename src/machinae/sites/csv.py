from __future__ import absolute_import

import csv
import io
import re

from .base import HttpSite


class CsvSite(HttpSite):
    _delim = None

    @property
    def dialect(self):
        if "pattern" not in self.conf:
            return "excel"

        class DelimDialect(csv.excel):
            delimiter = str(self.delim)
            skipinitialspace = True

        return DelimDialect()

    @property
    def delim(self):
        return self._delim or self.conf.get("pattern", ",")

    def get_content(self):
        r = super(CsvSite, self).get_content()
        body = r.text

        if len(self.delim) > 1:
            body = re.sub(self.conf["pattern"], "|", body)
            self._delim = "|"

        buf = io.StringIO(body)
        csvfile = csv.reader(buf, dialect=self.dialect)

        return csvfile

    def run(self):
        r = self._req(self.conf["request"])

        body = r.text
        if len(self.delim) > 1:
            body = re.sub(self.conf["pattern"], "|", body)
            self._delim = "|"

        buf = io.StringIO(body)
        csvfile = csv.reader(buf, dialect=self.dialect)

        for (lineno, row) in enumerate(csvfile):
            for parser in self.conf["results"]:
                start = parser.get("start", 1)
                stop = parser.get("end", None)

                # raise ValueError(start, stop)
                if lineno < start or len(row) == 0 or row[0].startswith("#"):
                    continue
                elif stop is not None and lineno > stop:
                    break

                if "match" in parser:
                    rex = re.compile(parser["match"]["regex"])
                    col = int(parser["match"]["column"])
                    if not rex.search(row[col]):
                        continue

                row = [item.strip() for item in row]
                result_dict = dict(zip(parser["values"], row))
                yield self.build_result(parser, result_dict)
