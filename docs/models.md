# 📋 Models Reference

> Field-by-field breakdown of every model in the system.
> Use this as your data dictionary — no need to dig through `models.py`.

---

## 📑 Contents

| Model                                       | Description                                     |
| ------------------------------------------- | ----------------------------------------------- |
| [👤 User](#-user)                           | Base login account for all system users         |
| [🎓 Student](#-student)                     | Student profile with academic and personal info |
| [👨‍🏫 Lecturer](#-lecturer)                   | Staff member who teaches courses                |
| [🏢 DeptAdmin](#-deptadmin)                 | Administrator scoped to a department            |
| [🏫 SchoolAdmin](#-schooladmin)             | Administrator scoped to a school                |
| [🏛️ InstitutionAdmin](#-institutionadmin)   | Top-level system administrator                  |
| [🏫 School](#-school)                       | A faculty or school within the institution      |
| [🏢 Department](#-department)               | A department within a school                    |
| [📖 Programme](#-programme)                 | A degree programme within a department          |
| [🏛️ Tclass](#-tclass)                       | A class cohort within a programme               |
| [📚 Course](#-course)                       | An individual unit or subject                   |
| [📋 Curriculum](#-curriculum)               | A course offered to a class in a session        |
| [🗓️ Session](#-session)                     | An academic semester                            |
| [✅ Reporting](#-reporting)                 | Student check-in record per session             |
| [🧾 FeeStructure](#-feestructure)           | Fee breakdown for a class per session           |
| [💰 StudentFeeAccount](#-studentfeeaccount) | Per-student financial ledger                    |
| [💳 Payment](#-payment)                     | Individual payment transaction                  |
| [⚠️ OverDraft](#-overdraft)                 | Overpayment record with carry-forward logic     |
| [📊 Results](#-results)                     | CAT or exam score per student per course        |
| [🕐 Timetable](#-timetable)                 | Class schedule slot with clash prevention       |

---

## 👤 User

> The base login account shared by all system users.
> Authentication is email-based. Role determines which profile model is created.

**Relationships**

- `student_profile` ← `Student` (reverse OneToOne)
- `lecturer_profile` ← `Lecturer` (reverse OneToOne)
- `deptadmin_profile` ← `DeptAdmin` (reverse OneToOne)
- `schooladmin_profile` ← `SchoolAdmin` (reverse OneToOne)
- `institutionadmin_profile` ← `InstitutionAdmin` (reverse OneToOne)

| Field             | Type          | Notes                                        |
| ----------------- | ------------- | -------------------------------------------- |
| `record_id`       | UUIDField     | Primary key, auto-generated                  |
| `email`           | EmailField    | Unique — used as username                    |
| `first_name`      | CharField     | Nullable                                     |
| `last_name`       | CharField     | Nullable                                     |
| `surname`         | CharField     | Nullable — middle name                       |
| `gender`          | CharField     | `M` = Male, `F` = Female                     |
| `profile_picture` | ImageField    | Uploads to `profiles/`, default provided     |
| `role`            | CharField     | `student` / `staff` / `admin`                |
| `is_active`       | BooleanField  | Default: `True`                              |
| `is_staff`        | BooleanField  | Default: `False` — grants admin panel access |
| `is_activated`    | BooleanField  | Default: `False` — custom activation flag    |
| `created_at`      | DateTimeField | Auto-set on creation                         |
| `updated_at`      | DateTimeField | Auto-updated on save                         |

**Properties**

| Property    | Returns                                |
| ----------- | -------------------------------------- |
| `full_name` | `"{first_name} {surname} {last_name}"` |
| `half_name` | `"{first_name}  {last_name}"`          |

---

## 🎓 Student

> Registered student with full academic, personal, family, and emergency contact information.

**Relationships**

- `user` → `User` (OneToOne) — login account
- `class_entered` → `Tclass` (ForeignKey) — enrolled class
- `enrollments` → `Curriculum` (ManyToMany) — course enrollments
- `reportings` ← `Reporting` (reverse FK)
- `fee_accounts` ← `StudentFeeAccount` (reverse FK)

**Personal Info**

| Field            | Type       | Notes                                 |
| ---------------- | ---------- | ------------------------------------- |
| `national_id`    | CharField  | Unique                                |
| `id_type`        | CharField  | `national` / `passport` / `birthCert` |
| `date_of_birth`  | DateField  |                                       |
| `place_of_birth` | CharField  |                                       |
| `telephone_no`   | CharField  |                                       |
| `school_email`   | EmailField | Unique — institution-assigned         |
| `religion`       | CharField  |                                       |
| `nationality`    | CharField  | Default: `Kenyan`                     |
| `ethnicity`      | CharField  |                                       |

**Address**

| Field          | Type      | Notes |
| -------------- | --------- | ----- |
| `domicile`     | CharField |       |
| `county`       | CharField |       |
| `sub_county`   | CharField |       |
| `constituency` | CharField |       |
| `division`     | CharField |       |
| `location`     | CharField |       |
| `home_address` | CharField |       |

**Family Info**

| Field                  | Type         | Notes                                 |
| ---------------------- | ------------ | ------------------------------------- |
| `marital_status`       | CharField    | `M` = Married, `U` = Unmarried        |
| `name_of_spouse`       | CharField    | Nullable                              |
| `spouse_contact`       | CharField    | Nullable                              |
| `occupation_of_spouse` | CharField    | Nullable                              |
| `number_of_children`   | IntegerField | Nullable                              |
| `father_name`          | CharField    |                                       |
| `father_id_type`       | CharField    | `national` / `passport` / `birthCert` |
| `father_id_no`         | CharField    |                                       |
| `father_date_of_birth` | DateField    |                                       |
| `mother_name`          | CharField    |                                       |
| `mother_id_type`       | CharField    | `national` / `passport` / `birthCert` |
| `mother_id_no`         | CharField    |                                       |
| `mother_date_of_birth` | DateField    |                                       |

**Emergency Contacts**

| Field                              | Type      | Notes                 |
| ---------------------------------- | --------- | --------------------- |
| `emergency_contact_name`           | CharField | Primary contact       |
| `emergency_contact_phone`          | CharField |                       |
| `emergency_contact_email`          | CharField |                       |
| `emergency_contact_relationship`   | CharField | e.g. Guardian, Parent |
| `emergency_contact_address`        | CharField | Nullable              |
| `emergency_contact_2_name`         | CharField | Secondary contact     |
| `emergency_contact_2_phone`        | CharField |                       |
| `emergency_contact_2_email`        | CharField |                       |
| `emergency_contact_2_relationship` | CharField |                       |
| `emergency_contact_2_address`      | CharField | Nullable              |

**Academic Info**

| Field                         | Type            | Notes                        |
| ----------------------------- | --------------- | ---------------------------- |
| `registration_number`         | CharField       | Unique — e.g. `BSC/001/2024` |
| `class_entered`               | ForeignKey      | → `Tclass`                   |
| `year_of_study`               | IntegerField    | Default: `1`                 |
| `stay`                        | CharField       | `resident` / `outside`       |
| `hostel`                      | CharField       | `A` / `B` / `C`, nullable    |
| `enrolled`                    | DateTimeField   | Auto-set on creation         |
| `deferred`                    | BooleanField    | Default: `False`             |
| `graduated`                   | DateField       | Nullable — set on graduation |
| `name_of_secondary_school`    | CharField       |                              |
| `address_of_secondary_school` | CharField       |                              |
| `enrollments`                 | ManyToManyField | → `Curriculum`               |

---

## 👨‍🏫 Lecturer

> A staff member who teaches courses and is assigned to a department.

**Relationships**

- `user` → `User` (OneToOne)
- `department` → `Department` (ForeignKey)
- Assigned to `Curriculum` entries via ManyToMany
- Assigned to `Timetable` slots via ForeignKey

| Field          | Type          | Notes          |
| -------------- | ------------- | -------------- |
| `record_id`    | UUIDField     | Primary key    |
| `user`         | OneToOneField | → `User`       |
| `staff_number` | CharField     | Unique         |
| `department`   | ForeignKey    | → `Department` |
| `created_at`   | DateTimeField | Auto-set       |
| `updated_at`   | DateTimeField | Auto-updated   |

---

## 🏢 DeptAdmin

> An administrator with access scoped to a single department.

**Relationships**

- `user` → `User` (OneToOne)
- `department` → `Department` (ForeignKey)

| Field        | Type          | Notes          |
| ------------ | ------------- | -------------- |
| `record_id`  | UUIDField     | Primary key    |
| `user`       | OneToOneField | → `User`       |
| `department` | ForeignKey    | → `Department` |
| `created_at` | DateTimeField | Auto-set       |
| `updated_at` | DateTimeField | Auto-updated   |

---

## 🏫 SchoolAdmin

> An administrator with access scoped to a single school.

**Relationships**

- `user` → `User` (OneToOne)
- `school` → `School` (ForeignKey)

| Field        | Type          | Notes        |
| ------------ | ------------- | ------------ |
| `record_id`  | UUIDField     | Primary key  |
| `user`       | OneToOneField | → `User`     |
| `school`     | ForeignKey    | → `School`   |
| `created_at` | DateTimeField | Auto-set     |
| `updated_at` | DateTimeField | Auto-updated |

---

## 🏛️ InstitutionAdmin

> Top-level administrator with full access to everything.
> Equivalent to a superuser in terms of data visibility.

**Relationships**

- `user` → `User` (OneToOne)

| Field        | Type          | Notes        |
| ------------ | ------------- | ------------ |
| `record_id`  | UUIDField     | Primary key  |
| `user`       | OneToOneField | → `User`     |
| `created_at` | DateTimeField | Auto-set     |
| `updated_at` | DateTimeField | Auto-updated |

---

## 🏫 School

> A faculty or school within the institution — e.g. School of Engineering.

**Relationships**

- `department_set` ← `Department` (reverse FK)

| Field            | Type          | Notes                                                        |
| ---------------- | ------------- | ------------------------------------------------------------ |
| `record_id`      | UUIDField     | Primary key                                                  |
| `school_name`    | CharField     |                                                              |
| `active_session` | ForeignKey    | → `Session`, nullable — consider moving to institution level |
| `created_at`     | DateTimeField | Auto-set                                                     |
| `updated_at`     | DateTimeField | Auto-updated                                                 |

> ⚠️ **Note:** `active_session` on `School` is a candidate for removal. Session is institution-wide — see [Architecture](architecture.md).

---

## 🏢 Department

> A department within a school — e.g. Department of Computer Science.

**Relationships**

- `school` → `School` (ForeignKey)
- `programme_set` ← `Programme` (reverse FK)
- `lecturer_set` ← `Lecturer` (reverse FK)
- `deptadmin_set` ← `DeptAdmin` (reverse FK)

| Field             | Type          | Notes        |
| ----------------- | ------------- | ------------ |
| `record_id`       | UUIDField     | Primary key  |
| `department_name` | CharField     |              |
| `school`          | ForeignKey    | → `School`   |
| `created_at`      | DateTimeField | Auto-set     |
| `updated_at`      | DateTimeField | Auto-updated |

---

## 📖 Programme

> A degree programme — e.g. BSc Computer Science.

**Relationships**

- `department` → `Department` (ForeignKey)
- `current_class` → `Tclass` (ForeignKey, nullable)
- `tclass_set` ← `Tclass` (reverse FK)

| Field            | Type          | Notes                                                      |
| ---------------- | ------------- | ---------------------------------------------------------- |
| `record_id`      | UUIDField     | Primary key                                                |
| `programme_name` | CharField     |                                                            |
| `department`     | ForeignKey    | → `Department`                                             |
| `current_class`  | ForeignKey    | → `Tclass`, nullable — the active class for this programme |
| `created_at`     | DateTimeField | Auto-set                                                   |
| `updated_at`     | DateTimeField | Auto-updated                                               |

---

## 🏛️ Tclass

> A class cohort within a programme — e.g. BSc CS Year 1 (2024 intake).

**Relationships**

- `programme` → `Programme` (ForeignKey)
- `courses` → `Course` (ManyToMany via `Curriculum`)
- `student_set` ← `Student` (reverse FK via `class_entered`)
- `curriculum_set` ← `Curriculum` (reverse FK)
- `fee_structures` ← `FeeStructure` (reverse FK)
- `timetable_set` ← `Timetable` (reverse FK)

| Field        | Type            | Notes                                       |
| ------------ | --------------- | ------------------------------------------- |
| `record_id`  | UUIDField       | Primary key                                 |
| `class_name` | CharField       |                                             |
| `programme`  | ForeignKey      | → `Programme`                               |
| `courses`    | ManyToManyField | → `Course` via `Curriculum` (through model) |
| `created_at` | DateTimeField   | Auto-set                                    |
| `updated_at` | DateTimeField   | Auto-updated                                |

---

## 📚 Course

> An individual unit or subject — e.g. Database Systems (CS301).

**Relationships**

- `department` → `Department` (ForeignKey)
- `curriculum_set` ← `Curriculum` (reverse FK)

| Field         | Type          | Notes                                          |
| ------------- | ------------- | ---------------------------------------------- |
| `record_id`   | UUIDField     | Primary key                                    |
| `course_name` | CharField     |                                                |
| `course_code` | CharField     | Unique — e.g. `CS301`                          |
| `department`  | ForeignKey    | → `Department`                                 |
| `type`        | CharField     | `C` = Core, `E` = Elective, `CC` = Common Unit |
| `created_at`  | DateTimeField | Auto-set                                       |
| `updated_at`  | DateTimeField | Auto-updated                                   |

---

## 📋 Curriculum

> A course offered to a specific class in a specific session.
> The junction between `Tclass`, `Course`, and `Session`.

**Relationships**

- `Tclass` → `Tclass` (ForeignKey)
- `course` → `Course` (ForeignKey)
- `session` → `Session` (ForeignKey)
- `professor` → `Lecturer` (ManyToMany)
- `students` ← `Student` (reverse M2M via `enrollments`)

| Field        | Type            | Notes                       |
| ------------ | --------------- | --------------------------- |
| `record_id`  | UUIDField       | Primary key                 |
| `Tclass`     | ForeignKey      | → `Tclass`                  |
| `course`     | ForeignKey      | → `Course`                  |
| `session`    | ForeignKey      | → `Session`                 |
| `professor`  | ManyToManyField | → `Lecturer`, blank allowed |
| `created_at` | DateTimeField   | Auto-set                    |
| `updated_at` | DateTimeField   | Auto-updated                |

**Constraints**

- `unique_together`: `(course, Tclass, session)` — a course can only appear once per class per session

**Class Methods**

| Method                                             | Description                                                                      |
| -------------------------------------------------- | -------------------------------------------------------------------------------- |
| `clone_curriculum(from_session_id, to_session_id)` | Copies all curriculum entries from one session to another — used during rollover |

---

## 🗓️ Session

> An academic semester — e.g. 2024/2025 Semester 1.
> There is only ever **one active session** institution-wide.

**Relationships**

- `curriculum_set` ← `Curriculum` (reverse FK)
- `reporting_set` ← `Reporting` (reverse FK)
- `fee_structures` ← `FeeStructure` (reverse FK)
- `fee_accounts` ← `StudentFeeAccount` (reverse FK)
- `timetable_set` ← `Timetable` (reverse FK)

| Field           | Type          | Notes                                                  |
| --------------- | ------------- | ------------------------------------------------------ |
| `record_id`     | UUIDField     | Primary key                                            |
| `academic_year` | CharField     | Format: `2024/2025`                                    |
| `semester`      | CharField     | `1` / `2` / `3`                                        |
| `start_date`    | DateField     |                                                        |
| `end_date`      | DateField     | Nullable                                               |
| `is_active`     | BooleanField  | Default: `False` — only one should be `True` at a time |
| `created_at`    | DateTimeField | Auto-set                                               |
| `updated_at`    | DateTimeField | Auto-updated                                           |

**Constraints**

- `unique_together`: `(academic_year, semester)`

**Methods**

| Method                         | Description                                                                         |
| ------------------------------ | ----------------------------------------------------------------------------------- |
| `generate_next_session_name()` | Returns `(next_semester, start_date, next_year_string)`                             |
| `rollover_academic_session()`  | Class method — transitions to next session, clones curriculum, processes overdrafts |

---

## ✅ Reporting

> Records a student's check-in for a given session.
> A student can only report once per session.

**Relationships**

- `student` → `Student` (ForeignKey)
- `session` → `Session` (ForeignKey)

| Field          | Type          | Notes                 |
| -------------- | ------------- | --------------------- |
| `record_id`    | UUIDField     | Primary key           |
| `student`      | ForeignKey    | → `Student`           |
| `session`      | ForeignKey    | → `Session`           |
| `reported_via` | CharField     | `online` / `physical` |
| `reported_at`  | DateTimeField | Auto-set on creation  |
| `created_at`   | DateTimeField | Auto-set              |
| `updated_at`   | DateTimeField | Auto-updated          |

**Constraints**

- `unique_together`: `(student, session)` — can't report twice in the same session

---

## 🧾 FeeStructure

> Defines what a class owes for a given session.
> Fees are itemised as a JSON breakdown.

**Relationships**

- `tclass` → `Tclass` (ForeignKey)
- `session` → `Session` (ForeignKey)
- `studentfeeaccount_set` ← `StudentFeeAccount` (reverse FK)

| Field        | Type          | Notes                                                            |
| ------------ | ------------- | ---------------------------------------------------------------- |
| `record_id`  | UUIDField     | Primary key                                                      |
| `tclass`     | ForeignKey    | → `Tclass`                                                       |
| `session`    | ForeignKey    | → `Session`                                                      |
| `breakdown`  | JSONField     | e.g. `{"tuition": 45000, "registration": 5000, "hostel": 12000}` |
| `created_at` | DateTimeField | Auto-set                                                         |
| `updated_at` | DateTimeField | Auto-updated                                                     |

**Constraints**

- `unique_together`: `(tclass, session)`

**Properties**

| Property       | Returns                          |
| -------------- | -------------------------------- |
| `total_amount` | Sum of all values in `breakdown` |

---

## 💰 StudentFeeAccount

> Per-student financial ledger for a session.
> Tracks what is owed, what has been paid, and the current balance.

**Relationships**

- `student` → `Student` (ForeignKey)
- `session` → `Session` (ForeignKey)
- `fee_structure` → `FeeStructure` (ForeignKey)
- `payments` ← `Payment` (reverse FK)
- `overdrafts` ← `OverDraft` (reverse FK)

| Field           | Type          | Notes            |
| --------------- | ------------- | ---------------- |
| `record_id`     | UUIDField     | Primary key      |
| `student`       | ForeignKey    | → `Student`      |
| `session`       | ForeignKey    | → `Session`      |
| `fee_structure` | ForeignKey    | → `FeeStructure` |
| `amount_paid`   | DecimalField  | Default: `0`     |
| `created_at`    | DateTimeField | Auto-set         |
| `updated_at`    | DateTimeField | Auto-updated     |

**Constraints**

- `unique_together`: `(student, session)`

**Properties**

| Property        | Returns                       |
| --------------- | ----------------------------- |
| `amount_billed` | `fee_structure.total_amount`  |
| `balance`       | `amount_billed - amount_paid` |
| `is_cleared`    | `True` if `balance <= 0`      |

---

## 💳 Payment

> An individual payment transaction against a student's fee account.

**Relationships**

- `account` → `StudentFeeAccount` (ForeignKey)
- `overdraft_set` ← `OverDraft` (reverse FK via `transaction`)

| Field             | Type          | Notes                           |
| ----------------- | ------------- | ------------------------------- |
| `record_id`       | UUIDField     | Primary key                     |
| `account`         | ForeignKey    | → `StudentFeeAccount`           |
| `amount`          | DecimalField  |                                 |
| `method`          | CharField     | `mpesa` / `bank` / `cash`       |
| `transaction_ref` | CharField     | Unique — M-Pesa code / bank ref |
| `paid_at`         | DateTimeField | Auto-set on creation            |
| `created_at`      | DateTimeField | Auto-set                        |
| `updated_at`      | DateTimeField | Auto-updated                    |

**Constraints**

- `unique_together`: `(transaction_ref, method)`

**Save logic**

- Returns early if account is already cleared
- Detects overpayment and creates an `OverDraft` record for the excess
- Updates `account.amount_paid` accordingly

---

## ⚠️ OverDraft

> Records an overpayment on a student's fee account.
> Tracked with a status — either carried forward to the next session or flagged for refund.

**Relationships**

- `account` → `StudentFeeAccount` (ForeignKey) — the account that was overpaid
- `transaction` → `Payment` (ForeignKey) — the payment that caused the overdraft
- `applied_to` → `StudentFeeAccount` (ForeignKey, nullable) — the next session's account if carried forward

| Field         | Type          | Notes                              |
| ------------- | ------------- | ---------------------------------- |
| `record_id`   | UUIDField     | Primary key                        |
| `account`     | ForeignKey    | → `StudentFeeAccount`              |
| `amount`      | DecimalField  | The excess amount                  |
| `transaction` | ForeignKey    | → `Payment`                        |
| `status`      | CharField     | `pending` / `carried` / `refunded` |
| `applied_to`  | ForeignKey    | → `StudentFeeAccount`, nullable    |
| `created_at`  | DateTimeField | Auto-set                           |
| `updated_at`  | DateTimeField | Auto-updated                       |

**Status Reference**

| Status        | Meaning                                                 |
| ------------- | ------------------------------------------------------- |
| ⏳ `pending`  | Just recorded, not yet processed                        |
| ✅ `carried`  | Applied as credit to next session's fee account         |
| 💸 `refunded` | Student has no next session — flagged for manual refund |

---

## 📊 Results

> A CAT or exam score for a student in a specific course.

**Relationships**

- `course` → `Course` (ForeignKey)
- `student` → `Student` (ForeignKey)

| Field        | Type          | Notes                                |
| ------------ | ------------- | ------------------------------------ |
| `record_id`  | UUIDField     | Primary key                          |
| `student`    | ForeignKey    | → `Student`                          |
| `course`     | ForeignKey    | → `Course`                           |
| `type`       | CharField     | `C` = CAT, `E` = Exam                |
| `score`      | DecimalField  | Max 5 digits, 2 decimal places       |
| `title`      | CharField     | e.g. `CAT 1`, `End of Semester Exam` |
| `created_at` | DateTimeField | Auto-set                             |
| `updated_at` | DateTimeField | Auto-updated                         |

---

## 🕐 Timetable

> A single scheduled slot — which class has which course, with which lecturer, in which venue, at what time.

**Relationships**

- `session` → `Session` (ForeignKey)
- `tclass` → `Tclass` (ForeignKey)
- `course` → `Course` (ForeignKey)
- `lecturer` → `Lecturer` (ForeignKey)

| Field        | Type          | Notes                                 |
| ------------ | ------------- | ------------------------------------- |
| `record_id`  | UUIDField     | Primary key                           |
| `session`    | ForeignKey    | → `Session`                           |
| `tclass`     | ForeignKey    | → `Tclass`                            |
| `course`     | ForeignKey    | → `Course`                            |
| `lecturer`   | ForeignKey    | → `Lecturer`                          |
| `day`        | CharField     | `MON` / `TUE` / `WED` / `THU` / `FRI` |
| `start_time` | TimeField     |                                       |
| `end_time`   | TimeField     |                                       |
| `venue`      | CharField     | Room or hall name                     |
| `created_at` | DateTimeField | Auto-set                              |
| `updated_at` | DateTimeField | Auto-updated                          |

**Constraints**

- `unique_together`: `(session, venue, day, start_time)` — no double-booking a venue
- `unique_together`: `(session, lecturer, day, start_time)` — no double-booking a lecturer

---

> 🔗 Back to [Project Index](../README.md)
> 🔗 Back to [Documentation Index](./README.md)
> 🔗 See the [ER Diagram](er-diagram.md) for a visual representation of these relationships
> 🔗 See the [models.py](../base/models.py) for the concrete implementation of these relationship
