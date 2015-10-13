import html
import itertools
import re
import sys
import warnings
from collections import OrderedDict

import ipwhois
import requests
from requests.packages.urllib3 import exceptions

from . import Result


class Site:
    _session = None

    def __init__(self, conf, verbose=False):
        self.conf = conf
        self.verbose = verbose

    @staticmethod
    def from_conf(conf, verbose=False):
        if "webscraper" in conf:
            scraper = Webscraper(conf["webscraper"], verbose)
        elif "json" in conf:
            scraper = JsonApi(conf["json"], verbose)
        elif "dns" in conf:
            scraper = DnsSite(conf["dns"], verbose)
        elif "ipwhois" in conf:
            scraper = IpWhois(conf["ipwhois"], verbose)
        else:
            raise NotImplementedError
        return scraper

    def run(self, target):
        raise NotImplementedError

    def get_target_dict(self, target):
        return {"target": target}


class DnsSite(Site):
    def get_target_dict(self, target):
        tdict = super().get_target_dict(target)
        tdict["target_stripped"] = target.replace(":", "")
        return tdict

    def _req(self, target, conf):
        try:
            import dns.exception
            import dns.resolver
        except ImportError:
            return []

        tdict = self.get_target_dict(target)

        query = conf["query"].format(**tdict)
        print("[.] Requesting {0} ({1})".format(query, conf["rrtype"]))
        try:
            answers = dns.resolver.query(query, conf["rrtype"])
        except dns.exception.Timeout:
            return []
        return answers

    def run(self, target):
        answers = self._req(target, self.conf["request"])

        results = list()
        for parser in self.conf["results"]:
            rex = re.compile(parser["regex"], flags=re.I)
            for answer in answers:
                m = rex.search(answer.to_text())
                if m:
                    result_dict = OrderedDict()
                    for (key, val) in zip(parser["values"], m.groups()):
                        result_dict[key] = val
                    result = Result(result_dict, parser["pretty_name"])
                    if result not in results:
                        results.append(result)
        return results


