# Golden path sequence

The “golden path” is the most important demo flow: one command, deterministic behavior, clear outputs.

Goal: you can run this end-to-end and it produces:
- run_id
- status + duration
- artifacts under `runs/<run_id>/`

## Golden path steps
1) User runs `gw demo` (or `gw run <workflow>`).
   Example: `uv run gw run sheets_cleanup_reporting --config workflows/sheets_cleanup_reporting/config.example.yml`
2) CLI loads config + validates.
3) Auth manager builds credentials:
   - SA for Drive/Sheets
   - OAuth user for Gmail dev
4) Client factory builds API clients.
5) Engine starts a run → creates `run_id`.
6) Engine executes workflow steps 1..N.
7) Engine persists step status + durations.
8) Engine writes logs + audit + artifacts index.
9) CLI prints a final summary banner.

## Diagram
```mermaid
sequenceDiagram
  autonumber
  actor User
  participant CLI as gw CLI
  participant CFG as Config Loader
  participant AUTH as Auth Manager
  participant FACT as Client Factory
  participant ENG as Engine
  participant WS as Workflow (Sheets/Gmail/Drive)
  participant RUNS as Run Store
  participant AUD as Audit Exporter
  participant ART as Artifacts (runs/<run_id>/)

  User->>CLI: gw demo (or gw run <workflow>)
  CLI->>CFG: load config + validate
  CLI->>AUTH: build credentials (SA/OAuth)
  AUTH->>FACT: init clients (scopes + retries)
  CLI->>ENG: start run(workflow, config)
  ENG->>RUNS: create run_id + run row
  ENG->>WS: execute steps (1..N)
  WS-->>ENG: step outputs + metrics
  ENG->>RUNS: persist step status + durations
  ENG->>AUD: generate audit (CSV/JSON)
  AUD->>ART: write audit file(s)
  ENG->>ART: write logs.jsonl + artifacts index
  ENG-->>CLI: run summary (run_id, status, duration, steps ok/failed)
  CLI-->>User: print end banner + where artifacts live
