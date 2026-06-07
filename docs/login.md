# Login & Access Control

## Authentication Flow

```mermaid
flowchart TD
    A[User visits /admin] --> B{Authenticated?}
    B -- No --> C[Redirect to login]
    C --> D[Enter email + password]
    D --> E{Valid credentials?}
    E -- No --> F[Show error]
    E -- Yes --> G{is_active?}
    G -- No --> F
    G -- Yes --> H[Load user's groups\nand permissions]
    H --> I[Render admin sidebar\nbased on permissions]
```

## Role Access Matrix

| Model        | Institution Admin | School Admin | Dept Admin | Lecturer  |
| ------------ | ----------------- | ------------ | ---------- | --------- |
| Student      | Full              | Own school   | Own dept   | View only |
| Lecturer     | Full              | Own school   | Own dept   | —         |
| Curriculum   | Full              | Own school   | Own dept   | View only |
| FeeStructure | Full              | Own school   | —          | —         |
| Payment      | Full              | Own school   | —          | —         |
| Session      | Full              | —            | —          | —         |
