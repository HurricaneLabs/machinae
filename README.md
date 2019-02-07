[![Build Status](https://travis-ci.org/HurricaneLabs/machinae.svg?branch=master)](https://travis-ci.org/HurricaneLabs/machinae)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/2344/badge)](https://bestpractices.coreinfrastructure.org/projects/2344)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=HurricaneLabs_machinae&metric=alert_status)](https://sonarcloud.io/dashboard?id=HurricaneLabs_machinae)

![Machinae Logo](images/machinae.jpg)


Machinae Security Intelligence Collector
========================================

Machinae is a tool for collecting intelligence from public sites/feeds about
various security-related pieces of data: IP addresses, domain names, URLs,
email addresses, file hashes and SSL fingerprints. It was inspired by
[Automater][1], another excellent tool for collecting information. The Machinae
project was born from wishing to improve Automater in 4 areas:

1. Codebase - Bring Automater to python3 compatibility while making the code
more pythonic
2. Configuration - Use a more human readable configuration format (YAML)
3. Inputs - Support JSON parsing out-of-the-box without the need to write
regular expressions, but still support regex scraping when needed
4. Outputs - Support additional output types, including JSON, while making
extraneous output optional


Installation
------------

Machinae can be installed using pip3:

    pip3 install machinae

Or, if you're feeling adventurous, can be installed directly from github:

    pip3 install git+https://github.com/HurricaneLabs/machinae.git

You will need to have whatever dependencies are required on your system for
compiling Python modules (on Debian based systems, `python3-dev`), as well as
the libyaml development package (on Debian based systems, `libyaml-dev`).

You'll also want to grab the [latest configuration file][2] and place it in
`/etc/machinae.yml`.


Configuration File
------------------

Machinae supports a simple configuration merging system to allow you to make
adjustments to the configuration without modifying the machinae.yml we provide
you, making configuration updates a snap. This is done by finding a system-wide
default configuration (default `/etc/machinae.yml`), merging into that a
system-wide local configuration (`/etc/machinae.local.yml`) and finally a
per-user local configuration (`~/.machinae.yml`). The system-wide configuration
can also be located in the current working directory, can be set using the
`MACHINAE_CONFIG` environment variable, or of course by using the `-c` or
`--config` command line options. Configuration merging can be disabled by
passing the `--nomerge` option, which will cause Machinae to only load the
default system-wide configuration (or the one passed on the command line).

As an example of this, say you'd like to enable the Fortinet Category site,
which is disabled by default. You could modify `/etc/machinae.yml`, but these
changes would be overwritten by an update. Instead, you can put the following
in either `/etc/machinae.local.yml` or `~/.machinae.yml`:

    fortinet_classify:
      default: true

Or, conversely, to disable a site, such as Virus Total pDNS:

    vt_ip:
      default: false
    vt_domain:
      default: false


Usage
-----

Machinae usage is very similar to Automater:

    usage: machinae [-h] [-c CONFIG] [--nomerge] [-d DELAY] [-f FILE] [-i INFILE] [-v]
                [-o {D,J,N,S}] [-O {ipv4,ipv6,fqdn,email,sslfp,hash,url}] [-q]
                [-s SITES] [-a AUTH] [-H HTTP_PROXY]
                [--dump-config | --detect-otype]
                ...

- See above for details on the `-c`/`--config` and `--nomerge` options.

- Machinae supports a `-d`/`--delay` option, like Automater. However, Machinae
uses 0 by default.

- Machinae output is controlled by two arguments:
    - `-o` controls the output format, and can be followed by a single character
	to indicated the desired type of output:
		- *N* is the default output ("Normal")
		- *D* is the default output, but dot characters are replaced
		- *J* is JSON output
	- `-f`/`--file` specifies the file where output should be written. The default
	is "-" for stdout.

- Machinae will attempt to auto-detect the type of target passed in (Machinae
refers to targets as "observables" and the type as "otype"). This detection can
be overridden with the `-O`/`--otype` option. The choices are listed in the
usage

- By default, Machinae operates in verbose mode. In this mode, it will output
status information about the services it is querying on the console as they are
queried. This output will always be written to stdout, regardless of the output
setting. To disable verbose mode, use `-q`

- By default, Machinae will run through all services in the configuration that
apply to each target's otype *and* are not marked as "default: false". To modify
this behavior, you can:
    - Pass a comma separated list of sites to run (use the top level key from the
	configuration).
	- Pass the special keyword `all` to run through all services *including* those
	marked as "default: false"

	Note that in both cases, `otype` validation is still applied.

- Machinae supports passing an HTTP proxy on the command line using the
`-H`/`--http-proxy` argument. If no proxy is specified, machinae will search the
standard `HTTP_PROXY` and `HTTPS_PROXY` environment variables, as well as the
less standard `http_proxy` and `https_proxy` environment variables.

- Lastly, a list of targets should be passed. All arguments other than the
options listed above will be interpreted as targets.


Out-of-the-Box Data Sources
---------------------------

Machinae comes with out-of-the-box support for the following data sources:

- IPVoid
- URLVoid
- URL Unshortener (http://www.toolsvoid.com/unshorten-url)
- Malc0de
- SANS
- FreeGeoIP (freegeoip.io)
- Fortinet Category
- VirusTotal pDNS (via web scrape - commented out)
- VirusTotal pDNS (via JSON API)
- VirusTotal URL Report (via JSON API)
- VirusTotal File Report (via JSON API)
- Reputation Authority
- ThreatExpert
- VxVault
- ProjectHoneypot
- McAfee Threat Intelligence
- StopForumSpam
- Cymru MHR
- ICSI Certificate Notary
- TotalHash (disabled by default)
- DomainTools Parsed Whois (Requires API key)
- DomainTools Reverse Whois (Requires API key)
- DomainTools Reputation
- IP WHOIS (Using RIR REST interfaces)
- Hacked IP
- Metadefender Cloud (Requires API key)
- GreyNoise (Requires API key)
- IBM XForce (Required API key)

With additional data sources on the way.

HTTP Basic Authentication and Configuration
-------------------------------------------

Machinae supports HTTP Basic Auth for sites that require it through the `--auth/-a`
flag. You will need to create a YAML file with your credentials, which will include
a key to the site that requires the credentials and a list of two items, username
and password or API key. For example, for the included PassiveTotal site this might
look like:

    passivetotal: ['myemail@example.com', 'my_api_key']

Inside the site configuration under `request` you will see a key such as:

    json:
      request:
        url: '...'
        auth: passivetotal

The `auth: passivetotal` points to the key inside the authentication config passed
via the command line.

### Disabled by default

The following sites are disabled by default

- Fortinet Category (`fortinet_classify`)
- Telize Geo IP (`telize`)
- TotalHash (`totalhash_ip`)
- DomainTools Parsed Whois (`domaintools_parsed_whois`)
- DomainTools Reverse Whois (`domaintools_reverse_whois`)
- DomainTools Reputation (`domaintools_reputation`)
- PassiveTotal Passive DNS (`passivetotal_pdns`)
- PassiveTotal Whois (`passivetotal_whois`)
- PassiveTotal SSL Certificate History (`passivetotal_sslcert`)
- PassiveTotal Host Attribute Components (`passivetotal_components`)
- PassiveTotal Host Attribute Trackers (`passivetotal_trackers`)
- MaxMind GeoIP2 Passive Insight (`maxmind`)
- FraudGuard (`fraudguard`)
- Shodan (`shodan`)
- Hacked IP
- Metadefender Cloud (Requires API key)
- GreyNoise (Requires API key)
- IBM XForce (Requires API key)

Output Formats
--------------

Machinae comes with a limited set of output formats: normal, normal with dot
escaping, and JSON. We plan to add additional output formats in the future.


Adding additional sites
-----------------------

*** COMING SOON ***


Known Issues
------------

- Some ISP's on IPvoid contain double-encoded HTML entities, which are not
double-decoded


Upcoming Features
-----------------

- Add IDS rule search functionality (VRT/ET)
- Add "More info" link for sites
- Add "dedup" option to parser settings
- Add option for per-otype request settings
- Add custom per-site output for error codes


Version History
---------------

### Version 1.4.1 (2018-08-31) ###
- New Features
    - Automatically Defangs output
    - MISP Support (example added to machinae.yml)
    
### Version 1.4.0 (2016-04-20) ###
- New features
    - "-a"/"--auth" option for passing an auth config file
        - Thanks johannestaas for the submission
    - "-H"/"--http-proxy" option, and environment support, for HTTP proxies
- New sites
    - Passivetotal (various forms, thanks johannestaas)
    - MaxMind
    - FraudGuard
    - Shodan
- Updated sites
    - FreeGeoIP (replaced freegeoip.net with freegeoip.io)

### Version 1.3.4 (2016-04-01) ###
- Bug fixes
    - Convert exceptions to str when outputting to JSON
        - Should actually close #14

### Version 1.3.3 (2016-03-28) ###
- Bug fixes
    - Correctly handle error results when outputting to JSON
        - Closes #14
        - Thanks Den1al for the bug report

### Version 1.3.2 (2016-03-10) ###
- New features
    - "Short" output mode - simply output yes/no/error for each site
    - "-i"/"--infile" option for passing a file with list of targets

### Version 1.3.1 (2016-03-08) ###

- New features
    - Prepend "http://" to URL targets when not starting with http:// or https://

### Version 1.3.0 (2016-03-07) ###

- New sites
    - Cymon.io - Threat intel aggregator/tracker by eSentire
- New features
    - Support simple paginated responses
    - Support url encoding 'target' in request URL
    - Support url decoding values in results

### Version 1.2.0 (2016-02-16) ###

- New features
    - Support for sites returning multiple JSON documents
    - Ability to specify time format for relative time parameters
    - Ability to parse Unix timestamps in results and display in ISO-8601 format
    - Ability to specify status codes to ignore per-API
- New sites
    - DNSDB - FarSight Security Passive DNS Data base (premium)

### Version 1.1.2 (2015-11-26) ###

- New sites
    - Telize (premium) - GeoIP site (premium)
    - Freegeoip - GeoIP site (free)
    - CIF - CIFv2 API support, from csirtgadgets.org
- New features
    - Ability to specify labels for single-line multimatch JSON outputs
    - Ability to specify relative time parameters using relatime library

### Version 1.0.1 (2015-10-13) ###

- Fixed a false-positive bug with Spamhaus (Github#10)

### Version 1.0.0 (2015-07-02) ###

- Initial release


License Info
------------

The MIT License (MIT)

Copyright (c) 2015 Hurricane Labs LLC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.


[1]: https://github.com/1aN0rmus/TekDefense-Automater
[2]: https://github.com/HurricaneLabs/machinae/raw/master/machinae.yml
