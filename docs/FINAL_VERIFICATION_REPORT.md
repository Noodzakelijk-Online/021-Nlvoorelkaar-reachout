# Final Verification Report

## Scope

- Branch: `main`
- Starting commit for 3.1 work: `9a2385c`
- Previous history-clean hardening commit: `9a2385c`
- Final delivery commit: the commit containing this report
- Supported Python: 3.10, 3.11, 3.12
- Deployment: local Windows desktop/operator application with optional loopback-to-ngrok HTTPS access

## Implemented Surfaces

Fail-closed runtime configuration and written-provider-approval validation; reviewed candidate intake; campaign/draft lifecycle; exact-snapshot approval; assisted and bounded live delivery; atomic claims; response/follow-up/outcome tracking; privacy/export; verified backup/restore; explicit app-scoped Drive upload; desktop and authenticated React web interfaces; loopback/ngrok launcher; read-only HAI feed; diagnostics; durable safety stop; reconciliation; support bundle; schema v4 migrations/health; CI, release, and security gates.

## Verification Results

The 3.1 working tree was validated locally; CI repeats the clean-checkout matrix on Python 3.10-3.12. Results before push:

- Repository safety, including all reachable history: passed.
- Compilation: passed.
- Full source suite: 116 passed on the machine Python in 99.15 seconds.
- Authenticated API workflow suite: 7 passed on managed Python 3.11.15.
- Local critical path: passed; no network used, no external message sent, export count 1, backup verified, database ready.
- `pip check`: no broken requirements.
- Runtime dependency audit: no known vulnerabilities.
- Development dependency audit: no known vulnerabilities.
- Frontend typecheck/production build: passed; 216.99 kB JavaScript (67.32 kB gzip), 8.06 kB CSS; npm reported zero vulnerabilities.
- Browser acceptance: login, dashboard, navigation, and durable Safety Stop activate/clear passed in Chrome at 1440x1000 and 390x844 with zero console errors.
- Python source archive and wheel: clean isolated builds passed and include compiled web assets.
- Standalone operator: PyInstaller bundle completed and its packaged network-free smoke test passed.
- SBOM: reproducible CycloneDX runtime document generated successfully.
- Desktop construction smoke: `MainApplication` rendered the dashboard with all 15 navigation items; logical 1200x840 window rendered at 1800x1260 under local 150% scaling.
- Startup guard: the launcher rejected the unsupported machine-default Python 3.14 as designed.
- CodeQL remediation: all insecure `mktemp` calls were replaced with `mkstemp` plus cleanup, and regex HTML stripping was replaced with structured parsing plus active-content regression coverage.
- GitHub security state: zero open Dependabot alerts and zero open CodeQL alerts; secret scanning, push protection, and Dependabot security updates enabled.

Commands:

```powershell
python scripts/check_repository_safety.py --history
python -m compileall -q .
python -m pytest -q -p no:cacheprovider
python run.py smoke
python run.py doctor
python -m pip check
python -m pip_audit -r requirements.txt
python -m pip_audit -r requirements-dev.txt
python -m pip_audit -r requirements-build.txt
cd web; npm.cmd ci; npm.cmd run build; npm.cmd audit --audit-level=high
```

CI additionally runs Python 3.10-3.12, the frontend build/audit, CodeQL, and a Python 3.12 Windows release workflow. A fresh clone must pass safety, compile, tests, smoke, and dependency checks without credentials or existing runtime data.

## Credentials and Runtime Data

Active and reachable history contains no committed OAuth files, token files, runtime databases/logs/backups, or packaged `dist/` tree. The rewrite removed root, packaged, `google_drive/`, and `google-drive/` credential/token paths. The removed historical Google OAuth client and refresh token remain compromised until the owner revokes/rotates them; history rewriting is not revocation.

GitHub retains 21 open secret alerts whose locations all resolve to pre-rewrite commits and are not ancestors of `main`. They are intentionally not dismissed: the underlying credentials were real, and only owner-side revocation/rotation can close the incident truthfully.

## Blocked External Evidence

- Written NLvoorelkaar approval, account permission, selectors, login, send confirmation, and rate acceptance. The code validates a current private approval record and keeps live actions disabled without it.
- Google OAuth authorization, upload, readback, and restore using newly rotated private credentials.
- Manual Windows screen-reader, high-DPI, and non-technical operator acceptance.
- Signed clean-machine Windows distribution, if a binary release is required.
- Public ngrok acceptance was not completed because the account's single endpoint was already active in another process (`ERR_NGROK_334`). The launcher failed closed and removed only the processes it created.

No mock, isolated smoke test, or local diagnostic is treated as evidence for those external conditions.
