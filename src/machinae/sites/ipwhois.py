from ipaddress import ip_address, summarize_address_range

import ipwhois

from .json import JsonApi


class IpWhois(JsonApi):
    @staticmethod
    def get_cidr(network):
        networks = [str(net) for net in summarize_address_range(
            ip_address(network["start_address"]),
            ip_address(network["end_address"])
        )]
        if len(networks) == 1:
            networks = networks[0]
        return networks

    def get_json(self):
        obj = ipwhois.IPWhois(self.kwargs["target"])
        try:
            # import json
            # print(json.dumps(obj.lookup_rdap(depth=2)))
            # return obj.lookup_rdap(depth=2)
            return obj.lookup_rws()
        except AttributeError:
            # rdap = obj.lookup_rdap(inc_raw=True)
            # print(json.dumps(rdap))
            # rdap["network"]["range"] = "{start_address} - {end_address}".format(**rdap["network"])
            # rdap["network"]["cidr"] = self.get_cidr(rdap["network"])
            # return rdap
            # RDAP is a stupid format, use raw whois
            raw = obj.lookup()
            print(raw)
            return raw
