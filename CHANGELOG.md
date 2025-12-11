# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.5.0] – 2025-02-XX
### Added
- **Concurrent site lookups** using a new `-w/--workers` command-line option.  
  - Allows multiple OSINT providers to be queried in parallel.  
  - Defaults to an auto-detected worker count when unspecified.
- **Thread-safe per-site timeouts** powered by `stopit.ThreadingTimeout`.
  - Replaces the legacy `SignalTimeout` mechanism that caused threading failures.
  - Prevents runaway or non-responsive providers from blocking full result sets.

### Changed
- Refactored internal site-lookup loop to support concurrency and timeout safety.
- Updated README with full details of modernization changes and new CLI options.
- Improved reliability of error handling during concurrent fetches.

### Deprecated / Disabled
The following legacy OSINT providers were marked **disabled by default** due to shutdowns, nonfunctional APIs, SSL issues, or permanent 403 responses:

- `malc0de` – invalid SSL certificate, abandoned service  
- `reputation_authority` – unavailable/unreliable  
- `threatcrowd_ip_report` – hostname/cert mismatch  
- `fortinet_classify` – HTML-only endpoint returns 403; unusable  
- `AbuseIPDB` (legacy scraping mode) – requires modern API key integration  
- `vt_ip` (VirusTotal pDNS v2) – API deprecated  

These may be re-enabled manually in user configs but are no longer recommended.

### Fixed
- Eliminated `signal only works in main thread of the main interpreter` errors during site queries.
- Removed blocking behavior when one or more providers fail or timeout.
- Improved result stability when multiple services fail simultaneously.

### Notes for Developers
- Existing YAML-based configs remain fully compatible.
- Internal site handlers may now need awareness of concurrent execution depending on future extensions.
- This release lays the groundwork for future modern OSINT integrations (ip-api, URLHaus, OTX, etc.).
- Concurrency architecture is intentionally conservative to minimize breaking changes.

---

## [1.4.9] – 2020-11-25
_(previous version retained unchanged for historical accuracy)_
