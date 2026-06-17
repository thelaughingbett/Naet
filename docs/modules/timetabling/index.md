# 🗓️ Timetabling Module

> How classes get scheduled, how exams get scheduled, and how to swap in
> a different algorithm for either one without touching the rest of the
> system. Think of this as the engine room — most students never see it,
> but everything breaks without it.

---

## 🗺️ Overview

Timetabling has two distinct concerns, each with its own pluggable
generator:

```
Weekly Timetable     → which class takes which course, when, and where
Exam Timetable       → which course is examined, when, where, and who invigilates
```

Both follow the same shape: a generator proposes a schedule, and a single
core file per submodule is the only place allowed to write it to the
database.

```
Session curriculum
      ↓
weekly_schedule:  AbstractTimetableStrategy.generate(session)         → TimetableGenerationResult
exam_timetable:   AbstractExamTimetableGenerator.generate(constraints) → ExamPlan
      ↓
core service / scheduler validates the output, then writes
Timetable rows  or  ExamSession + ExamVenue rows
```

The default algorithm for both is a greedy, slot-by-slot solver. It's not
trying to be optimal — it's trying to be correct, fast, and replaceable.
An institution that needs a smarter algorithm (an ILP solver, say) can
swap it in via settings, with no changes to anything else.

---

## 🏗️ Architecture

```
base/modules/timetabling/
├── __init__.py
├── weekly_schedule/
│   ├── base.py                 # AbstractTimetableStrategy, TimetableSlot, TimetableGenerationResult
│   ├── service.py                # run_timetable_generation() — the only place that writes Timetable rows
│   └── strategies/
│       ├── contrib/                # community-contributed strategies
│       └── examples/
│           ├── greedy.py             # GreedyStrategy — the default
│           ├── ilp.py                  # ILPStrategy — globally optimal via PuLP / OR-Tools
│           └── excel.py                  # ExcelImportStrategy — read a pre-filled timetable
└── exam_timetable/
    ├── base.py                 # AbstractExamTimetableGenerator, ExamConstraints, ExamPlan, ExamSlot
    ├── scheduler.py               # generate_exam_timetable() — the only place that writes ExamSession/ExamVenue rows
    └── strategies/
        ├── contrib/                 # community-contributed generators
        └── examples/
            ├── greedy.py              # GreedyExamGenerator — the default
            ├── ilp.py                   # for institutions wanting a globally-optimal solve
            └── excel.py                   # read a pre-filled exam timetable
```

---

## 📐 The Models

### Timetable

```
Timetable
├── curriculum     FK → Curriculum (course + class + session + lecturers)
├── day            'MON' | 'TUE' | 'WED' | 'THU' | 'FRI'
├── time_slot      '08:00-10:00' | '10:00-12:00' | ... (choices)
└── venue          FK → Venue
```

One `Timetable` row = one class, one slot, one venue. Lecturers live on
`Curriculum.professor` (M2M) — not on `Timetable` directly.

### ExamSession

```
ExamSession
├── curriculum     FK → Curriculum
├── exam_type      'MAIN' | 'SUPPLEMENTARY' | 'CAT'
├── date           DateField
└── time_slot      '08:00-11:00' | '11:00-14:00' | ... (choices)
```

### ExamVenue

```
ExamVenue
├── exam_session   FK → ExamSession
├── venue          FK → Venue
└── invigilator    FK → Lecturer
```

`ExamVenue` is separate from `ExamSession` because one exam can span
multiple venues (large cohorts, split across halls) — each venue gets
its own invigilator.

### ExamClash

Recorded when `ExamSession.detect_all_clashes(session)` finds a student
sitting two exams at the same date and time slot. Surfaced in the admin
for manual resolution.

---

## ⚙️ Configuration

The two submodules are configured independently, since each generator
needs a different shape of settings:

```python
# settings.py — weekly schedule
TIMETABLE_MODULE_CONFIG = {
    'STRATEGY': 'base.modules.timetabling.weekly_schedule.strategies.examples.greedy.GreedyStrategy',
    'DAYS':  [('MON', 'Monday'), ('TUE', 'Tuesday'), ('WED', 'Wednesday'), ('THU', 'Thursday'), ('FRI', 'Friday')],
    'SLOTS': [('08:00-10:00', '8 – 10am'), ('10:00-12:00', '10am – 12pm'), ('13:00-15:00', '1 – 3pm')],
}

# settings.py — exam timetable
TIMETABLE_GENERATOR = 'base.modules.timetabling.exam_timetable.strategies.examples.greedy.GreedyExamGenerator'

# or, passing options through to the generator:
TIMETABLE_GENERATOR = {
    'backend': 'base.modules.timetabling.exam_timetable.strategies.examples.ilp.ILPExamGenerator',
    'options': {
        'solver':     'CBC',
        'time_limit': 120,
        'gap':        0.01,
    },
}
```

`TIMETABLE_GENERATOR` also accepts an already-instantiated generator
instance directly, which is useful for tests that want to inject a
double without touching settings.

