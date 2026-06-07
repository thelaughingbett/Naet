# 📚 Documentation

> Everything you need to understand how this system is built and why.

---

## 📁 Documentation Structure

```



docs/
├── README.md                          ← docs home
├── architecture.md
├── er-diagram.md
├── models.md
├── actors.md
└── modules/
    ├── enrollment/
    │   ├── index.md                   ← barrel entry point
    │   ├── flowchart.md
    │   ├── sequence.md
    │   ├── class-diagram.md
    │   └── user-journey.md
    ├── fees/
    │   ├── index.md
    │   ├── flowchart.md
    │   ├── sequence.md
    │   ├── class-diagram.md
    │   └── user-journey.md
    ├── session-rollover/
    │   ├── index.md
    │   ├── flowchart.md
    │   └── sequence.md
    ├── auth/
    │   ├── index.md
    │   ├── flowchart.md
    │   ├── sequence.md
    │   └── user-journey.md
    └── timetabling/
        ├── index.md
        ├── flowchart.md
        └── class-diagram.md
```

---

## 🗺️ Where to Start

| Document                                 | What's inside                                           |
| ---------------------------------------- | ------------------------------------------------------- |
| [🗺️ System Overview](system-overview.md) | High-level sketch of the whole system — read this first |
| [🏗️ Architecture](architecture.md)       | Big picture — how the layers fit together               |
| [🗃️ Database Schema](er-diagram.md)      | Every model and their relationships                     |
| [📋 Models Reference](models.md)         | Field-by-field model breakdown                          |
| [🔐 Admin & Permissions](admin.md)       | Who can see and do what                                 |

---

## 📦 Module Breakdown

> Each module has its own index page with flowcharts, sequence diagrams,
> class diagrams, and user journeys — all in one place.

| Module                                                   | Description                             |
| -------------------------------------------------------- | --------------------------------------- |
| [🎓 Enrollment](modules/enrollment/index.md)             | How students get into courses           |
| [💰 Fees & Payments](modules/fees/index.md)              | Payment processing and overdraft logic  |
| [🔄 Session Rollover](modules/session-rollover/index.md) | Academic year transition                |
| [🔑 Auth & Access](modules/auth/index.md)                | Login flow and role-based access        |
| [🕐 Timetabling](modules/timetabling/index.md)           | Schedule management and clash detection |

---

> 💡 **Tip:** All Mermaid diagrams render automatically on GitHub.
> Clone the repo and open any `.md` file to see them live.
