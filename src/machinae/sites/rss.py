from __future__ import absolute_import

import re

import feedparser

from .base import HttpSite


class RssSite(HttpSite):
    def get_content(self):
        r = super(RssSite, self).get_content()
        return feedparser.parse(r.text)

    def run(self):
        r = self._req(self.conf["request"])
        body = r.text

        rss = feedparser.parse(body)

        for entry in rss.entries:
            for parser1 in self.conf["results"]:
                result_dict = dict()
                for (key, parser) in parser1.items():
                    print(parser)
                    rex = re.compile(parser["regex"])
                    fieldnames = parser["values"]
                    if not isinstance(fieldnames, list):
                        fieldnames = [fieldnames]
                    rss_value = getattr(entry, key)
                    m = rex.search(rss_value)
                    if m:
                        result_dict.update(dict(zip(fieldnames, m.groups())))
                    else:
                        result_dict = None
                        break

                if result_dict is None:
                    continue

                yield self.build_result(parser, result_dict)
