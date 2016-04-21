from __future__ import absolute_import

import gzip
import io
import warnings
import zipfile
from collections import OrderedDict

import magic
import pytz
import relatime
import requests
from tzlocal import get_localzone
try:
    from requests.packages.urllib3 import exceptions
except ImportError:
    # Apparently, some linux distros strip the packages out of requests
    # I'm not going to tell you what I think of that, just going to deal with it
    from urllib3 import exceptions

from . import Site


class HttpSite(Site):
    @property
    def url(self):
        print(self.conf["request"]["url"].format(**self.kwargs))
        return self.conf["request"]["url"].format(**self.kwargs)

    @property
    def session(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({"User-Agent": "Vor/1.0 (Like CIF/2.0)"})
            if self.proxies:
                self._session.proxies = self.proxies
        return self._session

    @staticmethod
    def unzip_content(r, *args, **kwargs):
        content = r.content

        with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
            mime = m.id_buffer(content)

        if mime == "application/zip":
            zip_buffer = io.BytesIO(content)
            with zipfile.ZipFile(zip_buffer) as zf:
                fn = zf.namelist()[0]
                with zf.open(fn) as f:
                    r._content = f.read()
        elif mime == "application/x-gzip":
            gz_buffer = io.BytesIO(content)
            with gzip.GzipFile(fileobj=gz_buffer) as gz:
                r._content = gz.read()
        else:
            r._content = content

        return r

    def _req(self, conf, url=None):
        if url is None:
            url = conf.get("url", "")
            if url == "":
                return
            url = url.format(**self.kwargs)
        method = conf.get("method", "get").upper()

        kwargs = dict()
        headers = conf.get("headers", {})
        if len(headers) > 0:
            kwargs["headers"] = headers
        verify_ssl = conf.get("verify_ssl", True)

        # GET params
        params = conf.get("params", {}).copy()
        for (k, v) in params.items():
            if hasattr(v, "items"):
                conf = params.pop(k)
                if "relatime" in conf:
                    dt = relatime.timeParser(conf["relatime"], timezone=str(get_localzone()))
                    target_tz = pytz.timezone(conf.get("timezone", "UTC"))
                    dt = dt.astimezone(target_tz)
                    dt = dt.replace(tzinfo=None)
                    time_format = conf.get("format", "%Y-%m-%dT%H:%M:%S.%fZ")
                    if time_format.lower() == "as_epoch":
                        params[k] = str(int(dt.timestamp()))
                    else:
                        params[k] = dt.strftime(time_format)
            else:
                params[k] = str(v).format(**self.kwargs)
        if len(params) > 0:
            kwargs["params"] = params

        # POST data
        data = conf.get("data", {})
        for (k, v) in data.items():
            data[k] = v.format(**self.kwargs)
        if len(data) > 0:
            kwargs["data"] = data

        # HTTP Basic Auth
        if conf.get("auth") and self.creds and self.creds.get(conf["auth"]):
            kwargs["auth"] = tuple(self.creds[conf["auth"]])

        # Auto decompress
        if conf.get("decompress", False):
            kwargs["hooks"] = {"response": self.unzip_content}

        raw_req = requests.Request(method, url, **kwargs)
        req = self.session.prepare_request(raw_req)
        if self.kwargs.get("verbose", False):
            print("[.] Requesting {0} ({1})".format(req.url, req.method))
        with warnings.catch_warnings():
            if not verify_ssl:
                warnings.simplefilter("ignore", exceptions.InsecureRequestWarning)
            return self.session.send(req, verify=verify_ssl)

    def get_content(self, conf=None, url=None):
        if conf is None:
            conf = self.conf["request"]

        r = self._req(conf, url)
        ignored_status_codes = [int(sc) for sc in conf.get("ignored_status_codes", [])]
        if r.status_code not in ignored_status_codes:
            r.raise_for_status()
        return r

    def build_result(self, parser, result_dict):
        defaults_dict = parser.get("defaults", {})

        result = OrderedDict()
        result.update(defaults_dict)
        result.update(result_dict)

        result.pop(None, None)

        if "map" in parser:
            for (old, new) in parser["map"].items():
                if new is None:
                    result.pop(old)
                elif old in result:
                    result[new] = result.pop(old)

        # fmt = dict()
        # for (k, v) in result.items():
        #     fk = "<{0}>".format(k)
        #     fmt[fk] = str(v)
        #
        # for (k, v) in result.items():
        #     for (find, replace) in fmt.items():
        #         try:
        #             result[k] = v.replace(find, replace)
        #         except AttributeError:
        #             pass

        if "defaults" in parser:
            for (k, v) in parser["defaults"].items():
                result[k] = v

        if "pretty_name" in parser:
            result = OrderedDict([
                ("value", result),
                ("pretty_name", parser["pretty_name"])
            ])

        if hasattr(result_dict, "labels"):
            result.labels = result_dict.labels

        return result
