# GW Engine — System overview

The Google Workspace Automation Engine (GW Engine) is a small runtime that executes “workflows” (plugins)
against Google Workspace APIs (Gmail/Drive/Sheets), while producing run tracking, structured logs, and
audit artifacts.

This doc is the high-level map: what runs where, and what it connects to.

## Core concepts
- **CLI** (`gw`) triggers a run (demo or a specific workflow).
- **Config Loader** reads config + env and validates required settings.
- **Auth Manager** chooses credentials for a given API:
  - Service Account (SA) for Drive/Sheets automation
  - OAuth user creds for Gmail dev
- **Client Factory** (`gw_engine.clients`) builds Google API clients with correct scopes and retry/backoff.
  - Central builder for Drive/Sheets/Gmail clients with consistent configuration
  - Reliability defaults: timeout + retries/backoff/jitter (configurable via env vars)
  - Rate-limit handling: retries on 429, 5xx, and rate-limit-style 403 reasons
- **Engine Runtime** executes steps and persists run state.
- **Run Store + Artifacts** write a run record and files under `runs/<run_id>/`.

## Outputs you should always get
- A **run_id** printed at the end of every run.
- `runs/<run_id>/logs.jsonl` with structured JSONL.
- Audit exports (CSV/JSON) and a simple artifacts index for debugging + proof.

## Diagram
```mermaid
flowchart LR
  U[User] --> CLI[CLI: gw]

  CLI --> CFG[Config Loader\n(env + yaml/json)]
  CLI --> AUTH[Auth Manager\nSA + OAuth]
  AUTH --> FACT[Client Factory\nGmail/Drive/Sheets]
  CFG --> ENG[Engine Runtime\nWorkflow + Step execution]
  FACT --> ENG

  ENG --> GMAIL[Gmail API]
  ENG --> DRIVE[Drive API]
  ENG --> SHEETS[Sheets API]

  ENG --> RUNS[Run Store]
  ENG --> ART[Artifacts Folder\nruns/<run_id>/]
  RUNS --> AUD[Audit Exporter\nCSV/JSON]
  ENG --> LOGS[Structured Logs\nJSONL]

  AUD --> ART
  LOGS --> ART
