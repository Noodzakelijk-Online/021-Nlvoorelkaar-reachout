# Audit Remediation Tracker

This file tracks repository-level remediation work after the security and quality audit.

## Completed

- Removed committed runtime secrets from the working tree.
- Removed committed packaged build output from `dist/`.
- Added ignore rules for local credentials, tokens, encrypted credential files, databases, logs, backups, and packaged builds.
- Moved Google Drive OAuth defaults to ignored `data/` paths and added environment-variable overrides.
- Reduced Google Drive OAuth scope to `drive.file`.
- Added missing Google API dependencies to `requirements.txt`.
- Added development/test dependencies in `requirements-dev.txt`.
- Added CI for compile checks, unit tests, and dependency auditing.
- Fixed service/test API mismatches in queueing, credential storage, blacklist, volunteer, messaging, error handling, logging, and session retry helpers.
- Parameterized database cleanup date filtering.
- Closed SQLite connections deterministically in service/database code.
- Replaced misleading generated documentation with current setup and security guidance.

## Still Required Before Publishing

- Revoke and rotate the previously committed Google OAuth client secret and refresh token.
- Rewrite Git history to purge committed secrets and `dist/` artifacts from all prior commits.
- Force-push the rewritten history only after coordinating with every collaborator.
- Re-run CI on Python 3.10, 3.11, and 3.12 in GitHub Actions.

## Future Improvements

- Consolidate duplicate application entry points.
- Add integration tests around the main UI flows and Google Drive backup path.
- Add static analysis and formatting checks once the team agrees on tools.
- Review live scraping behavior against the current NLvoorelkaar terms and website behavior before production use.