---

## ⚙️ How the Weekly Generator Works

The default, `GreedyStrategy`, places curriculum entries by trying every
`(day, slot, venue)` combination in order until one satisfies every hard
constraint, tracking bookings entirely in memory rather than re-querying
the database between placements.

### Constraints

| #   | Constraint                                                       | Type |
| --- | ---------------------------------------------------------------- | ---- |
| 1   | Lecturer not already booked at this day + slot                   | Hard |
| 2   | Class not already booked at this day + slot                      | Hard |
| 3   | Venue not already booked at this day + slot                      | Hard |
| 4   | A common unit can't be placed simultaneously for all its classes | Hard |
| 5   | Max 3 slots for one class on the same day                        | Soft |

### Common units (CC) — special handling

A common unit is the same course taken by several classes at once.
Regular courses are placed first; common units are processed last, since
they need a slot where every professor _and_ every class involved is
free at the same time — each class still gets its own venue.

```
CC101 has 3 classes: Year1-CS, Year1-IT, Year1-ENG
Generator finds: MON 08:00-10:00, where all 3 are free
Creates:
  Timetable(curriculum=CC101/Year1-CS,  day=MON, slot=08:00-10:00, venue=Hall A)
  Timetable(curriculum=CC101/Year1-IT,  day=MON, slot=08:00-10:00, venue=Hall B)
  Timetable(curriculum=CC101/Year1-ENG, day=MON, slot=08:00-10:00, venue=Hall C)
```

If an entry can't be placed at all, the strategy returns `success=False`
with a message naming the exact course and class — nothing partial gets
written. Soft-constraint hits (a class creeping up on its daily slot
limit) are recorded as warnings instead, and don't block the write.

### What gets cleared on regeneration

Running the generator clears every `Timetable` record for the session
before writing new ones, inside a single atomic transaction. Manual
edits to `Timetable` rows will be lost on the next run — use the admin
for permanent adjustments after generation, not before.

---

## ⚙️ How the Exam Generator Works

`generate_exam_timetable(session, exam_type='MAIN')` pre-fetches
everything the generator needs — candidate dates, venues, invigilators,
and curriculum entries (including which students are enrolled and which
professors teach each one) — into a plain `ExamConstraints` object before
calling the generator, so the generator itself never touches the
database.

### Constraints

| #   | Constraint                                            | Type |
| --- | ----------------------------------------------------- | ---- |
| 1   | Class not already sitting an exam at this date + slot | Hard |
| 2   | No student has two exams at the same date + slot      | Hard |
| 3   | Venue not already in use at this date + slot          | Hard |
| 4   | Invigilator not already assigned at this date + slot  | Hard |

### Date window

Exam dates are derived from the session's `end_date`, starting 14 days
before it and using weekdays only.

### Invigilator preference

`GreedyExamGenerator` prefers the course's own professors as invigilators
— they know the material and the students — and only falls back to any
free lecturer if none of them are available at that slot.

### Unplaced entries

If an entry can't be placed in any date/slot combination, the generator
records a warning rather than raising. Unlike the weekly generator
though, the exam scheduler treats _any_ warning as fatal: if even one
exam couldn't be placed, nothing is persisted for that run — the whole
generation has to succeed cleanly, or none of it lands. This is worth
keeping in mind when sizing venues and invigilator pools before running
a full session's exam timetable.

### Student clash detection

After generation, `ExamSession.detect_all_clashes(session)` can be run
separately to find any student sitting two exams at once and record them
in `ExamClash` for review.

---

## 🛠️ Adding a New Strategy or Generator

### Weekly schedule

**Step 1 — choose a location.** Institution-specific, written for your
own deployment: `weekly_schedule/strategies/your_strategy.py`. A
reference others can learn from: `strategies/examples/`. Community
contributions: `strategies/contrib/`.

**Step 2 — implement the contract:**

```python
from base.modules.timetabling.weekly_schedule.base import (
    AbstractTimetableStrategy,
    TimetableGenerationResult,
    TimetableSlot,
)


class YourStrategy(AbstractTimetableStrategy):
    def generate(self, session) -> TimetableGenerationResult:
        try:
            slots = []          # build your schedule here
            warnings = []
            return TimetableGenerationResult(success=True, slots=slots, warnings=warnings)
        except Exception as e:
            return TimetableGenerationResult(success=False, message=str(e))
```

**Step 3 — point settings at it:**

```python
TIMETABLE_MODULE_CONFIG = {
    'STRATEGY': 'base.modules.timetabling.weekly_schedule.strategies.your_strategy.YourStrategy',
    'DAYS':  [...],
    'SLOTS': [...],
}
```

### Exam timetable

**Step 1 — choose a location.** Same pattern, under
`exam_timetable/strategies/`.

**Step 2 — implement the contract:**

