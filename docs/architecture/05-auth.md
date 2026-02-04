# Google Auth: Service Accounts and OAuth (Dev)

This doc is the single source of truth for authentication in the GW Engine.

Goals (T4):
- Service Account auth works for Drive/Sheets.
- OAuth dev flow is documented and works for Gmail.
- Errors for missing creds/scopes are obvious and actionable.
- Secrets are never committed.

---

## Auth options

### Option A: Service Account (Drive/Sheets automation)
Use a Google Service Account for server-style automation.

Key points:
- Service Accounts are separate identities (not “you”).
- To access a specific Drive file / Sheet owned by you, you must **share it** with the service account email.
- Keep the service account JSON private; never commit it.

Env:
- `GOOGLE_SERVICE_ACCOUNT_JSON=/absolute/path/to/service_account.json`

#### Important scope note (this matters)
- For OAuth user apps, `drive.file` is a good least-privilege default.
- For Service Accounts, `drive.file` is often too restrictive for shared files and can behave like “not found”.
  In T4 we switched the SA to use full Drive scope so it can access shared items:
  - SA Drive scope: `https://www.googleapis.com/auth/drive`

---

### Option B: OAuth user credentials (developer flow / Gmail access)
Use OAuth for developer flows where the user must consent, especially Gmail.

Required env vars:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`

Gmail uses OAuth even if Service Account is configured (Drive/Sheets can still use SA).

---

## Scopes (recommended)
- Drive (OAuth user default): `https://www.googleapis.com/auth/drive.file`
- Drive (Service Account for shared file access): `https://www.googleapis.com/auth/drive`
- Sheets: `https://www.googleapis.com/auth/spreadsheets`
- Gmail (dev test): `https://www.googleapis.com/auth/gmail.readonly`

---

## Client factory uses scopes automatically

Scopes are centralized in `gw_engine.clients.scopes_for_api(...)`. You don't need to worry about scope selection in workflows.

Key design points:
- **Drive/Sheets** can use either Service Account or OAuth (determined by config)
- **Gmail** remains OAuth-only for now (until domain-wide delegation is added in a future iteration)
- The factory automatically applies the correct scopes for each API + auth method

**Distinction**: Auth is about **credentials** (who you are). The Client Factory is what **builds API clients consistently** with those credentials and the right configuration (scopes, timeouts, retries).

---

## Dev prerequisites (what to set up once)

### Service Account + quota-safe test sheet
Some service accounts can’t create new Drive files due to storage quota limits.
To avoid flaky “create file” tests, we use an existing spreadsheet you own and share to the SA.

1) Get the service account email:
```bash
python -c "import json;print(json.load(open('/absolute/path/to/service_account.json'))['client_email'])"
