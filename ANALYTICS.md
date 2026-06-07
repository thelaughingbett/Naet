# 📊 Analytics & Data Science

> This document outlines the analytics capabilities built into the system,
> the data science roadmap, and how the existing dataset can be used to
> improve student outcomes, lecturer effectiveness, and institutional
> decision-making.
>
> All analytics are built on data already collected by the system —
> no new data collection infrastructure is required for Phase 1 and 2.

---

## 🗃️ The Dataset

The system sits on a rich, multi-dimensional dataset that most institutions
don't have in one place:

| Data Type      | Models                                      | What it enables                            |
| -------------- | ------------------------------------------- | ------------------------------------------ |
| 📚 Academic    | `Results`, `Enrollment`, `Curriculum`       | Performance tracking, difficulty analysis  |
| 💰 Financial   | `StudentFeeAccount`, `Payment`, `OverDraft` | Fee prediction, financial stress detection |
| 🗓️ Temporal    | `Session`, `Reporting`, `enrolled`          | Trend analysis, trajectory modelling       |
| 👤 Demographic | `Student` (county, nationality, etc.)       | Equity analysis, regional patterns         |
| 🕐 Behavioural | `Reporting`, `Enrollment` timing            | Engagement signals, at-risk detection      |

---

## 🚦 Phased Roadmap

```
Phase 1 — Now (no new models, uses existing data)
├── At-risk student detection
├── Session performance dashboard
└── Grade trajectory charts on student portal

Phase 2 — After 2+ sessions of data
├── Course difficulty index
├── Fee collection forecasting
├── Lecturer load analysis
└── Graduation likelihood scoring

Phase 3 — After 3+ years of data
├── Dropout prediction (ML)
├── Personalised unit recommendations
└── Fee payment behaviour modelling
```

> ⚠️ Do not start Phase 3 without sufficient historical data.
> Underfitted models are worse than no model — they create false confidence.

---

## 🎯 Phase 1 — High Value, Available Now

### 🔴 At-Risk Student Detection

Identifies students likely to drop out or fail using signals already
in the system. No machine learning required — rule-based scoring.

**Risk signals used:**

| Signal                        | Source                  | Weight       |
| ----------------------------- | ----------------------- | ------------ |
| Fee balance as % of total     | `StudentFeeAccount`     | Up to 30 pts |
| Average CAT score below 40    | `Results`               | 30 pts       |
| Not reported for semester     | `Reporting`             | 20 pts       |
| Previously deferred           | `Student.deffered`      | 10 pts       |
| Behind expected year of study | `Student.year_of_study` | 10 pts       |

**Output:** A risk score 0–100 surfaced on the student list in admin:

```
🔴 High    (70–100) — immediate intervention recommended
🟡 Medium  (40–69)  — monitor closely
🟢 Low     (0–39)   — on track
```

**Where it appears:**

- `StudentAdmin` list — dept admins see risk indicators for their students
- Session dashboard — count of high-risk students per department

---

### 📊 Session Performance Dashboard

Aggregate statistics for the active session — visible to institution
and school admins. Answers the questions management actually asks:

```
How many students have reported this semester?
What percentage of fee accounts are cleared?
What is the average CAT score across all courses?
Which departments have the most at-risk students?
How much has been collected vs total billed?
```

**Accessible at:** `/admin/` dashboard (institution admin only)

---

### 📈 Grade Trajectory — Student Portal

Students see their own performance trend across sessions as a line chart.
Average score per session — shows whether they are improving, declining,
or stable. No student sees another student's data.

**Accessible at:** `/academics/results/` — chart rendered via Chart.js

---

## 🔬 Phase 2 — After 2 Sessions of Data

### 📚 Course Difficulty Index

Ranks courses by average score and fail rate across all students.
Distinguishes between genuinely difficult content and poor delivery.

**Output per course:**

```
Course         | Avg Score | Fail Rate | Sessions analysed
CS301 Networks |   52.4    |   18%     | 3
CS410 AI       |   38.1    |   41%     | 2  ← flag for review
```

Useful for academic quality assurance — directly relevant to CUE audits.

---

### 💰 Fee Collection Forecasting

Predicts expected fee collection for the next session based on:

- Historical payment rates per programme
- Enrollment numbers for the upcoming session
- Overdraft carry-forward amounts

Gives the finance office advance notice of expected shortfalls.

---

### 👨‍🏫 Lecturer Load Analysis

Analyses teaching hours per lecturer per session:

- Flags overloaded lecturers (risk of burnout, quality decline)
- Identifies underutilised capacity
- Feeds into the timetable generator to distribute load evenly

---

### 🎓 Graduation Likelihood Scoring

