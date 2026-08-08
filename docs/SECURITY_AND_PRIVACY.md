# Security and Privacy Design

## Assets and Trust Boundaries

Protected assets include provider credentials, OAuth tokens, volunteer identifiers/profile text, message bodies, responses, delivery evidence, exports, backups, and audit events. Trust boundaries exist between the desktop operator and local files, the application and NLvoorelkaar, the application and Google Drive, and any recipient of a support bundle/export.

## Threats and Controls

| Threat | Control |
| --- | --- |
| Credential disclosure | Ignored private paths, OS keyring/explicit master password, repository/history scanner, no secret logging. |
| Unauthorized external action | Provider flags off by default, explicit login/action, review gates, exact-snapshot approval, safety stop. |
| Duplicate or ambiguous send | Atomic claim, unique state transition, durable attempt, no automatic retry, reconciliation state. |
| Excess provider use | Same-origin requests, bounded pages, delays, batch and daily caps. |
| Backup archive attack | Traversal/symlink/size/ratio checks, staging, verified rollback backup. |
| Personal-data oversharing | Local-first storage, explicit export, privacy review, redaction, filtered backups, aggregate support bundles. |
| False readiness | Diagnostics distinguish local, database, credentials, provider opt-in, and provider connection. |
| Supply-chain compromise | Exact dependency pins, pip-audit, Dependabot, CodeQL, minimal GitHub token permissions. |

## Privacy Impact

Purpose is operator-reviewed volunteer outreach. Data minimization requires importing only fields needed to assess and contact candidates. Runtime data is local by default. Google Drive transfer is optional and limited to app-created backup files. Retention proposals do not delete automatically. Export, archive, redaction, and deletion require explicit action and audit evidence.

Data subjects may be represented by provider ID, profile URL/text, location, skills, availability, messages, responses, and outcomes. Operators must follow provider terms and applicable privacy law, document their lawful basis, answer access/deletion requests, and avoid collecting sensitive data not needed for outreach.

## Historical Exposure

Previously committed Google material must be treated as compromised even after Git history is rewritten. Owner-side revocation, rotation, and activity review remain mandatory.

