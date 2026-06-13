# Known limitations

This file records limitations supported by current code, tests, runbooks, or tracked evidence.

## Engine

- Generated run directories under `runs/<run_id>/` are operational artifacts and are ignored by git. Curated proof belongs under `runs/_evidence/`.
- The deterministic `uv run gw demo` path is local and does not prove live Google API access.

## Authentication

- Live Gmail execution requires OAuth credentials with Gmail permissions. Service-account auth is used for Drive/Sheets-style automation, not Gmail user mailbox access.
- Local credential values must stay in `.env` or ignored `config.local.yml` files.
- Target Sheets and Drive resources must be shared with the active credential identity.

## Sheets workflow

- Integration behavior depends on a real spreadsheet ID and write permission.
- Normal local/CI tests deselect integration tests; they do not prove access to a live Sheet.

## Gmail workflow

- Live Gmail search, label creation, label application, archiving, attachment download, and alert count behavior depend on OAuth scope and mailbox permissions.
- Fixture-backed tests validate parsing/actions/attachments/alerts without calling live Gmail.

## Drive workflow

- `drive_intake_validator` has configuration and demo scaffolding, but its README is empty in the current repository. Verify implementation status before using it for live Drive validation work.

## Testing and integration coverage

- `uv run pytest` passes the normal test suite with integration tests deselected.
- Integration tests require real Google credentials and resources supplied through local environment variables.

## Operational deployment

- No deployment packaging or scheduler is documented in this repository yet. Runs are started locally through CLI commands and workflow demo scripts.
