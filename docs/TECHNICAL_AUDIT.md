# Technical Audit

## Scope and Baseline

The audit covered every tracked source file, dependency manifest, workflow, entry point, storage boundary, provider adapter, operator action, test, and historical Git object. The implementation baseline was `7f2da80` on `main`.

## Critical Findings and Disposition

| Severity | Finding | Disposition |
| --- | --- | --- |
| Critical | Google OAuth client material and a refresh token were committed in the root and packaged `dist/` tree. | Removed from the active tree; history rewrite and owner-side revocation/rotation are release gates. |
| Critical | Legacy services claimed hidden/full-platform access and exposed autonomous send/sync paths. | Replaced by fail-closed compatibility shims; no maintained entry point invokes them. |
| High | Approved messages had no complete operator workflow and send claims were race-prone. | Added review, bounded live send, manual evidence, atomic send claims, daily/action caps, and ambiguous-send reconciliation. |
| High | Drive construction authenticated and created remote objects. | Rebuilt as side-effect-free construction with explicit opt-in, `drive.file`, and explicit upload. |
| High | Credential encryption could use a predictable fallback. | Removed fallback; use an explicit master password or OS keyring. |
| High | Backup metadata leaked local paths and restore could destroy current data after rollback-backup failure. | Redacted metadata and added verified pre-restore backup, staging, rollback, traversal/symlink/expansion checks. |
| Medium | Candidate search called a missing method and used excessive page defaults. | Added same-origin bounded search and conservative rate limits. |
| Medium | UI status and metrics could imply provider readiness. | Replaced with runtime, provider, database, and safety-stop state. |
| Medium | Packaged binaries and runtime data were tracked. | Removed `dist/`; repository safety checks reject build/runtime/secret paths. |
| Medium | No reproducible network-free end-to-end verification existed. | Added `nlve smoke`, diagnostics, support bundle, tests, and CI gates. |

## Maintained Architecture

- `main.py`: desktop orchestration and explicit provider actions.
- `views/modern_ui.py`: operator views and confirmations.
- `database/database_manager.py`: SQLite schema, state transitions, audit ledger, migrations, and health.
- `services/outreach_ledger.py`: campaign, draft, send, response, follow-up, outcome, and privacy workflow.
- `services/enhanced_scraper.py`: bounded same-origin live provider adapter, disabled by default.
- `google_drive/google_api_services.py`: explicitly connected app-scoped backup adapter.
- `nlve_cli.py` and `services/diagnostics.py`: diagnostics, smoke test, reconciliation, portability, backup, and privacy-safe support bundle.

## Residual Risk

No source change can revoke the historical Google credentials, establish current NLvoorelkaar permission, validate selectors against the live site, issue a signing certificate, or replace manual accessibility/provider acceptance. These are listed as blocked release gates, not completed work.

