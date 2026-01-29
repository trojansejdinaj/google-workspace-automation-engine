flowchart TB
  subgraph Core["Engine Core"]
    ENG[Engine Runtime]
    WF[Workflow Interface\nname(), steps(), validate()]
    ST[Step Interface\nrun(ctx)->ctx]
    CTX[Run Context\n(run_id + data + metrics)]
    LOG[Logger + run_id]
    RET[Retry/Backoff Policy]
    AUD[Audit Exporter]
    STORE[Run Store]
  end

  subgraph Adapters["Google Workspace Adapters"]
    GMAIL[Gmail Adapter]
    DRIVE[Drive Adapter]
    SHEETS[Sheets Adapter]
    FACT[Client Factory]
    AUTH[Auth Manager]
  end

  subgraph Workflows["Workflows (Plugins)"]
    W1[SheetsWorkflow]
    W2[GmailWorkflow]
    W3[DriveWorkflow]
  end

  ENG --> WF
  WF --> ST
  ST --> CTX
  ENG --> LOG
  ENG --> RET
  ENG --> STORE
  ENG --> AUD

  W1 --> SHEETS
  W2 --> GMAIL
  W3 --> DRIVE

  SHEETS --> FACT
  GMAIL --> FACT
  DRIVE --> FACT
  FACT --> AUTH
