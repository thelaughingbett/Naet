# 🏫 Naet

> A full-featured institutional management system built with Django,
> designed for Kenyan higher education institutions. 🇰🇪
>
> Handles everything from student enrollment and academic session management
> to fee collection, timetabling, vand role-based access control.

---

## ✨ Features

### 🎓 Academic Management

- 🏛️ Multi-level institutional hierarchy — Institution → School → Department → Programme → Class
- 🗓️ Academic session and semester management with automated rollover
- 📚 Curriculum management with course enrollment (core, elective, and common units)
- ⚡ Automatic enrollment of students into core courses on registration
- 🕐 Timetable management with venue and lecturer clash detection
- 📝 Exam scheduling with cross-programme clash detection

### 👤 Student Management

- 📋 Comprehensive student profiles (personal, family, emergency contacts, academic)
- ✅ Student reporting per session (online and physical)
- ⏸️ Deferral and graduation tracking
- 🪟 Proxy model views: Resident Students, Deferred Students, Graduated Students

### 💰 Fee Management

- 🧾 Per-class fee structures with itemised breakdowns (tuition, registration, hostel, etc.)
- 📊 Per-student fee accounts with real-time balance tracking
- 💳 Payment recording (M-Pesa, bank transfer, cash)
- ⚠️ Overdraft detection and carry-forward to next session or refund flagging

### 🔐 User & Access Management

- 👥 Custom user model with role-based access (Student, Staff, Admin)
- 🏛️ Role hierarchy: Institution Admin → School Admin → Dept Admin → Lecturer → Student
- 🔒 Scoped Django admin — each role sees only the data within their jurisdiction
- ⚡ Automatic group and permission assignment on user creation

### 📊 Results

- 📝 CAT and exam result recording per student per course

---

## 🛠️ Tech Stack

| Layer         | Technology                                              |
| ------------- | ------------------------------------------------------- |
| 🐍 Backend    | Python, Django                                          |
| 🗄️ Database   | PostgreSQL                                              |
| 🔐 Auth       | Django AbstractBaseUser + custom UserManager            |
| 🖥️ Admin      | Django Admin with custom scoping, proxy models, inlines |
| ⚡ Automation | Django signals for enrollment and session events        |

---

## 📁 Project Structure

```
StudentsPortal/
├── base/
│   ├── models.py         # All models
│   ├── admin.py          # Custom ModelAdmin classes
│   ├── signals.py        # Signal receivers
│   ├── managers.py       # Custom UserManager
│   ├── forms.py          # UserCreationForm, UserChangeForm
│   ├── apps.py           # AppConfig with signals loader
│   ├── fixtures/         # Seed data
│   ├── templates/        # html templates for the site
│   ├── static/           # static files
│   └── tests/
│       ├── test_models.py
│       ├── test_signals.py
│       └── test_admin.py
├── docs/                 # Full documentation
├── user-upload/          # media folder for user uploaded files
├── manage.py
└── requirements.txt
```

---

## [🗃️ Models Overview](./docs/models.md)

```
User                    Custom AbstractBaseUser (email login)
├── Student             OneToOne → User, academic + personal profile
├── Lecturer            OneToOne → User, department
├── DeptAdmin           OneToOne → User, department
├── SchoolAdmin         OneToOne → User, school
└── InstitutionAdmin    OneToOne → User

School
└── Department
    └── Programme
        └── Tclass (Class)
            └── Curriculum (Tclass + Course + Session + Lecturer)

Session                 Academic year + semester, institution-wide
Reporting               Student check-in per session
FeeStructure            Per class per session fee breakdown
StudentFeeAccount       Per student ledger
Payment                 Individual transactions (M-Pesa, bank, cash)
OverDraft               Overpayment tracking with carry-forward/refund status
Results                 CAT and exam scores per student per course
Timetable               Class schedule with venue and lecturer conflict prevention
```

---

## 🚀 Setup

### 📋 Requirements

- Python 3.10+
- PostgreSQL

### 📦 Installation

```bash
git clone https://github.com/thelaughingbett/StudentsPortal.git
cd StudentsPortal

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### ⚙️ Configuration

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

```env
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgres://user:password@localhost:5432/studentsportal
```

### 🗄️ Database

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py loaddata base/fixtures/data.json  # optional seed data
```

### ▶️ Run

```bash
python manage.py runserver
```

---

## 🔐 Admin Access

Navigate to `/admin` and log in with your superuser credentials.

Role-based access is enforced automatically:

| Role                 | Access                                        |
| -------------------- | --------------------------------------------- |
| 🏛️ Institution Admin | Full access to everything                     |
| 🏫 School Admin      | Own school's departments, students, lecturers |
| 🏢 Dept Admin        | Own department's students and lecturers       |
| 👨‍🏫 Lecturer          | View-only access to students                  |

---

## 💡 Key Design Decisions

- 🔑 **UUID primary keys** on all models for security and portability
- 🗓️ **Session is institution-wide** — one active session at a time, referenced by all academic and financial records
- ⚠️ **Overdraft handling** — overpayments are recorded separately and either carried forward to the next session or flagged for refund
- 🪟 **Proxy models** — `DeferredStudent`, `ResidentStudent`, and `GraduatedStudent` provide filtered admin views of the same student table without duplicating data
- ⚡ **Signal-driven enrollment** — students are automatically enrolled in core and common unit courses when created

---

## 🗺️ Roadmap

