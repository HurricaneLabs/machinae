import argparse
import copy
import os
import sys
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
import stopit
from machinae import __version__

from . import dict_merge, get_target_type, outputs, utils
from . import ErrorResult, Result, ResultSet, SiteResults, TargetInfo
from .sites import Site



def _run_single_site_for_target(
    site_name,
    site_conf,
    target_info,
    creds,
    proxies,
    verbose,
    timeout_seconds=15,
    delay_seconds=0,
):
    """
    Run one site for one target and return either:
      * SiteResults(site_info, [Result(...), ...]), or
      * ErrorResult(target_info, site_info, error)

    Returns None if the site does not support this otype.
    """
    target, otype, _ = target_info

    # Respect otype filtering just like the original logic
    if otype.lower() not in map(lambda x: x.lower(), site_conf.get("otypes", [])):
        return None

    # Work on a copy so threads don't stomp each other's config
    site_conf = copy.deepcopy(site_conf)
    site_conf["target"] = target
    site_conf["verbose"] = verbose
    # Keep track of the site name so we can restore ordering later if needed
    site_conf["name"] = site_name

    scraper = Site.from_conf(site_conf, creds=creds, proxies=proxies)

    # Respect delay between requests if configured
    if delay_seconds:
        time.sleep(delay_seconds)

    try:
        run_results = []
        # Use stopit.ThreadingTimeout here: works in worker threads and avoids
        # the "signal only works in main thread" problem from SignalTimeout.
        with stopit.ThreadingTimeout(timeout_seconds, swallow_exc=False):
            for r in scraper.run():
                if "value" not in r:
                    r = {"value": r, "pretty_name": None}
                run_results.append(Result(r["value"], r["pretty_name"]))
    except stopit.TimeoutException:
        return ErrorResult(target_info, site_conf, "Timeout")
    except Exception as e:  # pylint: disable=broad-except
        # This mirrors the original broad exception handling
        return ErrorResult(target_info, site_conf, e)
    else:
        return SiteResults(site_conf, run_results)

default_config_locations = (
    "machinae.yml",
    "/etc/machinae.yml",
    os.path.expanduser(os.getenv("MACHINAE_CONFIG", "")),
)


