# 📋 Models Reference

> Field-by-field breakdown of every model in the system.
> Use this as your data dictionary — no need to dig through `models.py`.
> P.s all models are just guides you are free to mess with them as much as you want

---

## 📑 Contents

| Model                                             | Description                                         |
| ------------------------------------------------- | --------------------------------------------------- |
| [👤 User](#-user)                                 | Base login account for all system users             |
| [🎓 Student](#-student)                           | Student profile with academic and personal info     |
| [👨‍🏫 Lecturer](#-lecturer)                         | Staff member who teaches courses                    |
| [🏢 DeptAdmin](#-deptadmin)                       | Administrator scoped to a department                |
| [🏫 SchoolAdmin](#-schooladmin)                   | Administrator scoped to a school                    |
| [🏛️ InstitutionAdmin](#-institutionadmin)         | Top-level system administrator                      |
| [💻 ItStaff](#-itstaff)                           | IT staff member                                     |
| [💰 FinanceStaff](#-financestaff)                 | Finance staff member                                |
| [🏨 HostelWarden](#-hostelwarden)                 | Manages a hostel building                           |
| [🏫 School](#-school)                             | A faculty or school within the institution          |
| [🏢 Department](#-department)                     | A department within a school                        |
| [📖 Programme](#-programme)                       | A degree programme within a department              |
| [🏛️ Tclass](#-tclass)                             | A class cohort within a programme                   |
| [📚 Course](#-course)                             | An individual unit or subject                       |
| [📋 Curriculum](#-curriculum)                     | A course offered to a class in a session            |
| [🔗 CommonUnitCurriculum](#-commonunitcurriculum) | Proxy — common units shared across multiple classes |
| [📝 Enrollment](#-enrollment)                     | A student's enrollment request for a curriculum     |
| [🗓️ Session](#-session)                           | An academic semester                                |
| [✅ Reporting](#-reporting)                       | Student check-in record per session                 |
| [⏸️ Deferment](#-deferment)                       | A single deferment event for a student              |
| [👨‍👩‍👧 ParentGuardian](#-parentguardian)             | Parent or guardian record for a student             |
| [🆘 EmergencyContact](#-emergencycontact)         | Emergency contact record for a student              |
| [🧾 FeeStructure](#-feestructure)                 | Fee breakdown for a class per session               |
| [💰 StudentFeeAccount](#-studentfeeaccount)       | Per-student financial ledger                        |
| [💳 Payment](#-payment)                           | Individual payment transaction                      |
| [⚠️ OverDraft](#-overdraft)                       | Overpayment record with carry-forward logic         |
| [📊 Result](#-result)                             | CAT or exam score per student per curriculum entry  |
| [🕐 Timetable](#-timetable)                       | Class schedule slot linked to a curriculum entry    |
| [📅 ExamSession](#-examsession)                   | A single exam sitting for a curriculum entry        |
| [🏟️ ExamVenue](#-examvenue)                       | Venue and invigilator assignment for an exam        |
| [⚡ ExamClash](#-examclash)                       | Detected exam time conflict for a student           |
| [🪪 ExamCard](#-examcard)                         | Issued exam admit card for a student in a session   |
| [🏨 Hostel](#-hostel)                             | A physical hostel building on campus                |
| [🚪 Room](#-room)                                 | An individual room within a hostel                  |
| [🛏️ HostelAllocation](#-hostelallocation)         | Links a student to a room for a session             |
| [🔄 ERPSyncLog](#-erpsynclog)                     | Outbound ERP sync attempt log                       |
| [⭐ CourseEvaluation](#-courseevaluation)         | Student rating of a course                          |
| [⭐ LecturerEvaluation](#-lecturerevaluation)     | Student rating of a lecturer                        |
| [⭐ HostelEvaluation](#-hostelevaluation)         | Student rating of their hostel allocation           |
| [📰 NewsItem](#-newsitem)                         | News card synced from external CMS                  |
| [📅 EventItem](#-eventitem)                       | Campus event card with RSVP support                 |

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
| `half_name` | `"{first_name} {last_name}"`           |
| `initials`  | `"{first_name[0]}{last_name[0]}"`      |

---

## 🎓 Student

> Registered student with academic, personal, and address information.
> Emergency contacts and parent/guardian records are now separate models.

**Relationships**

- `user` → `User` (OneToOne) — login account
- `class_entered` → `Tclass` (ForeignKey) — enrolled class
- `enrollments` → `Curriculum` (ManyToMany via `Enrollment`) — course enrollments
- `reportings` ← `Reporting` (reverse FK)
- `fee_accounts` ← `StudentFeeAccount` (reverse FK)
- `deferments` ← `Deferment` (reverse FK)
- `parents` ← `ParentGuardian` (reverse FK)
- `emergency_contacts` ← `EmergencyContact` (reverse FK)
- `hostel_allocations` ← `HostelAllocation` (reverse FK)

**Personal Info**

| Field                  | Type         | Notes                                 |
| ---------------------- | ------------ | ------------------------------------- |
| `national_id`          | CharField    | Unique                                |
| `id_type`              | CharField    | `national` / `passport` / `birthCert` |
| `date_of_birth`        | DateField    |                                       |
| `place_of_birth`       | CharField    |                                       |
| `telephone_no`         | CharField    |                                       |
| `school_email`         | EmailField   | Unique — institution-assigned         |
| `religion`             | CharField    |                                       |
| `nationality`          | CharField    | Default: `Kenyan`                     |
| `ethnicity`            | CharField    |                                       |
| `marital_status`       | CharField    | `M` = Married, `U` = Unmarried        |
| `name_of_spouse`       | CharField    | Nullable                              |
| `spouse_contact`       | CharField    | Nullable                              |
| `occupation_of_spouse` | CharField    | Nullable                              |
| `number_of_children`   | IntegerField | Nullable                              |

**Address**

| Field          | Type      | Notes                                 |
| -------------- | --------- | ------------------------------------- |
| `domicile`     | CharField |                                       |
| `county`       | CharField |                                       |
| `sub_county`   | CharField |                                       |
| `constituency` | CharField |                                       |
| `division`     | CharField |                                       |
| `location`     | CharField |                                       |
| `home_adress`  | CharField | Note: field name has a typo in source |

**Academic Info**

| Field                         | Type            | Notes                           |
| ----------------------------- | --------------- | ------------------------------- |
| `registration_number`         | CharField       | Unique — e.g. `BSC/001/2024`    |
| `class_entered`               | ForeignKey      | → `Tclass`                      |
| `stay`                        | CharField       | `resident` / `outside`          |
| `enrolled`                    | DateTimeField   | Auto-set on creation            |
| `deferred`                    | BooleanField    | Default: `False`                |
| `name_of_secondary_school`    | CharField       |                                 |
| `address_of_secondary_school` | CharField       |                                 |
| `enrollments`                 | ManyToManyField | → `Curriculum` via `Enrollment` |

**Properties**

| Property                      | Returns                                                                          |
| ----------------------------- | -------------------------------------------------------------------------------- |
| `expected_graduation_session` | `Session` — calculated from enrolment session + programme semesters + deferments |
| `semesters_remaining`         | `int` — sessions between now and expected graduation                             |
| `is_overdue`                  | `True` if `semesters_remaining < 0` and class not graduated                      |
| `current_hostel`              | `Room` — active allocation room for the current session                          |

---

## 👨‍🏫 Lecturer

> A staff member who teaches courses and is assigned to a department.

**Relationships**

- `user` → `User` (OneToOne via `StaffUserMixin`)
- `department` → `Department` (ForeignKey via `WithDepartmentMixin`)
- Assigned to `Curriculum` entries via ManyToMany
- Assigned to `Timetable` slots via ForeignKey
- Assigned as `invigilator` on `ExamVenue`

| Field          | Type          | Notes                                    |
| -------------- | ------------- | ---------------------------------------- |
| `record_id`    | UUIDField     | Primary key                              |
| `user`         | OneToOneField | → `User`                                 |
| `staff_number` | CharField     | Unique                                   |
| `department`   | ForeignKey    | → `Department`                           |
| `title`        | CharField     | e.g. `Lec.`, `Snr. Lec.`, `Prof.`, `HOD` |
| `created_at`   | DateTimeField | Auto-set                                 |
| `updated_at`   | DateTimeField | Auto-updated                             |

---

## 🏢 DeptAdmin

> An administrator with access scoped to a single department.

**Relationships**

- `user` → `User` (OneToOne)
- `department` → `Department` (ForeignKey)

| Field          | Type          | Notes          |
| -------------- | ------------- | -------------- |
| `record_id`    | UUIDField     | Primary key    |
| `user`         | OneToOneField | → `User`       |
| `staff_number` | CharField     | Unique         |
| `department`   | ForeignKey    | → `Department` |
| `created_at`   | DateTimeField | Auto-set       |
| `updated_at`   | DateTimeField | Auto-updated   |

---

## 🏫 SchoolAdmin

> An administrator with access scoped to a single school.

**Relationships**

- `user` → `User` (OneToOne)
- `school` → `School` (ForeignKey)

| Field          | Type          | Notes        |
| -------------- | ------------- | ------------ |
| `record_id`    | UUIDField     | Primary key  |
| `user`         | OneToOneField | → `User`     |
| `staff_number` | CharField     | Unique       |
| `school`       | ForeignKey    | → `School`   |
| `created_at`   | DateTimeField | Auto-set     |
| `updated_at`   | DateTimeField | Auto-updated |

---

## 🏛️ InstitutionAdmin

> Top-level administrator with full access to everything.
> Equivalent to a superuser in terms of data visibility.

**Relationships**

- `user` → `User` (OneToOne)

| Field          | Type          | Notes        |
| -------------- | ------------- | ------------ |
| `record_id`    | UUIDField     | Primary key  |
| `user`         | OneToOneField | → `User`     |
| `staff_number` | CharField     | Unique       |
| `created_at`   | DateTimeField | Auto-set     |
| `updated_at`   | DateTimeField | Auto-updated |

---

## 💻 ItStaff

> IT staff member with system-level access.

| Field          | Type          | Notes        |
| -------------- | ------------- | ------------ |
| `record_id`    | UUIDField     | Primary key  |
| `user`         | OneToOneField | → `User`     |
| `staff_number` | CharField     | Unique       |
| `created_at`   | DateTimeField | Auto-set     |
| `updated_at`   | DateTimeField | Auto-updated |

---

## 💰 FinanceStaff

> Finance staff member with access to fee and payment data.

| Field          | Type          | Notes        |
| -------------- | ------------- | ------------ |
| `record_id`    | UUIDField     | Primary key  |
| `user`         | OneToOneField | → `User`     |
| `staff_number` | CharField     | Unique       |
| `created_at`   | DateTimeField | Auto-set     |
| `updated_at`   | DateTimeField | Auto-updated |

---

## 🏨 HostelWarden

> Manages a hostel building. Assigned as warden on a `Hostel`.

**Relationships**

- `user` → `User` (OneToOne)
- `hostel` → `Hostel` (ForeignKey)
- `managed_hostels` ← `Hostel` (reverse FK via `warden`)

| Field          | Type          | Notes                |
| -------------- | ------------- | -------------------- |
| `record_id`    | UUIDField     | Primary key          |
| `user`         | OneToOneField | → `User`             |
| `staff_number` | CharField     | Unique               |
| `hostel`       | ForeignKey    | → `Hostel`, nullable |
| `created_at`   | DateTimeField | Auto-set             |
| `updated_at`   | DateTimeField | Auto-updated         |

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

| Field                | Type          | Notes                                                      |
| -------------------- | ------------- | ---------------------------------------------------------- |
| `record_id`          | UUIDField     | Primary key                                                |
| `programme_name`     | CharField     |                                                            |
| `degree_type`        | CharField     | e.g. `BSc`, `MSc`, `PhD`, `MBA` — see choices list         |
| `department`         | ForeignKey    | → `Department`                                             |
| `current_class`      | ForeignKey    | → `Tclass`, nullable — the active class for this programme |
| `duration_years`     | IntegerField  | Default: `4`                                               |
| `semesters_per_year` | IntegerField  | Default: `2`                                               |
| `created_at`         | DateTimeField | Auto-set                                                   |
| `updated_at`         | DateTimeField | Auto-updated                                               |

**Properties**

| Property          | Returns                               |
| ----------------- | ------------------------------------- |
| `total_semesters` | `duration_years × semesters_per_year` |

---

## 🏛️ Tclass [Tclass because class was taken 🙃]

> A class cohort within a programme — e.g. BSc CS Year 1 (2024 intake).

**Relationships**

- `programme` → `Programme` (ForeignKey)
- `courses` → `Course` (ManyToMany via `Curriculum`)
- `student_set` ← `Student` (reverse FK via `class_entered`)
- `curriculum_set` ← `Curriculum` (reverse FK)
- `fee_structures` ← `FeeStructure` (reverse FK)
- `timetable_slots` ← `Timetable` (reverse FK via curriculum)

| Field           | Type            | Notes                                       |
| --------------- | --------------- | ------------------------------------------- |
| `record_id`     | UUIDField       | Primary key                                 |
| `class_name`    | CharField       |                                             |
| `programme`     | ForeignKey      | → `Programme`                               |
| `courses`       | ManyToManyField | → `Course` via `Curriculum` (through model) |
| `year_of_study` | IntegerField    | Default: `1`, nullable                      |
| `graduated`     | DateField       | Nullable — set when cohort graduates        |
| `created_at`    | DateTimeField   | Auto-set                                    |
| `updated_at`    | DateTimeField   | Auto-updated                                |

---

## 📚 Course

> An individual unit or subject — e.g. Database Systems (CS301).

**Relationships**

- `department` → `Department` (ForeignKey)
- `curriculum_set` ← `Curriculum` (reverse FK)
- `prerequisites` → `Course` (ManyToMany, self-referential)

| Field           | Type            | Notes                                          |
| --------------- | --------------- | ---------------------------------------------- |
| `record_id`     | UUIDField       | Primary key                                    |
| `course_name`   | CharField       |                                                |
| `course_code`   | CharField       | Unique — e.g. `CS301`                          |
| `department`    | ForeignKey      | → `Department`                                 |
| `course_type`   | CharField       | `C` = Core, `E` = Elective, `CC` = Common Unit |
| `credits`       | IntegerField    | Default: `3`                                   |
| `prerequisites` | ManyToManyField | → `Course` (self), blank allowed               |
| `offered`       | IntegerField    | Default: `1`                                   |
| `created_at`    | DateTimeField   | Auto-set                                       |
| `updated_at`    | DateTimeField   | Auto-updated                                   |

---

## 📋 Curriculum

> A course offered to a specific class in a specific session.
> The junction between `Tclass`, `Course`, and `Session`.

**Relationships**

- `Tclass` → `Tclass` (ForeignKey)
- `course` → `Course` (ForeignKey)
- `session` → `Session` (ForeignKey)
- `professor` → `Lecturer` (ManyToMany)
- `results` → `Student` (ManyToMany via `Result`)
- `enrolled_students` ← `Student` (reverse M2M via `Enrollment`)
- `timetable_slots` ← `Timetable` (reverse FK)
- `exam_sessions` ← `ExamSession` (reverse FK)

| Field        | Type            | Notes                       |
| ------------ | --------------- | --------------------------- |
| `record_id`  | UUIDField       | Primary key                 |
| `Tclass`     | ForeignKey      | → `Tclass`                  |
| `course`     | ForeignKey      | → `Course`                  |
| `session`    | ForeignKey      | → `Session`                 |
| `professor`  | ManyToManyField | → `Lecturer`, blank allowed |
| `results`    | ManyToManyField | → `Student` via `Result`    |
| `created_at` | DateTimeField   | Auto-set                    |
| `updated_at` | DateTimeField   | Auto-updated                |

**Constraints**

- `unique_together`: `(course, Tclass, session)` — a course can only appear once per class per session

**Class Methods**

| Method                                             | Description                                                                      |
| -------------------------------------------------- | -------------------------------------------------------------------------------- |
| `clone_curriculum(from_session_id, to_session_id)` | Copies all curriculum entries from one session to another — used during rollover |

---

## 🔗 CommonUnitCurriculum

> Proxy model over `Curriculum` — filters to common unit (`CC`) courses only.
> Used in the admin to manage courses shared across multiple classes.

| Field | Type    | Notes                |
| ----- | ------- | -------------------- |
| —     | (proxy) | No additional fields |

**Properties**

| Property  | Returns                                                                      |
| --------- | ---------------------------------------------------------------------------- |
| `classes` | QuerySet of `class_name` strings — all classes sharing this course + session |

---

## 📝 Enrollment

> A student's formal enrollment request for a specific curriculum entry.
> Replaces the bare ManyToMany — adds an approval workflow.

**Relationships**

- `student` → `Student` (ForeignKey)
- `curriculum` → `Curriculum` (ForeignKey)

| Field        | Type          | Notes                               |
| ------------ | ------------- | ----------------------------------- |
| `record_id`  | UUIDField     | Primary key                         |
| `student`    | ForeignKey    | → `Student`                         |
| `curriculum` | ForeignKey    | → `Curriculum`                      |
| `status`     | CharField     | `pending` / `approved` / `rejected` |
| `created_at` | DateTimeField | Auto-set                            |
| `updated_at` | DateTimeField | Auto-updated                        |

**Constraints**

- `unique_together`: `(student, curriculum)` — one enrollment record per student per curriculum entry

---

## 🗓️ Session

> An academic semester — e.g. 2024/2025 Semester 1.
> There is only ever **one active session** institution-wide.

**Relationships**

- `curricula` ← `Curriculum` (reverse FK)
- `reportings` ← `Reporting` (reverse FK)
- `fee_structures` ← `FeeStructure` (reverse FK)
- `deferments` ← `Deferment` (reverse FK)
- `hostel_allocations` ← `HostelAllocation` (reverse FK)
- `exam_cards` ← `ExamCard` (reverse FK)

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

**Properties**

| Property   | Returns                                                |
| ---------- | ------------------------------------------------------ |
| `progress` | `int` (0–100) — percentage of session elapsed by today |

**Methods**

| Method                         | Description                                                                        |
| ------------------------------ | ---------------------------------------------------------------------------------- |
| `generate_next_session_name()` | Returns `(next_semester, start_date, next_year_string)`                            |
| `rollover_academic_session()`  | Class method — transitions to next session, clones curriculum, deactivates current |

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

## ⏸️ Deferment

> Records each individual deferment event for a student.
> A student may defer multiple times — each gets its own record.

**Relationships**

- `student` → `Student` (ForeignKey)
- `session_deferred` → `Session` (ForeignKey) — the session deferred from
- `session_returning` → `Session` (ForeignKey, nullable) — expected return session
- `approved_by` → `User` (ForeignKey, nullable)

| Field               | Type          | Notes                                                       |
| ------------------- | ------------- | ----------------------------------------------------------- |
| `record_id`         | UUIDField     | Primary key                                                 |
| `student`           | ForeignKey    | → `Student`                                                 |
| `session_deferred`  | ForeignKey    | → `Session` — the session they deferred from                |
| `session_returning` | ForeignKey    | → `Session`, nullable — expected return session             |
| `reason`            | CharField     | `financial` / `medical` / `personal` / `academic` / `other` |
| `reason_detail`     | TextField     | Nullable — free text from registrar                         |
| `status`            | CharField     | `active` / `reinstated` / `withdrawn`                       |
| `approved_by`       | ForeignKey    | → `User`, nullable                                          |
| `reinstated_at`     | DateTimeField | Nullable — set when student returns                         |
| `created_at`        | DateTimeField | Auto-set                                                    |
| `updated_at`        | DateTimeField | Auto-updated                                                |

**Constraints**

- `unique_together`: `(student, session_deferred)` — can't defer twice in the same session

---

## 👨‍👩‍👧 ParentGuardian

> Parent or guardian record for a student.
> Replaces the flat father/mother fields that previously lived on `Student`.

**Relationships**

- `student` → `Student` (ForeignKey)

| Field           | Type          | Notes                                 |
| --------------- | ------------- | ------------------------------------- |
| `record_id`     | UUIDField     | Primary key                           |
| `student`       | ForeignKey    | → `Student`                           |
| `relation`      | CharField     | `father` / `mother` / `guardian`      |
| `name`          | CharField     |                                       |
| `id_type`       | CharField     | `national` / `passport` / `birthCert` |
| `id_no`         | CharField     |                                       |
| `date_of_birth` | DateField     |                                       |
| `created_at`    | DateTimeField | Auto-set                              |
| `updated_at`    | DateTimeField | Auto-updated                          |

---

## 🆘 EmergencyContact

> Emergency contact record for a student.
> Replaces the two flat emergency contact blocks that previously lived on `Student`.

**Relationships**

- `student` → `Student` (ForeignKey)

| Field          | Type          | Notes                                           |
| -------------- | ------------- | ----------------------------------------------- |
| `record_id`    | UUIDField     | Primary key                                     |
| `student`      | ForeignKey    | → `Student`                                     |
| `name`         | CharField     |                                                 |
| `phone`        | CharField     |                                                 |
| `email`        | CharField     |                                                 |
| `relationship` | CharField     | e.g. `father`, `guardian`, `friend`, `neighbor` |
| `address`      | CharField     | Nullable                                        |
| `is_primary`   | BooleanField  | Default: `False`                                |
| `created_at`   | DateTimeField | Auto-set                                        |
| `updated_at`   | DateTimeField | Auto-updated                                    |

**Constraints**

- Only one contact per student may have `is_primary = True` (enforced via `UniqueConstraint`)

---

## 🧾 FeeStructure

> Defines what a class owes for a given session.
> Fees are itemised as a JSON breakdown.

**Relationships**

- `Tclass` → `Tclass` (ForeignKey)
- `session` → `Session` (ForeignKey)
- `studentfeeaccount_set` ← `StudentFeeAccount` (reverse FK)

| Field        | Type          | Notes                                                            |
| ------------ | ------------- | ---------------------------------------------------------------- |
| `record_id`  | UUIDField     | Primary key                                                      |
| `Tclass`     | ForeignKey    | → `Tclass`                                                       |
| `session`    | ForeignKey    | → `Session`                                                      |
| `breakdown`  | JSONField     | e.g. `{"tuition": 45000, "registration": 5000, "hostel": 12000}` |
| `created_at` | DateTimeField | Auto-set                                                         |
| `updated_at` | DateTimeField | Auto-updated                                                     |

**Constraints**

- `unique_together`: `(Tclass, session)`

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
- `fee_structure` → `FeeStructure` (ForeignKey) — session is derived from here
- `payments` ← `Payment` (reverse FK)
- `overdrafts` ← `OverDraft` (reverse FK)
- `credits` ← `OverDraft` (reverse FK via `applied_to`)

| Field           | Type          | Notes            |
| --------------- | ------------- | ---------------- |
| `record_id`     | UUIDField     | Primary key      |
| `student`       | ForeignKey    | → `Student`      |
| `fee_structure` | ForeignKey    | → `FeeStructure` |
| `amount_paid`   | DecimalField  | Default: `0`     |
| `created_at`    | DateTimeField | Auto-set         |
| `updated_at`    | DateTimeField | Auto-updated     |

**Constraints**

- `unique_together`: `(student, fee_structure)`

**Properties**

| Property         | Returns                                      |
| ---------------- | -------------------------------------------- |
| `amount_billed`  | `fee_structure.total_amount`                 |
| `balance`        | `amount_billed - amount_paid`                |
| `is_cleared`     | `True` if `balance <= 0`                     |
| `days_remaining` | Date 14 days before the session's `end_date` |

> ⚠️ **Note:** Session is no longer a direct FK on `StudentFeeAccount` — it is accessed via `fee_structure.session`.

---

## 💳 Payment

> An individual payment transaction against a student's fee account.
> Initiated immediately; confirmed later via webhook.

**Relationships**

- `account` → `StudentFeeAccount` (ForeignKey)
- `overdraft_set` ← `OverDraft` (reverse FK via `transaction`)

| Field             | Type          | Notes                                                       |
| ----------------- | ------------- | ----------------------------------------------------------- |
| `record_id`       | UUIDField     | Primary key                                                 |
| `account`         | ForeignKey    | → `StudentFeeAccount`                                       |
| `amount`          | DecimalField  |                                                             |
| `method`          | CharField     | `mpesa` / `bank` / `cash`                                   |
| `transaction_ref` | CharField     | Unique, nullable until confirmed                            |
| `status`          | CharField     | `pending` / `completed` / `failed` / `cancelled`            |
| `provider_ref`    | CharField     | Nullable — MerchantRequestID / CheckoutRequestID / bank ref |
| `phone_number`    | CharField     | Nullable — for M-Pesa STK push                              |
| `paid_at`         | DateTimeField | Auto-set on creation                                        |
| `initiated_at`    | DateTimeField | Auto-set on creation                                        |
| `created_at`      | DateTimeField | Auto-set                                                    |
| `updated_at`      | DateTimeField | Auto-updated                                                |

**Constraints**

- `unique_together`: `(transaction_ref, method)`
- Raises `ValidationError` on save if account is already cleared

**Methods**

| Method                                   | Description                                                                                                          |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `confirm(transaction_ref, provider_ref)` | Called by the webhook handler — marks `completed`, updates `amount_paid`, fires overdraft detection and notification |

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

**Methods**

| Method      | Description                                                                                 |
| ----------- | ------------------------------------------------------------------------------------------- |
| `process()` | Finds next session account and carries the amount forward; falls back to `refunded` if none |

---

## 📊 Result

> A CAT or exam score for a student in a specific curriculum entry.
> Linked via `Curriculum` rather than directly to `Course` and `Student`.

**Relationships**

- `curricula` → `Curriculum` (ForeignKey)
- `student` → `Student` (ForeignKey)

| Field        | Type          | Notes                                |
| ------------ | ------------- | ------------------------------------ |
| `record_id`  | UUIDField     | Primary key                          |
| `curricula`  | ForeignKey    | → `Curriculum`                       |
| `student`    | ForeignKey    | → `Student`                          |
| `type`       | CharField     | `C` = CAT, `E` = Exam                |
| `score`      | DecimalField  | Max 5 digits, 2 decimal places       |
| `title`      | CharField     | e.g. `CAT 1`, `End of Semester Exam` |
| `created_at` | DateTimeField | Auto-set                             |
| `updated_at` | DateTimeField | Auto-updated                         |

---

## 🕐 Timetable

> A single scheduled slot linked to a curriculum entry.
> Venue and time slot are distinct fields to support fixed-slot scheduling.

**Relationships**

- `curriculum` → `Curriculum` (ForeignKey)
- `venue` → `Venue` (ForeignKey)

| Field        | Type          | Notes                                          |
| ------------ | ------------- | ---------------------------------------------- |
| `record_id`  | UUIDField     | Primary key                                    |
| `curriculum` | ForeignKey    | → `Curriculum`                                 |
| `day`        | CharField     | `MON` / `TUE` / `WED` / `THU` / `FRI`          |
| `time_slot`  | CharField     | e.g. `08:00-10:00` — one of 6 predefined slots |
| `venue`      | ForeignKey    | → `Venue`                                      |
| `created_at` | DateTimeField | Auto-set                                       |
| `updated_at` | DateTimeField | Auto-updated                                   |

**Time Slots**

| Slot          | Label                    |
| ------------- | ------------------------ |
| `08:00-10:00` | 1st Slot (08:00 – 10:00) |
| `10:00-12:00` | 2nd Slot (10:00 – 12:00) |
| `12:00-13:00` | 3rd Slot (12:00 – 13:00) |
| `13:00-15:00` | 4th Slot (13:00 – 15:00) |
| `15:00-17:00` | 5th Slot (15:00 – 17:00) |
| `17:00-19:00` | 6th Slot (17:00 – 19:00) |

> ⚠️ **Note:** `Timetable` previously had direct FKs to `Session`, `Tclass`, `Course`, and `Lecturer`, plus separate `start_time` / `end_time` fields. These are now derived via the linked `Curriculum` entry. Clash detection constraints are pending implementation.

---

## 📅 ExamSession

> A single exam sitting for a curriculum entry — CAT, main, supplementary, or practical.

**Relationships**

- `curriculum` → `Curriculum` (ForeignKey)
- `venues` ← `ExamVenue` (reverse FK)
- `clashes_a` / `clashes_b` ← `ExamClash` (reverse FKs)

| Field        | Type          | Notes                                             |
| ------------ | ------------- | ------------------------------------------------- |
| `record_id`  | UUIDField     | Primary key                                       |
| `curriculum` | ForeignKey    | → `Curriculum`                                    |
| `exam_type`  | CharField     | `CAT` / `MAIN` / `SUPP` / `SPECIAL` / `PRACTICAL` |
| `date`       | DateField     |                                                   |
| `time_slot`  | CharField     | e.g. `08:00-11:00` — one of 5 predefined slots    |
| `created_at` | DateTimeField | Auto-set                                          |
| `updated_at` | DateTimeField | Auto-updated                                      |

**Constraints**

- `unique_together`: `(curriculum, exam_type)` — one exam type per curriculum entry

**Properties**

| Property     | Returns                            |
| ------------ | ---------------------------------- |
| `slot_start` | Start time string from `time_slot` |
| `slot_end`   | End time string from `time_slot`   |

**Class Methods**

| Method                                         | Description                                                                     |
| ---------------------------------------------- | ------------------------------------------------------------------------------- |
| `detect_clashes_for_student(student, session)` | Returns list of `(ExamSession, ExamSession)` clash pairs for a student          |
| `detect_all_clashes(session)`                  | Runs clash detection for all enrolled students and persists `ExamClash` records |

---

## 🏟️ ExamVenue

> Assigns a venue and invigilator to an exam session.

**Relationships**

- `exam_session` → `ExamSession` (ForeignKey)
- `venue` → `Venue` (ForeignKey)
- `invigilator` → `Lecturer` (ForeignKey)

| Field          | Type          | Notes           |
| -------------- | ------------- | --------------- |
| `record_id`    | UUIDField     | Primary key     |
| `exam_session` | ForeignKey    | → `ExamSession` |
| `venue`        | ForeignKey    | → `Venue`       |
| `invigilator`  | ForeignKey    | → `Lecturer`    |
| `created_at`   | DateTimeField | Auto-set        |
| `updated_at`   | DateTimeField | Auto-updated    |

**Constraints**

- `unique_together`: `(exam_session, venue)`
- `clean()` prevents an invigilator from being double-booked at the same date/time slot

---

## ⚡ ExamClash

> Records a detected exam time conflict for a student.
> Created by `ExamSession.detect_all_clashes()`.

**Relationships**

- `student` → `Student` (ForeignKey)
- `session_a` → `ExamSession` (ForeignKey)
- `session_b` → `ExamSession` (ForeignKey)

| Field        | Type          | Notes            |
| ------------ | ------------- | ---------------- |
| `record_id`  | UUIDField     | Primary key      |
| `student`    | ForeignKey    | → `Student`      |
| `session_a`  | ForeignKey    | → `ExamSession`  |
| `session_b`  | ForeignKey    | → `ExamSession`  |
| `resolved`   | BooleanField  | Default: `False` |
| `created_at` | DateTimeField | Auto-set         |
| `updated_at` | DateTimeField | Auto-updated     |

---

## 🪪 ExamCard

> Issued exam admit card for a student in a session.
> Only one active card per student per session is allowed.
> Reprinting creates a new record; old one is superseded.

**Relationships**

- `student` → `Student` (ForeignKey)
- `session` → `Session` (ForeignKey)

| Field             | Type          | Notes                                |
| ----------------- | ------------- | ------------------------------------ |
| `record_id`       | UUIDField     | Primary key                          |
| `student`         | ForeignKey    | → `Student`                          |
| `session`         | ForeignKey    | → `Session`                          |
| `serial_number`   | CharField     | Unique — format `UNI-YYYY-XXXX-XXXX` |
| `is_active`       | BooleanField  | Default: `True`                      |
| `issued_at`       | DateTimeField | Auto-set                             |
| `last_printed_at` | DateTimeField | Nullable — updated on each print     |
| `created_at`      | DateTimeField | Auto-set                             |
| `updated_at`      | DateTimeField | Auto-updated                         |

**Constraints**

- `unique_together`: `(student, session, is_active)` — one active card per student per session

**Class Methods / Properties**

| Name                | Description                                                                      |
| ------------------- | -------------------------------------------------------------------------------- |
| `generate_serial()` | Generates a unique `UNI-YYYY-XXXX-XXXX` serial number                            |
| `qr_payload`        | `"{registration_number}\|{serial_number}\|{session}"` — encoded into the card QR |

---

## 🏨 Hostel

> A physical hostel building on campus.

**Relationships**

- `warden` → `HostelWarden` (ForeignKey, nullable)
- `rooms` ← `Room` (reverse FK)

| Field        | Type          | Notes                      |
| ------------ | ------------- | -------------------------- |
| `record_id`  | UUIDField     | Primary key                |
| `name`       | CharField     |                            |
| `gender`     | CharField     | `M` / `F` / `mixed`        |
| `warden`     | ForeignKey    | → `HostelWarden`, nullable |
| `created_at` | DateTimeField | Auto-set                   |
| `updated_at` | DateTimeField | Auto-updated               |

**Properties**

| Property         | Returns                                    |
| ---------------- | ------------------------------------------ |
| `total_capacity` | Sum of `capacity` across all rooms         |
| `occupied_beds`  | Count of active `HostelAllocation` records |
| `available_beds` | `total_capacity - occupied_beds`           |

---

## 🚪 Room

> An individual room within a hostel.

**Relationships**

- `hostel` → `Hostel` (ForeignKey)
- `allocations` ← `HostelAllocation` (reverse FK)

| Field                | Type                 | Notes                                      |
| -------------------- | -------------------- | ------------------------------------------ |
| `record_id`          | UUIDField            | Primary key                                |
| `hostel`             | ForeignKey           | → `Hostel`                                 |
| `room_number`        | CharField            |                                            |
| `room_type`          | CharField            | `single` / `double` / `triple` / `ensuite` |
| `capacity`           | IntegerField         | Default: `2`                               |
| `floor`              | IntegerField         | Default: `1`                               |
| `price_per_semester` | PositiveIntegerField | KES                                        |
| `created_at`         | DateTimeField        | Auto-set                                   |
| `updated_at`         | DateTimeField        | Auto-updated                               |

**Constraints**

- `unique_together`: `(hostel, room_number)`

**Properties**

| Property    | Returns                                                   |
| ----------- | --------------------------------------------------------- |
| `is_full`   | `True` if active allocations ≥ `capacity`                 |
| `occupants` | Active `HostelAllocation` QuerySet with student/user data |

---

## 🛏️ HostelAllocation

> Links a student to a specific room for a specific session.

**Relationships**

- `student` → `Student` (ForeignKey)
- `room` → `Room` (ForeignKey)
- `session` → `Session` (ForeignKey)

| Field          | Type          | Notes           |
| -------------- | ------------- | --------------- |
| `record_id`    | UUIDField     | Primary key     |
| `student`      | ForeignKey    | → `Student`     |
| `room`         | ForeignKey    | → `Room`        |
| `session`      | ForeignKey    | → `Session`     |
| `allocated_at` | DateTimeField | Auto-set        |
| `is_active`    | BooleanField  | Default: `True` |
| `move_in_date` | DateField     | Nullable        |
| `notes`        | TextField     | Blank allowed   |
| `created_at`   | DateTimeField | Auto-set        |
| `updated_at`   | DateTimeField | Auto-updated    |

**Constraints**

- `unique_together`: `(student, session)` — one room per student per session
- `clean()` validates room capacity and gender compatibility

---

## 🔄 ERPSyncLog

> Logs each outbound sync attempt to the external ERP system.
> Uses a string reference instead of a GenericForeignKey to keep it dependency-free.

| Field              | Type          | Notes                                                       |
| ------------------ | ------------- | ----------------------------------------------------------- |
| `record_id`        | UUIDField     | Primary key                                                 |
| `content_type_str` | CharField     | e.g. `"Payment:uuid"` or `"Enrollment:uuid"`                |
| `event`            | CharField     | e.g. `"payment_confirmed"`                                  |
| `handler`          | CharField     | The handler function or class that processed this event     |
| `attempt`          | IntegerField  | Default: `1` — incremented on retry                         |
| `status`           | CharField     | `attempting` / `success` / `failed` / `error` / `exhausted` |
| `message`          | TextField     | Blank allowed — error message or notes                      |
| `external_ref`     | CharField     | Nullable — ID returned from ERP on success                  |
| `raw_response`     | JSONField     | Nullable — full ERP response body                           |
| `created_at`       | DateTimeField | Auto-set                                                    |
| `updated_at`       | DateTimeField | Auto-updated                                                |

---

## ⭐ CourseEvaluation

> Student rating of a course delivered within a curriculum entry.

**Relationships**

- `curriculum` → `Curriculum` (ForeignKey)

| Field        | Type          | Notes          |
| ------------ | ------------- | -------------- |
| `record_id`  | UUIDField     | Primary key    |
| `curriculum` | ForeignKey    | → `Curriculum` |
| `rating`     | IntegerField  | Default: `0`   |
| `comments`   | TextField     | Nullable       |
| `created_at` | DateTimeField | Auto-set       |
| `updated_at` | DateTimeField | Auto-updated   |

---

## ⭐ LecturerEvaluation

> Student rating of a specific lecturer within a curriculum entry.

**Relationships**

- `curriculum` → `Curriculum` (ForeignKey)
- `lecturer` → `Lecturer` (ForeignKey)

| Field        | Type          | Notes          |
| ------------ | ------------- | -------------- |
| `record_id`  | UUIDField     | Primary key    |
| `curriculum` | ForeignKey    | → `Curriculum` |
| `lecturer`   | ForeignKey    | → `Lecturer`   |
| `rating`     | IntegerField  | Default: `0`   |
| `comments`   | TextField     | Nullable       |
| `created_at` | DateTimeField | Auto-set       |
| `updated_at` | DateTimeField | Auto-updated   |

---

## ⭐ HostelEvaluation

> Student rating of their hostel allocation at the end of a session.
> One evaluation per allocation — covers six categories plus an overall score.

**Relationships**

- `allocation` → `HostelAllocation` (OneToOne)

| Field                 | Type          | Notes                |
| --------------------- | ------------- | -------------------- |
| `record_id`           | UUIDField     | Primary key          |
| `allocation`          | OneToOneField | → `HostelAllocation` |
| `cleanliness_rating`  | IntegerField  | 1–5                  |
| `security_rating`     | IntegerField  | 1–5                  |
| `water_supply_rating` | IntegerField  | 1–5                  |
| `electricity_rating`  | IntegerField  | 1–5                  |
| `noise_levels_rating` | IntegerField  | 1–5                  |
| `maintenance_rating`  | IntegerField  | 1–5                  |
| `rating`              | IntegerField  | 1–5 — overall score  |
| `comments`            | TextField     | Blank allowed        |
| `created_at`          | DateTimeField | Auto-set             |
| `updated_at`          | DateTimeField | Auto-updated         |

---

## 📰 NewsItem

> Lightweight card-data store for news synced from an external CMS.
> Never stores full article content — just enough to render a card.
> `source_url` redirects to the full article.

| Field          | Type          | Notes                     |
| -------------- | ------------- | ------------------------- |
| `record_id`    | UUIDField     | Primary key               |
| `external_id`  | CharField     | Unique — CMS identifier   |
| `title`        | CharField     |                           |
| `summary`      | TextField     |                           |
| `category`     | CharField     | e.g. `Academic`, `Sports` |
| `date`         | DateField     |                           |
| `source_url`   | URLField      | Link to full article      |
| `source_name`  | CharField     |                           |
| `badge`        | CharField     | Nullable — label chip     |
| `thumbnail`    | URLField      | Nullable                  |
| `is_published` | BooleanField  | Default: `True`           |
| `created_at`   | DateTimeField | Auto-set                  |
| `updated_at`   | DateTimeField | Auto-updated              |

---

## 📅 EventItem

> Campus event card with location, online support, and RSVP tracking.

| Field           | Type          | Notes                                  |
| --------------- | ------------- | -------------------------------------- |
| `record_id`     | UUIDField     | Primary key                            |
| `external_id`   | CharField     | Unique — external identifier           |
| `title`         | CharField     |                                        |
| `description`   | TextField     |                                        |
| `category`      | CharField     | e.g. `Academic`, `Sports`, `Social`    |
| `date`          | DateField     |                                        |
| `start_time`    | TimeField     | Nullable                               |
| `end_time`      | TimeField     | Nullable                               |
| `location`      | CharField     | Nullable                               |
| `is_online`     | BooleanField  | Default: `False`                       |
| `meeting_url`   | URLField      | Nullable — Zoom/Teams link             |
| `badge`         | CharField     | Nullable — label chip                  |
| `thumbnail`     | URLField      | Nullable                               |
| `source_url`    | URLField      | Nullable — full details / registration |
| `source_name`   | CharField     |                                        |
| `rsvp_url`      | URLField      | Nullable — external registration form  |
| `rsvp_deadline` | DateField     | Nullable                               |
| `is_published`  | BooleanField  | Default: `True`                        |
| `created_at`    | DateTimeField | Auto-set                               |
| `updated_at`    | DateTimeField | Auto-updated                           |

**Properties**

| Property       | Returns                                                 |
| -------------- | ------------------------------------------------------- |
| `status`       | `upcoming` / `ongoing` / `past` — based on today's date |
| `is_rsvp_open` | `True` if RSVP URL exists and deadline hasn't passed    |

---

> 🔗 Back to [Project Index](../README.md)
> 🔗 Back to [Documentation Index](./README.md)
> 🔗 See the [ER Diagram](er-diagram.md) for a visual representation of these relationships
> 🔗 See the models source files for the concrete implementation
