import collections
import re
import socket
import ipaddress

__version__ = "1.4.8"
TargetInfo = collections.namedtuple("TargetInfo", ("target", "otype", "otype_detected"))
ErrorResult = collections.namedtuple("ErrorResult", ("target_info", "site_info", "error_info"))
ResultSet = collections.namedtuple("ResultSet", ("target_info", "results"))
SiteResults = collections.namedtuple("SiteResults", ("site_info", "resultset"))
Result = collections.namedtuple("Result", ("value", "pretty_name"))

#pylint: disable=no-else-return,too-many-return-statements
def get_target_type(target):
    try:
        getVer = ipaddress.ip_address(target)
        if getVer.version == 4:
            return "ipv4"
        elif getVer.version == 6:
            return "ipv6"
    except ValueError:
        pass

    #pylint: disable=no-else-return
    # Hashes
    if re.match("^[a-f0-9]{32}$", target, re.I):
        # MD5
        return "hash"
    elif re.match("^[a-f0-9]{40}$", target, re.I):
        # SHA-1
        return "hash.sha1"
    elif re.match("^[a-f0-9]{64}$", target, re.I):
        # SHA-256
        return "hash.sha256"
    elif re.match("^[a-f0-9]{128}$", target, re.I):
        # SHA-512
        return "hash.sha512"

    # URL
    elif re.match("^https?://", target, re.I):
        return "url"

    # Email Addresses
    elif re.match("^.*?@.*?$", target, re.I):
        return "email"

    # SSL fingerprints
    elif re.match("^(?:[a-f0-9]{2}:){19}[a-f0-9]{2}$", target, flags=re.I):
        return "sslfp"

    # Mac Addresses
    elif re.match("^([0-9a-fA-F][0-9a-fA-F][-:\.]){5}([0-9a-fA-F][0-9a-fA-F])$", target, re.I):
        return "mac"

    return "fqdn"


# d2 takes precedence
def dict_merge(d1, d2):
    d3 = d1.copy()
    for key in d2:
        if key in d3 and hasattr(d3[key], "items") and hasattr(d2[key], "items"):
            d3[key] = dict_merge(d3[key], d2[key])
        elif hasattr(d2[key], "items"):
            d3[key] = d2[key].copy()
        else:
            d3[key] = d2[key]
    return d3