class HttpSite(Site):
    @property
    def session(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({"User-Agent": "Machinae/1.0 (Like Automater/2.1)"})
        return self._session

    def _req(self, target, conf):
        tdict = self.get_target_dict(target)

        url = conf.get("url", "").format(**tdict)
        if url == "":
            return
        method = conf.get("method", "get").upper()

        kwargs = dict()
        headers = conf.get("headers", {})
        if len(headers) > 0:
            kwargs["headers"] = headers
        verify_ssl = conf.get("verify_ssl", True)

        # GET params
        params = conf.get("params", {}).copy()
        for (k, v) in params.items():
            params[k] = str(v).format(**tdict)
        if len(params) > 0:
            kwargs["params"] = params

        # POST data
        data = conf.get("data", {})
        for (k, v) in data.items():
            data[k] = v.format(**tdict)
        if len(data) > 0:
            kwargs["data"] = data

        raw_req = requests.Request(method, url, **kwargs)
        req = self.session.prepare_request(raw_req)
        if self.verbose:
            print("[.] Requesting {0} ({1})".format(req.url, req.method))
        with warnings.catch_warnings():
            if not verify_ssl:
                warnings.simplefilter("ignore", exceptions.InsecureRequestWarning)
            return self.session.send(req, verify=verify_ssl)


class JsonApi(HttpSite):
    @staticmethod
    def get_value(data, key):
        if key == "@" or data is None:
            return data
        ret = data
        key_parts = key.split(".")
        for key_part in key_parts:
            if key_part not in ret:
                return None
            ret = ret[key_part]
        return ret

    def get_json(self, target):
        r = self._req(target, self.conf["request"])
        r.raise_for_status()
        try:
            return r.json()
        except:
            raise Exception("Error parsing JSON response")

    def run(self, target):
        data = self.get_json(target)

        if hasattr(data, "items"):
            data = [data]

        if "results" not in self.conf:
            return []

        results = list()
        for row in data:
            for parser in self.conf["results"]:
                for result in self.parse_dict(row, parser):
                    if result not in results:
                        results.append(result)

        return results

    @classmethod
    def get_result_dicts(cls, data, parser, mm_key=None, onlyif=None):
        if not hasattr(parser, "items"):
            parser = {"key": parser}

        key = parser["key"]
        rex = None
        if "regex" in parser:
            rex = re.compile(parser["regex"], flags=re.I)

        if key == "@" and mm_key is not None:
            yield {key: mm_key}
            raise StopIteration

        values = cls.get_value(data, key)
        if values is None:
            raise StopIteration

        if not parser.get("match_all", False):
            values = [values]

        for val in values:
            result_dict = OrderedDict()

            if rex:
                try:
                    m = rex.search(val)
                except TypeError as e:
                    msg = "[BUG] {0}\n".format(e)
                    msg += "    [-] Parser: {0}\n".format(str(parser))
                    msg += "    [-] Regex: {0}\n".format(str(parser["regex"]))
                    msg += "    [-] Value: {0}\n".format(str(val))
                    sys.stderr.write(msg)
                    raise StopIteration
                if not m:
                    raise StopIteration
                if len(m.groups()) > 0:
                    val = m.groups()
                    if len(val) == 1:
                        val = val[0]

            result_dict[key] = val

            yield result_dict

    @classmethod
    def multi_match_generator(cls, data, parser, mm_key):
        if not hasattr(data, "items"):
            # Is a list, process each list item
            for item in data:
                yield from cls.multi_match_generator(item, parser, mm_key="@")

            raise StopIteration

        onlyif = parser.get("onlyif", None)
        if onlyif is not None and not hasattr(onlyif, "items"):
            onlyif = {"key": onlyif}

        # Decide how to iterate on the data
        # Options are:
        #   Return result_dict per match in dict (if: data is dict)
        #   Return one result_dict for whole dict (if: data is dict)
        if mm_key == "@":
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
                value = v.get(onlyif["key"], None)

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
                yield result_dict

    @classmethod
    def parse_dict(cls, data, parser):
        if not hasattr(parser, "items"):
            parser = {"key": parser}

        if "multi_match" in parser:
            target = cls.get_value(data, parser["key"])
            if target is None:
                return []
            result_iter = cls.multi_match_generator(target, parser["multi_match"], parser["key"])
        else:
            result_iter = cls.get_result_dicts(data, parser)

        results = list()
        for result_dict in result_iter:
            result = Result(result_dict, parser["pretty_name"])
            if result not in results:
                results.append(result)
        return results

    def parse_dict_2(self, data, parser):
        data_part = self.get_value(data, parser["key"])

        results = list()

        if data_part is None:
            return results

        if "multi_match" in parser:
            if hasattr(data_part, "items"):
                if parser["key"] == "@":
                    data_iter = [(None, data_part)]
                else:
                    data_iter = data_part.items()
            else:
                data_iter = zip(itertools.repeat(None), data_part)

            for (k, v) in data_iter:
                if "onlyif" in parser["multi_match"]:
                    key = parser["multi_match"]["onlyif"]
                    val = v[key]
                    if not val:
                        continue

                result_dict = OrderedDict()
                for match in parser["multi_match"]["keys"]:
                    rex = None
                    if hasattr(match, "items"):
                        rex = re.compile(match["regex"])
                        match = match["key"]
                    if match == "@":
                        val = k
                    else:
                        val = v[match]

                    if rex:
                        m = rex.search(val)
                        if m is None:
                            continue
                        val = m.groups()
                        if len(val) == 1:
                            val = val[0]

                    if val is None:
                        continue
                    result_dict[match] = val

                if len(result_dict) == 0:
                    continue
                result = Result(result_dict, parser["pretty_name"])
                if result not in results:
                    results.append(result)
        else:
            match_all = parser.get("match_all", False)

        return results


class IpWhois(JsonApi):
    def get_json(self, target):
        obj = ipwhois.IPWhois(target)
        return obj.lookup_rws()


class Webscraper(HttpSite):
    def run(self, target):
        if "setup" in self.conf:
            self._req(target, self.conf["setup"])

        r = self._req(target, self.conf["request"])
        body = r.text

        strip_comments = str(self.conf["request"].get("strip_comments", False)).lower()
        if strip_comments in ("1", "yes", "true"):
            try:
                from bs4 import BeautifulSoup, Comment
            except:
                pass
            else:
                soup = BeautifulSoup(r.text)
                for comment in soup.find_all(text=lambda _: isinstance(_, Comment)):
                    comment.extract()
                body = str(soup)

        body = html.unescape(body)

        results = list()
        if "results" not in self.conf:
            raise Exception("No parsing configuration found")
        for parser in self.conf["results"]:
            rex = re.compile(parser["regex"], flags=re.I)
            for match in rex.finditer(body):
                result_dict = dict()
                for (k, v) in zip(parser["values"], match.groups()):
                    result_dict[k] = v
                result = Result(result_dict, parser["pretty_name"])
                if result not in results:
                    results.append(result)

        return results
