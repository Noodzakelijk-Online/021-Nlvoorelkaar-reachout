# Changelog

All notable changes to this project are documented here.

## 3.1.0 - 2026-08-09

- Added an authenticated React web operator interface backed by the same application service and SQLite ledger as the desktop GUI.
- Added verified loopback and ngrok launch paths plus a privacy-minimized, read-only HAI Generic JSON Feed.
- Added a private written-provider-approval gate for every live NLvoorelkaar login, search, and send action.
- Made Safety Stop durable across desktop, web, CLI, and process restarts.
- Added database pagination and indexes, fixed local-midnight send accounting, and validated 10,000-record query performance.
- Added reproducible wheel/source builds, two Windows executables, an SBOM/checksum release archive, and a provenance-enabled Windows workflow.
- Removed unused Selenium, Matplotlib, and pandas runtime dependencies to reduce install time, attack surface, memory, and release size.
- Added browser/API workflow coverage, frontend audit/build gates, and release-only packaging fixes.

## 3.0.0 - 2026-08-08

- Added a review-gated outreach operating ledger and operator-facing workflow views.
- Added fail-safe external-provider feature flags, emergency stop controls, and recovery commands.
- Added candidate import, local critical-path verification, database diagnostics, and privacy-safe support bundles.
- Made Google Drive authorization and remote mutations explicitly user initiated.
- Removed committed OAuth material and generated packaged builds from the active source tree.
- Added repository secret/runtime-data checks and expanded CI security gates.
- Updated cryptography, aiohttp, and Pillow to releases fixing the August 2026 advisory set.
- Replaced insecure test temporary-file creation and regex-based HTML sanitization identified by CodeQL.

## 2.0.0

- Historical enhanced desktop implementation. This release predates the current safety and verification baseline.
