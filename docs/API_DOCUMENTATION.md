# Application Service Reference

This is a local desktop application, not a network API. Its supported integration surface is Python application services plus the `nlve_cli.py` operator command.

## Runtime Configuration

`config.runtime.RuntimeSettings.from_environment()` validates external feature flags and bounded limits. Defaults disable live search, live send, and Google Drive.

## Outreach Ledger

`services.outreach_ledger.OutreachLedger` owns the operating lifecycle:

- `check_campaign_readiness(campaign_id)`
- `create_message_drafts(campaign_id, volunteer_ids=None)`
- `approve_message(draft_id, reason, actor)`
- `send_approved_drafts(scraper, draft_ids)`
- `confirm_manual_send(draft_id, delivery_evidence, actor)`
- `record_response(...)`
- `approve_follow_up(...)` and `confirm_follow_up_sent(...)`
- `record_outreach_outcome(...)`
- `export_volunteer_data(...)`

External sending must go through this service. Direct and legacy send paths raise `RuntimeError`.

## Database

`database.database_manager.DatabaseManager` initializes additive schema version 3, enables SQLite foreign keys and busy timeouts, exposes integrity diagnostics, atomically claims approved drafts, and reconciles stale attempts without guessing provider outcomes.

## Provider Adapters

`services.enhanced_scraper.EnhancedScraper` performs bounded same-origin HTTPS requests with a transparent user agent and conservative delay. The controller feature gate must be enabled before it is used live.

`google_drive.google_api_services.GoogleDriveManager` is side-effect free on construction. Call `connect(interactive=True)` only from an explicit operator action, then upload a verified backup. Scope is `drive.file`.

## Operator CLI

```text
python run.py doctor
python run.py smoke
python run.py reconcile-sends --minutes 15
python run.py import-volunteers PATH
python run.py export-volunteers PATH --format json|csv
python run.py backup --name NAME
python run.py support-bundle PATH
```

All CLI commands except explicitly configured provider actions are local. The smoke command never uses the network or real credentials.
