# Run model

The run model is the backbone of observability: it lets you answer:
- What ran?
- When did it run?
- Which step failed?
- Where are the artifacts?

This model can live in a lightweight DB or even as files, but the schema stays stable.

## Entities
### RUNS
One row per engine execution.
- workflow_name, status, started/ended timestamps
- config_hash + git_sha (reproducibility)

### RUN_STEPS
One row per step execution within a run.
- step_name, status, duration
- error_code + error_message
- metrics_json for step outputs (counts, ids, etc.)

### ARTIFACTS
One row per artifact produced by a run.
- path, type, checksum

## Diagram
```mermaid
erDiagram
  RUNS ||--o{ RUN_STEPS : contains
  RUNS ||--o{ ARTIFACTS : produces

  RUNS {
    string run_id PK
    string workflow_name
    string status
    datetime started_at
    datetime ended_at
    int duration_ms
    string config_hash
    string git_sha
  }

  RUN_STEPS {
    string run_id FK
    int step_index
    string step_name
    string status
    datetime started_at
    datetime ended_at
    int duration_ms
    string error_code
    string error_message
    string metrics_json
  }

  ARTIFACTS {
    string run_id FK
    string type
    string path
    string checksum
    datetime created_at
  }
