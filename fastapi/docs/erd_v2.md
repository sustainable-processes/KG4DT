### ERD — v2 relational schema (PostgreSQL)

This ERD reflects the finalized design, including `reactors.chemistry` and `reactors.kinetics` JSONB columns and the many‑to‑many `reactor_basic_junction`.

```mermaid
erDiagram
  USERS ||--o{ PROJECTS : has
  PROJECTS ||--o{ EXPERIMENT_DATA : has
  PROJECTS ||--o{ MODELS : has
  REACTORS }o--o{ BASICS : uses via REACTOR_BASIC_JUNCTION
  CATEGORIES ||--o{ TEMPLATES : groups
  REACTORS ||--o{ TEMPLATES : templated_by

  USERS {
    bigint id PK
    citext username "UNIQUE"
    citext email "UNIQUE"
    timestamptz created_at
    timestamptz updated_at
  }

  PROJECTS {
    bigint id PK
    bigint user_id FK
    varchar name
    jsonb content
    timestamptz created_at
    timestamptz updated_at
    "UNIQUE(user_id, lower(name))"
  }

  EXPERIMENT_DATA {
    bigint id PK
    bigint project_id FK
    jsonb data
    timestamptz created_at
    timestamptz updated_at
  }

  MODELS {
    bigint id PK
    bigint project_id FK
    varchar name
    text[] mt
    text[] me
    jsonb laws
    timestamptz created_at
    timestamptz updated_at
  }

  REACTORS {
    bigint id PK
    varchar name
    integer number_of_input
    integer number_of_output
    timestamptz created_at
    timestamptz updated_at
    varchar icon_url
    jsonb json_data
    jsonb chemistry
    jsonb kinetics
  }

  BASICS {
    bigint id PK
    varchar name
    enum type "steam|solid|gas"
    enum usage "inlet|outlet|utilities"
    varchar structure
    varchar phase
    varchar operation
    timestamptz created_at
    timestamptz updated_at
  }

  REACTOR_BASIC_JUNCTION {
    bigint reactor_id FK, PK
    bigint basic_id FK, PK
    timestamptz association_at
  }

  CATEGORIES {
    bigint id PK
    varchar name "UNIQUE"
  }

  TEMPLATES {
    bigint id PK
    bigint category_id FK
    bigint reactor_id FK
    timestamptz created_at
    timestamptz updated_at
    "UNIQUE(category_id, reactor_id)"
  }
```

How to render: any Markdown viewer with Mermaid support (e.g., VS Code with Markdown Preview Mermaid Support) or paste the diagram block at https://mermaid.live
