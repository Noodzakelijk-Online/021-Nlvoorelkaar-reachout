# Web API Reference

The FastAPI transport in `web_api/app.py` exposes the shared `ApplicationService` used by the operator web UI. It does not bypass review, Safety Stop, retention, or audit rules.

## Authentication and Errors

Set `NLVE_WEB_API_TOKEN` to a private random value of at least 32 characters. Every `/api/v1/*` request requires `Authorization: Bearer <token>`. `/healthz` is the only unauthenticated route. Interactive API documentation and the OpenAPI route are disabled.

Validation errors use HTTP 422. Invalid operations use 400, blocked state transitions use 409, oversized imports use 413, and request limits use 429. Application errors use:

```json
{"error":{"code":"operation_blocked","message":"Safety stop is active"}}
```

## Read Routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/healthz` | Minimal tunnel/process health check |
| GET | `/api/v1/status` | Runtime, database, provider authorization, HAI, and Safety Stop state |
| GET | `/api/v1/dashboard` | Bounded operating summaries and recent queues |
| GET | `/api/v1/volunteers?limit=100&offset=0` | Paginated candidate records |
| GET | `/api/v1/campaigns` | Campaign list |
| GET | `/api/v1/messages/review` | Drafts requiring review |
| GET | `/api/v1/messages?message_status=approved` | Drafts in one validated state |
| GET | `/api/v1/responses` | Recorded response inbox |
| GET | `/api/v1/follow-ups` | Follow-up queue |
| GET | `/api/v1/privacy/retention?days=365` | Stale-record review candidates |
| GET | `/api/v1/hai/feed` | Privacy-minimized, read-only HAI feed |

List routes enforce bounded limits of at most 500 records. Candidate import accepts reviewed CSV or JSON files up to 5 MiB.

## Mutation Routes

| Method | Route | Required body or evidence |
|---|---|---|
| POST | `/api/v1/volunteers/import` | Multipart `file` containing CSV or JSON |
| POST | `/api/v1/campaigns` | Campaign fields and message template |
| POST | `/api/v1/campaigns/{id}/drafts` | Optional bounded `volunteer_ids` list |
| POST | `/api/v1/messages/{id}/approve` | Non-empty review `reason` |
| POST | `/api/v1/messages/{id}/reject` | Non-empty review `reason` |
| POST | `/api/v1/messages/{id}/confirm-manual-send` | Operator-observed delivery `evidence` |
| POST | `/api/v1/responses` | Volunteer ID, campaign ID, and response content |
| POST | `/api/v1/follow-ups/{id}/approve` | Uses the persisted suggested message snapshot |
| POST | `/api/v1/follow-ups/{id}/confirm-manual-send` | Operator-observed delivery `evidence` |
| POST | `/api/v1/privacy/retention/{id}/archive` | Explicit decision `reason` |
| POST | `/api/v1/privacy/retention/{id}/redact` | Explicit decision `reason` |
| PUT | `/api/v1/operations/safety-stop` | `{"active": true}` or `false` |

The API cannot claim a provider send from inference. Manual send and follow-up completion require operator-entered evidence and are blocked while durable Safety Stop is active.

## Service and Database

`services.application_service.ApplicationService` is the transport-independent boundary. `services.outreach_ledger.OutreachLedger` owns approvals, send attempts, responses, follow-ups, privacy actions, and HAI projection. `DatabaseManager` initializes additive schema version 4, uses SQLite foreign keys and busy timeouts, and performs bounded pagination in SQL.

All external provider actions must pass `RuntimeSettings.require_provider_action`. A live action remains disabled unless both its feature flag and a valid private written-approval record authorize that exact action.
