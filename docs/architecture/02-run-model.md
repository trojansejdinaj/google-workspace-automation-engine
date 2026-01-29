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