class MachinaeCommand:
    _conf = None
    _sites = None

    def __init__(self, args=None):
        if args is None:
            ap = argparse.ArgumentParser()
            ap.add_argument("-c", "--config", default=None)
            ap.add_argument("--nomerge", default=False, action="store_true")

            ap.add_argument("-d", "--delay", default=0)
            ap.add_argument("-f", "--file", default="-")
            ap.add_argument("-i", "--infile", default=None)
            ap.add_argument("-o", dest="output", default="N", choices=("D", "J", "N", "S"))
            ap.add_argument("-O", "--otype",
                            choices=("ipv4", "ipv6", "fqdn", "email", "sslfp", "hash", "url", "mac")
                            )
            ap.add_argument("-q", "--quiet", dest="verbose", default=True, action="store_false")
            ap.add_argument("-s", "--sites", default="default")
            ap.add_argument("-w", "--workers", type=int, default=10,
                            help="Maximum concurrent site lookups per target")
            ap.add_argument("-a", "--auth")
            ap.add_argument("-H", "--http-proxy", dest="http_proxy")
            ap.add_argument("targets", nargs=argparse.REMAINDER)
            ap.add_argument("-v", "--version", action="version", version="%(prog)s "+ __version__)

            modes = ap.add_mutually_exclusive_group()
            modes.add_argument("--dump-config", dest="mode",
                               action="store_const", const="dump_config")
            modes.add_argument("--detect-otype", dest="mode",
                               action="store_const", const="detect_otype")
            modes.add_argument("--list-sites", dest="mode",
                               action="store_const", const="list_sites")
            args = ap.parse_args()
        self.args = args

    @property
    def conf(self):
        if self._conf is None:
            path = None
            if self.args.config:
                path = self.args.config
            else:
                for possible_path in default_config_locations:
                    if possible_path is None:
                        continue
                    if os.path.exists(possible_path):
                        path = possible_path
                        break

            if path:
                with open(path, "r") as f:
                    conf = utils.safe_load(f)
            else:
                conf = {}

            if not self.args.nomerge:
                local_path = "/etc/machinae.local.yml"
                if os.path.exists(local_path):
                    with open(local_path, "r") as f:
                        local_conf = utils.safe_load(f)
                    conf = dict_merge(conf, local_conf)

                local_path = os.path.expanduser("~/.machinae.yml")
                if os.path.exists(local_path):
                    with open(local_path, "r") as f:
                        local_conf = utils.safe_load(f)
                    conf = dict_merge(conf, local_conf)

            self._conf = conf
        return self._conf

    @property
    #pylint: disable=too-many-locals, too-many-branches
    def results(self):
        """
        Yield ResultSet objects for each target, but run the per-site lookups
        concurrently to speed things up.

        External behavior (what the rest of Machinae sees) is unchanged:
        this is still a generator of ResultSet instances.
        """
        creds = None
        if self.args.auth and os.path.isfile(self.args.auth):
            with open(self.args.auth) as auth_f:
                creds = utils.safe_load(auth_f.read())

        proxies = {}
        if self.args.http_proxy:
            proxies["http"] = self.args.http_proxy
            proxies["https"] = self.args.http_proxy
        else:
            if "HTTP_PROXY" in os.environ:
                proxies["http"] = os.environ["HTTP_PROXY"]
            elif "http_proxy" in os.environ:
                proxies["http"] = os.environ["http_proxy"]
            if "HTTPS_PROXY" in os.environ:
                proxies["https"] = os.environ["HTTPS_PROXY"]
            elif "https_proxy" in os.environ:
                proxies["https"] = os.environ["https_proxy"]

        if "http" in proxies:
            print("HTTP Proxy: {http}".format(**proxies), file=sys.stderr)
        if "https" in proxies:
            print("HTTPS Proxy: {https}".format(**proxies), file=sys.stderr)

        # Iterate over targets as before, but fan out per-site work with a pool
        for target_info in self.targets:
            target, otype, _ = target_info
            target_results = []

            # Figure out which sites apply to this otype, preserving config order
            all_sites = list(self.sites.items())
            sites_for_target = [
                (site_name, site_conf)
                for (site_name, site_conf) in all_sites
                if otype.lower()
                in map(lambda x: x.lower(), site_conf.get("otypes", []))
            ]

            if not sites_for_target:
                # Nothing to do for this target
                yield ResultSet(target_info, target_results)
                continue

            # Remember ordering so we can restore it after concurrent execution
            order_index = {name: idx for idx, (name, _) in enumerate(sites_for_target)}

            # Reasonable cap on workers
            # Use the smaller of: user-specified workers or number of sites
            max_workers = min(self.args.workers, len(sites_for_target))

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(
                        _run_single_site_for_target,
                        site_name,
                        site_conf,
                        target_info,
                        creds,
                        proxies,
                        self.args.verbose,
                        timeout_seconds=15,
                        delay_seconds=int(self.args.delay),
                    )
                    for (site_name, site_conf) in sites_for_target
                ]

                for fut in as_completed(futures):
                    site_result = fut.result()
                    if site_result is not None:
                        target_results.append(site_result)

            # Re-sort results to match original site order
            def _sort_key(res):
                site_info = res.site_info
                site_name = site_info.get("name", "")
                return order_index.get(site_name, 0)

            target_results.sort(key=_sort_key)

            # Yield the ResultSet for this target (same as before)
            yield ResultSet(target_info, target_results)

    @property
    def sites(self):
        if self._sites is None:
            if self.args.sites.lower() == "all":
                sites = self._conf.keys()
            elif self.args.sites.lower() == "default":
                sites = [k for (k, v) in self.conf.items() if v.get("default", True)]
            else:
                sites = self.args.sites.lower().split(",")
            self._sites = OrderedDict([(k, v) for (k, v) in self.conf.items() if k in sites])
        return copy.deepcopy(self._sites)

    @property
    def targets(self):
        targets = list()
        if self.args.infile:
            with open(self.args.infile, "r") as f:
                targets.extend([line.strip() for line in f.readlines()])

        targets.extend(self.args.targets)

        for target in targets:
            (otype, otype_detected) = self.detect_otype(target)
            if otype == "url" and not (target.startswith("http://") or target.startswith("https://")):
                target = "http://{0}".format(target)
            yield TargetInfo(target, otype, otype_detected)

    def detect_otype(self, target):
        if self.args.otype:
            return (self.args.otype, False)
        return (get_target_type(target), True)

    def run(self):
        fmt = self.args.output.upper()
        dest = self.args.file

        if not self.conf:
            sys.stderr.write("Warning: operating without a config file. This is probably not what "
                             "you want. To correct this, fetch a copy of the default "
                             "configuration file from https://github.com/hurricanelabs/machinae "
                             "and place it in /etc/machinae.yml or ~/.machinae.yml and run again."
                             "\n")

        if self.args.mode == "dump_config":
            output = utils.dump(self.conf)
        elif self.args.mode == "detect_otype":
            target_dict = OrderedDict()
            for target_info in self.targets:
                target_dict.update({target_info.target: target_info.otype})
            output = utils.dump(target_dict)
        elif self.args.mode == "list_sites":
            output = utils.listsites(self.conf)
        else:
            output = outputs.MachinaeOutput.get_formatter(fmt).run(self.results)

        if dest == "-":
            ofile = sys.stdout
        else:
            ofile = open(dest, "w")

        ofile.write(output)

        if dest != "-":
            ofile.close()


def main():
    try:
        cmd = MachinaeCommand()
        cmd.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