- [ ] 📅 Attendance tracking (per timetable slot)
- [ ] 📝 Exam scheduling and invigilation assignment
- [ ] 📱 SMS notifications via Africa's Talking API
- [ ] 🌐 REST API (Django REST Framework)
- [ ] 🖥️ Student and staff self-service portal
- [ ] 📚 Library management module
- [ ] 💼 Payroll for staff
- [ ] 🌾 IoT sensor integration for smart campus monitoring

---

## [📚 Documentation](./docs/README.md)

> Everything you need to understand how this system is built and why.

### 🗺️ Where to Start

| Document                                      | What's inside                                           |
| --------------------------------------------- | ------------------------------------------------------- |
| [🗺️ System Overview](docs/system-overview.md) | High-level sketch of the whole system — read this first |
| [🏗️ Architecture](docs/architecture.md)       | Big picture — how the layers fit together               |
| [🗃️ Database Schema](docs/er-diagram.md)      | Every model and their relationships                     |
| [📋 Models Reference](docs/models.md)         | Field-by-field model breakdown                          |
| [🔐 Admin & Permissions](docs/admin.md)       | Who can see and do what                                 |

---

## 📦 Module Breakdown

| Module                                                        | Description                             |
| ------------------------------------------------------------- | --------------------------------------- |
| [🎓 Enrollment](docs/modules/enrollment/index.md)             | How students get into courses           |
| [💰 Fees & Payments](docs/modules/fees/index.md)              | Payment processing and overdraft logic  |
| [🔄 Session Rollover](docs/modules/session-rollover/index.md) | Academic year transition                |
| [🔑 Auth & Access](docs/modules/auth/index.md)                | Login flow and role-based access        |
| [🕐 Timetabling](docs/modules/timetabling/index.md)           | Schedule management and clash detection |

## 👨‍💻 Author

Built by Emmanuel Bett . 🇰🇪

[GitHub](https://github.com/thelaughingbett) ·

---

## 📄 License

[Apache 2.0 ](./LICENSE)

## ⚖️ Data Protection & Privacy

This system collects and processes sensitive personal data including
national ID numbers, financial records, family information, and
special category data (religion, ethnicity) under the
**Kenya Data Protection Act, 2019**.

Any institution deploying this system must:

- Register as a data controller with the **ODPC** at [odpc.go.ke](https://odpc.go.ke)
- Appoint a Data Protection Officer
- Display a privacy notice at registration
- Enable HTTPS — no exceptions

Full details in [DATA_PROTECTION.md](DATA_PROTECTION.md) 🔐

## 📜 Legal Obligations

Beyond data protection, institutions deploying this system have obligations under:

| Law                                       | Relevance                                         |
| ----------------------------------------- | ------------------------------------------------- |
| Computer Misuse and Cybercrimes Act, 2018 | Unauthorized access, credential security          |
| Universities Act, 2012 (CUE)              | Academic records retention, CUE audit readiness   |
| Kenya Revenue Authority                   | 7-year financial record retention, fee receipting |
| HELB                                      | Semester enrollment verification exports          |
| Persons with Disabilities Act             | Portal accessibility — WCAG 2.1 AA                |

Full details in [LEGAL.md](LEGAL.md) ⚖️

## ⏸️ Deferment & Graduation Tracking

Deferment is tracked as a full audit model — not a simple boolean.
Each deferment event is a `Deferment` record with reason, return session,
status, and approver. Expected graduation is computed dynamically from
programme duration plus deferred semesters.

```
Student defers
└── Deferment record created (status=active)
    ├── session_deferred  → which semester they left
    ├── session_returning → when they plan to come back
    ├── reason            → financial / medical / personal / academic
    └── approved_by       → audit trail

Admin reinstates
└── Deferment.status = reinstated
└── student.deffered = False

Expected graduation
└── Programme.total_semesters + deferment_count
└── Computed from enrollment session forward
└── student.is_overdue → True if past expected date and not graduated
```

Full details → [docs/modules/admissions/index.md](docs/modules/admissions/index.md)

---

## 🔄 ERP Integration

Generic, event-driven synchronisation of any model to any external ERP system.
Not scoped to payments — payments, enrollments, deferments, results, reporting
can all fire ERP events.

### Architecture

```
Something happens anywhere in the system
└── dispatch_erp_event(instance, event)
    └── transaction.on_commit → erp_sync.delay()

Celery task
└── resolves instance from DB
└── looks up event in ERPRegistry
└── runs each registered handler independently
└── logs every attempt to ERPSyncLog

Retry schedule (exponential backoff, per handler)
├── attempt 1 → 60s
├── attempt 2 → 120s
├── attempt 3 → 240s
├── attempt 4 → 480s
└── attempt 5 → exhausted → notify admin
```

### Event naming convention

```
payment.confirmed       enrollment.approved
payment.failed          deferment.created
reporting.submitted     result.published
student.graduated
```

### Adding a new ERP system

Implement `AbstractERPTask`, register it — nothing else changes:

```python
class MyTask(AbstractERPTask):
    event         = 'payment.confirmed'
    model         = 'Payment'
    max_retries   = 5
    retry_backoff = 120

    def sync(self, instance) -> ERPSyncResult:
        # instance is a Payment object
        ...
```

### Dispatching from anywhere

```python
from erp.dispatch import dispatch_erp_event

dispatch_erp_event(payment,    'payment.confirmed')
dispatch_erp_event(enrollment, 'enrollment.approved')
dispatch_erp_event(reporting,  'reporting.submitted')
dispatch_erp_event(deferment,  'deferment.created')
```

Full details → [docs/modules/erp/index.md](docs/modules/erp/index.md)

> 🔗 [Performance & Technical Decisions](docs/PerformanceTechnicalDecisions.md)