```python
from base.modules.timetabling.exam_timetable.base import (
    AbstractExamTimetableGenerator,
    ExamConstraints,
    ExamPlan,
    ExamSlot,
)


class YourExamGenerator(AbstractExamTimetableGenerator):
    generator_name = 'your_generator'

    def generate(self, constraints: ExamConstraints) -> ExamPlan:
        plan = ExamPlan(metadata={'generator': self.generator_name})

        for entry in constraints.curriculum_entries:
            plan.slots.append(ExamSlot(
                curriculum_id=entry['id'],
                date=constraints.exam_dates[0],
                time_slot=constraints.slots[0],
                venue_id=constraints.venues[0]['id'],
                invigilator_id=constraints.invigilators[0]['id'],
                exam_type=constraints.exam_type,
            ))

        return plan
```

**Step 3 — point settings at it:**

```python
TIMETABLE_GENERATOR = 'base.modules.timetabling.exam_timetable.strategies.your_generator.YourExamGenerator'
```

---

## 🚦 The Golden Rules

**1. Generators propose — they never persist**
`weekly_schedule/service.py` and `exam_timetable/scheduler.py` are the
only files that ever call `bulk_create`. Everything upstream of that
just builds data structures.

**2. Never let `generate()` raise for an ordinary scheduling failure**
Catch your own exceptions and return a result/plan object — reserve a
real exception for something genuinely unexpected, like a malformed
input or a solver crash.

**3. Hard constraints fail the run; soft constraints become warnings**
A lecturer double-booking is a hard stop. A class having a busy day is
worth a warning, not a rejected schedule (in the weekly generator —
remember the exam scheduler currently treats every warning as fatal,
so an exam generator's "soft" warnings still block persistence there).

**4. Regeneration is destructive by design**
Both generators clear existing records for the session before writing
new ones, atomically. Treat anything written by hand as temporary until
you're done generating.

**5. Validate before you write**
Both submodules run a validation pass over the proposed schedule (legal
day/slot values, no internal double-bookings) before anything touches
the database — catching a bad value here is far cheaper than discovering
it as a DB constraint error mid-transaction.

---

## 🚀 Running the Generators

```bash
# generate weekly timetable for the active session
python manage.py generate_timetable

# generate main exams for the active session
python manage.py generate_exam_timetable --type MAIN

# generate CATs
python manage.py generate_exam_timetable --type CAT

# target a specific session
python manage.py generate_exam_timetable --type SUPPLEMENTARY --session <uuid>
```

---

## ⚠️ Things to Know Before Running

**1. Every curriculum entry needs at least one professor assigned**
Both generators stop immediately and name the exact course + class if
one is missing a professor.

**2. You need venues in the database**
Both generators stop immediately if no venues exist at all.

**3. The greedy algorithms can fail on dense curricula**
With many classes, many courses, and few venues or exam slots, a greedy
algorithm can run out of options before everything is placed. The error
message names exactly which course/class couldn't be placed — the usual
fixes are adding more venues, loosening soft constraints, or switching
to a smarter strategy.

**4. The exam scheduler is all-or-nothing**
If any single exam can't be placed, nothing from that run is written —
unlike the weekly schedule, where soft-constraint warnings can land
alongside a successful write.

---

## 🧪 Testing a Strategy

```python
class YourStrategyTest(TestCase):
    def setUp(self):
        self.session    = SessionFactory(is_active=True)
        self.department = DepartmentFactory()
        self.venues     = VenueFactory.create_batch(5)

        for i in range(3):
            tclass = TclassFactory()
            for j in range(4):
                course   = CourseFactory(department=self.department)
                lecturer = LecturerFactory(department=self.department)
                CurriculumFactory(
                    Tclass=tclass,
                    course=course,
                    session=self.session,
                    professors=[lecturer],
                )

    def test_all_curriculum_placed(self):
        from base.modules.timetabling.weekly_schedule.service import run_timetable_generation
        success, message, count = run_timetable_generation(self.session)

        self.assertTrue(success)
        self.assertEqual(count, Curriculum.objects.filter(session=self.session).count())

    def test_no_venue_double_booking(self):
        from base.modules.timetabling.weekly_schedule.service import run_timetable_generation
        run_timetable_generation(self.session)

        seen = set()
        for slot in Timetable.objects.filter(curriculum__session=self.session):
            key = (slot.venue_id, slot.day, slot.time_slot)
            self.assertNotIn(key, seen, f"Venue double-booked: {key}")
            seen.add(key)
```

---

## 🔗 Where to Go Next

| Topic                                   | Document                                       |
| --------------------------------------- | ---------------------------------------------- |
| 📰 News module                          | [News Module](news.md)                         |
| 🔌 ERP sync module                      | [ERP Module](erp.md)                           |
| 📧 Email generation module              | [Email Generation Module](email_generation.md) |
| 📊 Results import module                | [Results Module](results.md)                   |
| 📋 Timetable / ExamSession model fields | [Models Reference](../models.md)               |
| 🎓 Curriculum structure                 | [Enrollment Module](enrollment/index.md)       |

---

> 🔗 Back to [Documentation Index](../README.md)
