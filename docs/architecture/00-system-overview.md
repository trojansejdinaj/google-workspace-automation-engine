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