Rule-based prediction of whether a student will graduate on time:

```
on_track   → completing units at expected rate
at_risk    → 10–30% behind expected completion
off_track  → more than 30% behind
```

Triggers early academic counselling for at-risk students.

---

## 🤖 Phase 3 — Machine Learning (3+ Years of Data)

### Dropout Prediction Model

Logistic regression trained on historical student data.

**Features:**

```
Average CAT score — first semester
Fee clearance rate — first semester
Reported on time (bool)
Deferred in year 1 (bool)
Number of electives registered
County (proxy for socioeconomic context)
```

**Target:** `graduated` (bool)

**Tools:** `scikit-learn`, `pandas`, `joblib` for model persistence

> This model needs at least 3 cohorts of graduated/dropped students
> before it produces reliable predictions. Do not deploy earlier.

---

### Personalised Unit Recommendations

Recommends elective units to students based on:

- What high-performing students in the same programme chose
- The student's own performance profile
- Course difficulty index

Collaborative filtering — similar to how streaming services recommend content.

---

### Fee Payment Behaviour Modelling

Predicts whether a specific student will clear fees by the deadline,
allowing proactive outreach by the finance office before the deadline passes.

---

## 🛠️ Technical Stack

| Tool                   | Purpose                             | Phase |
| ---------------------- | ----------------------------------- | ----- |
| `django.db.models.Avg` | Aggregations in views               | 1     |
| `Chart.js`             | Frontend charts (already available) | 1     |
| `pandas`               | DataFrame manipulation              | 2     |
| `django-pandas`        | QuerySet → DataFrame bridge         | 2     |
| `matplotlib`           | Chart generation for PDF reports    | 2     |
| `scikit-learn`         | ML models                           | 3     |
| `joblib`               | Model persistence                   | 3     |

Install for Phase 2:

```bash
pip install pandas django-pandas matplotlib
```

---

## 🔐 Privacy & Ethics

Analytics on student data carries real ethical weight.

### What is acceptable

- Aggregate statistics (averages, counts, rates) — no individual identified
- At-risk scores shown only to authorised staff (dept admin and above)
- Students seeing their **own** trajectory — never another student's
- Anonymised data used for model training

### What is not acceptable

- Sharing individual student risk scores publicly or with other students
- Using ethnicity, religion, or county as features in predictive models
  without explicit ethical review — this risks encoding discrimination
- Automated decisions based solely on model output —
  a human must review and act, not the system
- Retaining raw student data beyond the retention periods in
  [DATA_PROTECTION.md](DATA_PROTECTION.md) for analytics purposes

### Algorithmic transparency

Students have the right to know if a score or decision affecting them
was informed by automated processing — this is required under both the
**Kenya DPA** and general principles of fairness.

Any at-risk flag shown to staff must be:

- Based on documented, explainable signals (not a black box)
- Accompanied by the specific reasons (e.g. "fee balance 85% unpaid")
- Reviewable and overrideable by staff

---

## 📁 File Structure

```
utils/
├── analytics.py        ← at-risk scoring, session stats, trajectory
├── forecasting.py      ← fee and enrollment forecasting (Phase 2)
└── ml/
    ├── dropout.py      ← dropout prediction model (Phase 3)
    ├── recommend.py    ← unit recommendation (Phase 3)
    └── models/         ← serialised trained models (Phase 3)

templates/base/
└── analytics/
    ├── dashboard.html  ← institution admin session dashboard
    └── trajectory.html ← student grade trajectory chart
```

---

## 📋 What Each Role Sees

| Role                 | Analytics Access                                            |
| -------------------- | ----------------------------------------------------------- |
| 🏛️ Institution Admin | Full session dashboard, all departments, fee forecasts      |
| 🏫 School Admin      | School-level dashboard, dept breakdowns                     |
| 🏢 Dept Admin        | Department students — at-risk indicators, course difficulty |
| 👨‍🏫 Lecturer          | Their own courses — class average, score distribution       |
| 🎓 Student           | Own grade trajectory, own fee history                       |

---

## 🔗 Related Documents

| Document                                                             | Description                             |
| -------------------------------------------------------------------- | --------------------------------------- |
| [DATA_PROTECTION.md](DATA_PROTECTION.md)                             | Data retention, student rights, consent |
| [LEGAL.md](LEGAL.md)                                                 | CUE audit requirements, KRA retention   |
| [docs/models.md](docs/models.md)                                     | Full model reference — data sources     |
| [docs/modules/academics/index.md](docs/modules/academics/index.md)   | Results and enrollment module           |
| [docs/modules/financials/index.md](docs/modules/financials/index.md) | Fee and payment module                  |
| [README.md](README.md)                                               | Project overview                        |
