from __future__ import absolute_import

import re
from collections import Counter

from bs4 import BeautifulSoup, Comment

from .base import HttpSite


def html_unescape(content):
    try:
        import html
        return html.unescape(content)
    except ImportError:
        import HTMLParser
        html_parser = HTMLParser.HTMLParser()
        return html_parser.unescape(content)


class HtmlSite(HttpSite):
    def get_html(self):
        r = super(HtmlSite, self).get_content()
        body = r.text

        cleanup = self.conf["request"].get("cleanup", {})

        strip_comments = str(cleanup.get("strip_comments", False)).lower()
        if strip_comments in ("1", "yes", "true"):
            soup = BeautifulSoup(r.text, "html5lib")
            for comment in soup.find_all(text=lambda _: isinstance(_, Comment)):
                comment.extract()
            body = str(soup)

        return html_unescape(body)


class TableScraper(HtmlSite):
    @staticmethod
    def compare_rows(row1, row2):
        row1 = [cell.strip().lower() for cell in row1]
        row2 = [cell.strip().lower() for cell in row2]
        return (Counter(row1) == Counter(row2))

    @staticmethod
    def get_row_contents(row):
        return [cell.get_text().strip() for cell in row.find_all(["td", "th"])]

    @classmethod
    def find_table(cls, html, headers):
        soup = BeautifulSoup(html, "html5lib")
        for table in soup.find_all("table"):
            cells = cls.get_row_contents(table.find("tr"))
            if cls.compare_rows(cells, headers):
                return (table, cells)
        raise ValueError("No matching table found")

    def run(self):
        body = self.get_html()

        for parser in self.conf["results"]:
            (table, columns) = self.find_table(body, parser["map"].keys())
            for row in table.find_all("tr"):
                cells = self.get_row_contents(row)
                if self.compare_rows(cells, columns):
                    continue
                result_dict = dict(zip(columns, cells))
                yield self.build_result(parser, result_dict)


class Webscraper(HtmlSite):
    def run(self):
        body = self.get_html()

        if "results" not in self.conf:
            raise Exception("No parsing configuration found")
        for parser in self.conf["results"]:
            rex = re.compile(parser["regex"], flags=re.I)
            for match in rex.finditer(body):
                result_dict = dict()
                for (k, v) in zip(parser["values"], match.groups()):
                    result_dict[k] = v
                yield self.build_result(parser, result_dict)
