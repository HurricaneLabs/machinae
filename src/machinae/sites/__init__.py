from __future__ import absolute_import

import urllib.parse


class Site(object):
    _session = None
    _kwargs = None

    def __init__(self, conf, creds=None, proxies=None):
        self.conf = conf
        self.creds = creds
        self.proxies = proxies

    def kwargs_getter(self):
        return self._kwargs

    def kwargs_setter(self, kwargs):
        if "target" in kwargs:
            target = kwargs.pop("target")
            if "target" in self.conf.get("request", {}):
                target_conf = self.conf["request"]["target"]

                # PTR-style
                ptr_style = str(target_conf.get("ptr", False)).lower()
                if ptr_style in ("1", "yes", "true"):
                    target = ".".join(reversed(target.split(".")))

                urlencode = str(target_conf.get("urlencode", False)).lower()
                if urlencode in ("1", "yes", "true"):
                    target = urllib.parse.quote(target)
                elif urlencode == "twice":
                    target = urllib.parse.quote(
                        urllib.parse.quote(target, safe="")
                    )

                if "format" in target_conf:
                    target = target_conf["format"] % (target,)

            kwargs["target"] = target

        self._kwargs = kwargs

    kwargs = property(kwargs_getter, kwargs_setter)

    @staticmethod
    def from_conf(conf, *args, **kwargs):
        from . import csv, html, rss, json, ipwhois
        if "webscraper" in conf:
            site_conf = conf.pop("webscraper")
            scraper = html.Webscraper(site_conf, *args, **kwargs)
        elif "tablescraper" in conf:
            site_conf = conf.pop("tablescraper")
            scraper = html.TableScraper(site_conf, *args, **kwargs)
        elif "json" in conf:
            site_conf = conf.pop("json")
            scraper = json.JsonApi(site_conf, *args, **kwargs)
        elif "csv" in conf:
            site_conf = conf.pop("csv")
            scraper = csv.CsvSite(site_conf, *args, **kwargs)
        elif "rss" in conf:
            site_conf = conf.pop("rss")
            scraper = rss.RssSite(site_conf, *args, **kwargs)
        elif "ipwhois" in conf:
            site_conf = conf.pop("ipwhois")
            scraper = ipwhois.IpWhois(site_conf, *args, **kwargs)
        # elif "dns" in conf:
        #     scraper = DnsSite(conf["dns"], *args, **kwargs)
        # elif "ipwhois" in conf:
        #     scraper = IpWhois(conf["ipwhois"], *args, **kwargs)
        else:
            raise NotImplementedError(conf.keys())
        scraper.kwargs = conf.copy()
        return scraper

    def get_content(self):
        raise NotImplementedError

    def __iter__(self):
        for _ in self.run():
            yield _
