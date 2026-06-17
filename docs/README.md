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
    ├── email_generation/
    │   ├── index.md                   ← barrel entry point
    │   ├── flowchart.md
    │   ├── sequence.md
    │   ├── class-diagram.md
    │   └── user-journey.md
    ├── erp/
    │   ├── index.md
    │   ├── flowchart.md
    │   ├── sequence.md
    │   ├── class-diagram.md
    │   └── user-journey.md
    ├── events/
    │   ├── index.md
    │   ├── flowchart.md
    │   ├── sequence.md
    │   ├── class-diagram.md
    │   └── user-journey.md
    ├── news/
    │   ├── index.md
    │   ├── flowchart.md
    │   ├── sequence.md
    │   ├── class-diagram.md
    │   └── user-journey.md
    ├── payments/
    │   ├── index.md
    │   ├── flowchart.md
    │   ├── sequence.md
    │   ├── class-diagram.md
    │   └── user-journey.md
    ├── results/
    │   ├── index.md
    │   ├── flowchart.md
    │   ├── sequence.md
    │   ├── class-diagram.md
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

| Module                                                   | Description                              |
| -------------------------------------------------------- | ---------------------------------------- |
| [📧 Email Generation](modules/email_generation/index.md) | Automated email creation and delivery    |
| [🏢 ERP](modules/erp/index.md)                           | Enterprise resource planning integration |
| [📅 Events](modules/events/index.md)                     | Event scheduling and management          |
| [📰 News](modules/news/index.md)                         | News publishing and feed management      |
| [💳 Payments](modules/payments/index.md)                 | Payment processing and transaction logic |
| [📊 Results](modules/results/index.md)                   | Academic results and grade management    |
| [🕐 Timetabling](modules/timetabling/index.md)           | Schedule management and clash detection  |

---

> 💡 **Tip:** All Mermaid diagrams render automatically on GitHub.
> Clone the repo and open any `.md` file to see them live.
