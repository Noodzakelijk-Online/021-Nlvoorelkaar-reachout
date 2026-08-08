# Application Interface Audit

This repository exposes no HTTP backend. `docs/API_DOCUMENTATION.md` records the supported local Python/CLI boundary.

Provider calls are reachable only through:

- `EnhancedScraper`: explicit login, same-origin bounded search, and reviewed send.
- `GoogleDriveManager`: explicit connect and app-scoped upload/download.

The maintained UI does not invoke campaign, sync, reporting, volunteer-data, performance-network, or scheduler compatibility send/sync paths. Those paths raise instead of returning synthetic success.

Every state-changing outreach action routes through `OutreachLedger` and `DatabaseManager`, which own validation, state transitions, atomic claims, and audit events. Direct SQL is confined to repository services and diagnostics.

