# NLvoorelkaar Reachout

Local-first desktop tooling for review-gated volunteer outreach. The maintained workflow is candidate intake, local campaign preparation, message review, assisted or explicitly enabled delivery, response tracking, follow-ups, privacy review, and verified backup/export.

The application does not claim access to private profiles, does not send unapproved messages, and does not enable live provider mutations by default.

## Supported Runtime

- Python 3.10, 3.11, or 3.12
- Windows desktop for the supported GUI path
- An NLvoorelkaar account only for explicitly enabled live search/send
- Optional Google OAuth desktop credentials only for explicitly enabled Drive backup

## Install and Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run.py
```

The launcher never installs packages automatically. It reports missing dependencies and exits.

Run local diagnostics and the network-free critical-path verification:

```powershell
python run.py doctor
python run.py smoke
```

## Safe Defaults

All external provider features fail closed. Opt in only after reviewing current platform terms and the operator runbook.

```powershell
$env:NLVE_ENV = "production"
$env:NLVE_LIVE_SEARCH_ENABLED = "0"
$env:NLVE_LIVE_SEND_ENABLED = "0"
$env:NLVE_GOOGLE_DRIVE_ENABLED = "0"
$env:NLVE_MAX_SEARCH_PAGES = "5"
$env:NLVE_MAX_SEND_BATCH = "5"
$env:NLVE_DAILY_SEND_LIMIT = "20"
```

`NLVE_ENV=test` rejects every external-provider flag. Candidate CSV/JSON import, local message review, manual-send evidence, response tracking, exports, and local backups work without provider automation.

## Critical Path

1. Open **Candidate Intake** and import reviewed CSV/JSON data, or explicitly enable bounded live search.
2. Create a campaign with a target and message template.
3. Assess matches and create personalized drafts.
4. Review/edit each draft and approve its exact snapshot.
5. Copy and send manually, then record evidence, or explicitly enable a bounded live send.
6. Record responses, approve follow-ups, and record outcomes.
7. Review privacy retention proposals and export or redact data as needed.
8. Create a verified local backup; optionally upload it to app-scoped Google Drive storage.

Live send actions are capped per action and per day. The emergency **Safety Stop** blocks new provider actions and requests cancellation of active work. A stale in-flight send is marked `external_outcome_unknown`; the operator must inspect provider history before re-approval.

## Candidate Import

CSV and JSON imports accept `volunteer_id` (or legacy `profile_id`) plus optional fields such as `name`, `location`, `description`, `skills`, `categories`, `availability`, `contact_info`, and `profile_url`.

```powershell
python run.py import-volunteers C:\private\reviewed-candidates.csv
```

Imports are local, audited, idempotent by volunteer ID, and do not contact NLvoorelkaar.

## Google Drive

Drive support uses the `drive.file` scope. Creating `GoogleDriveManager` has no auth, browser, refresh, or remote-write side effects. An explicit operator action connects and uploads one verified backup.

```powershell
$env:NLVE_GOOGLE_DRIVE_ENABLED = "1"
$env:NLVE_GOOGLE_CLIENT_SECRET_PATH = "C:\private\google_credentials.json"
$env:NLVE_GOOGLE_TOKEN_PATH = "C:\private\google_token.json"
```

Do not reuse the OAuth credentials that were historically committed. They are compromised and must be revoked/rotated in Google Cloud.

## Data and Privacy

Runtime data belongs under ignored `data/`, `logs/`, and `backups/` paths. Local databases can contain volunteer identifiers, profiles, message bodies, responses, and audit evidence. Backups exclude credential/token/session-like files. Support bundles exclude logs, credentials, message bodies, and volunteer records.

```powershell
python run.py export-volunteers C:\private\volunteers.json --format json
python run.py backup --name before-maintenance
python run.py support-bundle C:\private\nlve-support.zip
```

## Development Checks

```powershell
python -m pip install -r requirements-dev.txt
python scripts\check_repository_safety.py
python -m compileall -q .
python -m pytest -q
python nlve_cli.py smoke
python -m pip_audit -r requirements.txt
python -m pip_audit -r requirements-dev.txt
```

CI runs the test suite on Python 3.10-3.12, scans reachable Git history for forbidden secret/runtime paths, runs the local critical path, audits dependencies, and runs CodeQL.

## Current External Blockers

- The historically exposed Google OAuth client and refresh token require owner-side revocation/rotation.
- Current NLvoorelkaar terms, selectors, account permissions, and live send confirmation semantics require owner/operator validation before enabling live flags.
- A real Google Drive authorization and upload/download acceptance test requires private OAuth credentials.
- No release-signing certificate or clean-machine Windows acceptance evidence is available yet.

See [docs/OPERATOR_RUNBOOK.md](docs/OPERATOR_RUNBOOK.md), [docs/CRITICAL_PATH.md](docs/CRITICAL_PATH.md), and [docs/FINAL_VERIFICATION_REPORT.md](docs/FINAL_VERIFICATION_REPORT.md).
