# Application Interface Audit

The authenticated `/api/v1` HTTP boundary, desktop UI, CLI, and HAI adapter all call `ApplicationService`. `docs/API_DOCUMENTATION.md` records the routes, authentication, bounds, and error contract.

Provider calls are reachable only through:

- `EnhancedScraper`: explicit login, same-origin bounded search, and reviewed send.
- `GoogleDriveManager`: explicit connect and app-scoped upload/download.

The maintained UI does not invoke campaign, sync, reporting, volunteer-data, performance-network, or scheduler compatibility send/sync paths. Those paths raise instead of returning synthetic success.

Every state-changing outreach action routes through `ApplicationService`, `OutreachLedger`, and `DatabaseManager`, which own validation, state transitions, atomic claims, and audit events. The web route module contains no direct SQL or provider calls. Direct SQL is confined to repository services and diagnostics.

The HAI feed is read-only and privacy-minimized. It exposes stable review references but no volunteer names, contact details, message bodies, credentials, approval authority, or send authority.
