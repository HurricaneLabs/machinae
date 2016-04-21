from __future__ import absolute_import

import datetime
import json
import re
import urllib.parse
from collections import OrderedDict

from dateutil.parser import parse

from .base import HttpSite


class JsonApi(HttpSite):
    @staticmethod
    def get_value(data, key, default=None):
        if key == "@" or data is None:
            return data
        ret = data
        key_parts = key.split(".")
        for key_part in key_parts:
            if key_part not in ret:
                return default
            ret = ret[key_part]
        return ret

    def get_json(self, url=None):
        r = self.get_content(url=url)

        ignored_status_codes = [int(sc) for sc in self.conf["request"].get("ignored_status_codes", [])]
        if r.status_code in ignored_status_codes:
            return []

        if not self.conf.get("multi_json", False):
            return r.json()

        if r.status_code in ignored_status_codes:
            return []

        results = list()
        for json_line in r.text.split("\n"):
            if not json_line:
                break
            results.append(json.loads(json_line))
        return results

    def run(self):
        data = self.get_json()

        if hasattr(data, "items"):
            next_url = None
            if self.conf.get("paginated", False):
                next_url = data.get("next", None)

            data = [data]
            while next_url:
                next_data = self.get_json(url=next_url)
                next_url = next_data.get("next", None)
                data.append(next_data)

        if "results" not in self.conf:
            return

        for row in data:
            for parser in self.conf["results"]:
                for _ in self.parse_dict(row, parser):
                    yield _

    @classmethod
    def get_result_dicts(cls, data, parser, mm_key=None, onlyif=None):
        if not hasattr(parser, "items"):
            parser = {"key": parser}

        if "key" not in parser:
            yield data
            return

        key = parser["key"]
        rex = None
        if "regex" in parser:
            rex = re.compile(parser["regex"], flags=re.I)

        if key == "@" and mm_key is not None:
            yield {key: mm_key}
            return

        values = cls.get_value(data, key)
        if values is None:
            return

        if not parser.get("match_all", False):
            values = [values]

        for val in values:
            result_dict = OrderedDict()

            if rex:
                m = rex.search(val)
                if not m:
                    return
                if len(m.groups()) > 0:
                    val = m.groups()
                    if len(val) == 1:
                        val = val[0]

            urldecode = str(parser.get("urldecode", False)).lower()
            if urldecode in ("1", "yes", "true"):
                val = urllib.parse.unquote(val)
            elif urldecode == "twice":
                val = urllib.parse.unquote(
                    urllib.parse.unquote(val)
                )

            if "format" in parser:
                if parser["format"] == "as_list":
                    val = ", ".join(map(str, val))
                elif parser["format"] == "as_time":
                    try:
                        dt = datetime.datetime.fromtimestamp(val)
                    except:
                        dt = parse(val)
                    val = dt.isoformat()
            result_dict[key] = val

            yield result_dict

    @classmethod
    def multi_match_generator(cls, data, parser, mm_key):
        if not hasattr(data, "items"):
            # Is a list, process each list item
            for item in data:
                for _ in cls.multi_match_generator(item, parser, mm_key="@"):
                    yield _

            return

        onlyif = parser.get("onlyif", None)
        if onlyif is not None and not hasattr(onlyif, "items"):
            onlyif = {"key": onlyif}

        # Decide how to iterate on the data
        # Options are:
        #   Return result_dict per match in dict (if: data is dict)
        #   Return one result_dict for whole dict (if: data is dict)
        if mm_key == "@" or parser.get("match_all", False):
            # Treat the entire data as a single match
            # Returns a single result_dict
            data = [(None, data)]
        else:
            # Each matching key is a separate result_dict
            data = data.items()

        for (k, v) in data:
            if onlyif is not None:
                if not hasattr(onlyif, "items"):
                    onlyif = {"key": onlyif}
                value = cls.get_value(v, onlyif["key"], None)

                if value is None:
                    continue
                elif "regex" in onlyif:
                    rex = re.compile(onlyif["regex"], re.I)
                    if not rex.search(value):
                        continue
                else:
                    if not bool(value):
                        continue
            result_dict = OrderedDict()
            for mm_parser in parser["keys"]:
                for mm_result_dict in cls.get_result_dicts(v, mm_parser, mm_key=k, onlyif=onlyif):
                    result_dict.update(mm_result_dict)

            if len(result_dict) > 0:
                result_dict.labels = parser.get("labels", None)
                yield result_dict

    def parse_dict(self, data, parser):
        if not hasattr(parser, "items"):
            parser = {"key": parser}

        if "multi_match" in parser:
            target = self.get_value(data, parser["key"])
            if target is None:
                return
            result_iter = self.multi_match_generator(target, parser["multi_match"], parser["key"])
        else:
            result_iter = self.get_result_dicts(data, parser)

        for result_dict in result_iter:
            yield self.build_result(parser, result_dict)
