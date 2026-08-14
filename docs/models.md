# 📋 Models Reference

> Field-by-field breakdown of every model in the system.
> Use this as your data dictionary — no need to dig through `models.py`.
> P.s all models are just guides you are free to mess with them as much as you want

---

## 📑 Contents

| Model                                                         | Description                                                       |
| ------------------------------------------------------------- | ----------------------------------------------------------------- |
| [👤 User](#-user)                                             | Base login account for all system users                           |
| [🎓 Student](#-student)                                       | Student profile with academic and personal info                   |
| [👨‍🏫 Lecturer](#-lecturer)                                     | Staff member who teaches courses                                  |
| [🏢 DeptAdmin](#-deptadmin)                                   | Administrator scoped to a department                              |
| [🏫 SchoolAdmin](#-schooladmin)                               | Administrator scoped to a school                                  |
| [🏛️ InstitutionAdmin](#-institutionadmin)                     | Top-level system administrator                                    |
| [💻 ItStaff](#-itstaff)                                       | IT staff member                                                   |
| [💰 FinanceStaff](#-financestaff)                             | Finance staff member                                              |
| [🏨 HostelWarden](#-hostelwarden)                             | Manages a hostel building                                         |
| [🏫 School](#-school)                                         | A faculty or school within the institution                        |
| [🏢 Department](#-department)                                 | A department within a school                                      |
| [📖 Programme](#-programme)                                   | A degree programme within a department                            |
| [🏛️ Tclass](#-tclass)                                         | A class cohort within a programme                                 |
| [📚 Course](#-course)                                         | An individual unit or subject                                     |
| [📋 Curriculum](#-curriculum)                                 | A course offered to a class in a session                          |
| [🔗 CommonUnitCurriculum](#-commonunitcurriculum)             | Proxy — common units shared across multiple classes               |
| [📝 Enrollment](#-enrollment)                                 | A student's enrollment request for a curriculum                   |
| [🗓️ Session](#-session)                                       | An academic semester                                              |
| [✅ Reporting](#-reporting)                                   | Student check-in record per session                               |
| [⏸️ Deferment](#-deferment)                                   | A single deferment event for a student                            |
| [👨‍👩‍👧 ParentGuardian](#-parentguardian)                         | Parent or guardian record for a student                           |
| [🆘 EmergencyContact](#-emergencycontact)                     | Emergency contact record for a student                            |
| [🧾 FeeStructure](#-feestructure)                             | Fee breakdown for a class per session                             |
| [💰 StudentFeeAccount](#-studentfeeaccount)                   | Per-student financial ledger                                      |
| [💳 Payment](#-payment)                                       | Individual payment transaction                                    |
| [📊 Result](#-result)                                         | CAT or exam score per student per curriculum entry                |
| [🕐 Timetable](#-timetable)                                   | Class schedule slot linked to a curriculum entry                  |
| [🏟️ Venue](#-venue)                                           | A physical room, hall, or lab used for classes/exams              |
| [📅 ExamSession](#-examsession)                               | A single exam sitting for a curriculum entry                      |
| [🏟️ ExamVenue](#-examvenue)                                   | Venue and invigilator assignment for an exam                      |
| [⚡ ExamClash](#-examclash)                                   | Detected exam time conflict for a student                         |
| [🪪 ExamCard](#-examcard)                                     | Issued exam admit card for a student in a session                 |
| [🏨 Hostel](#-hostel)                                         | A physical hostel building on campus                              |
| [🚪 Room](#-room)                                             | An individual room within a hostel                                |
| [🛏️ HostelAllocation](#-hostelallocation)                     | Links a student to a room for a session                           |
| [🔄 ERPSyncLog](#-erpsynclog)                                 | Outbound ERP sync attempt log                                     |
| [⭐ CourseEvaluation](#-courseevaluation)                     | Student rating of a course                                        |
| [⭐ LecturerEvaluation](#-lecturerevaluation)                 | Student rating of a lecturer                                      |
| [⭐ HostelEvaluation](#-hostelevaluation)                     | Student rating of their hostel allocation                         |
| [📰 NewsItem](#-newsitem)                                     | News card synced from external CMS                                |
| [📅 EventItem](#-eventitem)                                   | Campus event card with RSVP support                               |
| [🔧 LecturerAssignment](#-lecturerassignment)                 | _(optional)_ Through-table for `Curriculum.professor`             |
| [🥽 LabTechnicalStaff](#-labtechnicalstaff)                   | Lab technician/manager, scoped to a department                    |
| [🩺 MedicalStaff](#-medicalstaff)                             | Campus clinic doctor/nurse/pharmacist                             |
| [📚 LibraryStaff](#-librarystaff)                             | University librarian / library assistant                          |
| [🎫 Application](#-application)                               | A prospective student's admission application                     |
| [📎 ApplicationDocument](#-applicationdocument)               | Supporting document attached to an application                    |
| [🔁 TransferCreditEvaluation](#-transfercreditevaluation)     | External course credit review for an applicant                    |
| [🪪 IDCard](#-idcard)                                         | Issued student ID card                                            |
| [🏥 StudentMedicalProfile](#-studentmedicalprofile)           | Core health registry for a student                                |
| [🩹 ClinicEncounter](#-clinicencounter)                       | Campus clinic visit log                                           |
| [📢 Complaint](#-complaint)                                   | Formal student grievance filed with the registrar                 |
| [📎 ComplaintDocument](#-complaintdocument)                   | Evidence/document attached to a complaint                         |
| [📈 ComplaintEscalationHistory](#-complaintescalationhistory) | Tracks a complaint's move up the admin chain                      |
| [🔀 StatusChangeRequest](#-statuschangerequest)               | Leave of absence / withdrawal / readmission request               |
| [🧮 DegreeAudit](#-degreeaudit)                               | Running check of a student's credit/GPA graduation eligibility    |
| [🎓 Graduation](#-graduation)                                 | A student's graduation candidacy record                           |
| [📜 Diploma](#-diploma)                                       | The physical/digital degree certificate issued                    |
| [🎉 Convocation](#-convocation)                               | A graduation ceremony event                                       |
| [🏘️ HostelListing](#-hostellisting)                           | Off-campus hostel guide entry (not on-campus allocation)          |
| [🏗️ Building](#-building)                                     | A physical structure on campus containing venues                  |
| [📆 DailyClassExecution](#-dailyclassexecution)               | Actual day-to-day execution/attendance log for a timetable slot   |
| [🧑‍⚖️ ExamInvigilatorAssignment](#-examinvigilatorassignment)   | _(optional)_ Through-table for multi-invigilator venues           |
| [🏛️ Club](#-club)                                             | A student club or society                                         |
| [🧑‍🏫 ClubPatron](#-clubpatron)                                 | Faculty advisor overseeing a club                                 |
| [📣 ClubRecruitmentDrive](#-clubrecruitmentdrive)             | A membership recruitment window for a club                        |
| [🪪 ClubMembership](#-clubmembership)                         | Links a student to a club they've joined                          |
| [👑 ClubLeadershipPosition](#-clubleadershipposition)         | An executive role held within a club membership                   |
| [📅 ClubEvent](#-clubevent)                                   | A club-organised event                                            |
| [✅ ClubEventAttendance](#-clubeventattendance)               | Attendance record for a club event                                |
| [📊 ClubActivityReport](#-clubactivityreport)                 | Periodic activity summary submitted by a club                     |
| [💰 ClubBudget](#-clubbudget)                                 | A club's allocated budget for a session                           |
| [🧾 ClubTransaction](#-clubtransaction)                       | Individual income/expense entry against a club budget             |
| [🏛️ CouncilTerm](#-councilterm)                               | A single term of the student governing body                       |
| [🪑 CouncilPosition](#-councilposition)                       | An occupied/vacant seat within a council term                     |
| [🗳️ Election](#-election)                                     | A student council election cycle                                  |
| [📋 ElectionPosition](#-electionposition)                     | A specific seat being contested in an election                    |
| [🙋 Candidate](#-candidate)                                   | A student running for an election position                        |
| [✔️ Vote](#-vote)                                             | A single cast ballot                                              |
| [📜 CouncilProposal](#-councilproposal)                       | A motion tabled by a council position                             |
| [✍️ ProposalSupport](#-proposalsupport)                       | A student's endorsement signature on a proposal                   |
| [📅 CouncilMeeting](#-councilmeeting)                         | A scheduled council meeting                                       |
| [✅ CouncilMeetingAttendance](#-councilmeetingattendance)     | Attendance record for a council meeting                           |
| [🆘 Grievance](#-grievance)                                   | A welfare grievance submitted through student governance          |
| [🔄 GrievanceUpdate](#-grievanceupdate)                       | A status update/log entry on a grievance                          |
| [📜 Accreditation](#-accreditation)                           | A regulatory accreditation held by a programme or the institution |
| [📎 AccreditationDocument](#-accreditationdocument)           | Evidence document supporting an accreditation                     |
| [🗓️ RegistrationWindow](#-registrationwindow)                 | Generic open/close window for any registration-type activity      |
| [📄 RegulatoryReport](#-regulatoryreport)                     | A statutory report submission tracked against a regulator         |
| [📎 RegulatoryReportDocument](#-regulatoryreportdocument)     | Evidence document supporting a regulatory report                  |
| [🗓️ ComplianceCalendarEvent](#-compliancecalendarevent)       | Denormalized deadline feed across accreditation/reports/windows   |
| [📣 Announcement](#-announcement)                             | A lecturer/staff post to a class or department                    |
| [📎 AnnouncementDocument](#-announcementdocument)             | File attached to an announcement                                  |

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

| Field          | Type      | Notes |
| -------------- | --------- | ----- |
| `domicile`     | CharField |       |
| `county`       | CharField |       |
| `sub_county`   | CharField |       |
| `constituency` | CharField |       |
| `division`     | CharField |       |
| `location`     | CharField |       |
| `home_address` | CharField |       |

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

**Lifecycle proxy models**

`ResidentStudent`, `DeferredStudent`, and `GraduatedStudent` are proxy models
over `Student` — no new fields, just filtered admin views (`stay='resident'`,
`deferred=True`, and `class_entered.graduated` set, respectively). Useful for
scoping admin panels and querysets without adding real tables.

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

> 🔧 **Optional extension:** `professor` is a plain ManyToMany today. If you
> need to track which lecturer is primary vs. assisting, or per-lecturer
> workload hours, route it through [`LecturerAssignment`](#-lecturerassignment)
> instead (`professor = models.ManyToManyField('Lecturer', through='LecturerAssignment')`).

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
> There is only ever **one active session** institution-wide.[for now]

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

| Method                                   | Description                                                                                  |
| ---------------------------------------- | -------------------------------------------------------------------------------------------- |
| `confirm(transaction_ref, provider_ref)` | Called by the webhook handler — marks `completed`, updates `amount_paid`, fires notification |

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
| `venue`      | ForeignKey    | → [`Venue`](#-venue)                           |
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

**Constraints**

- `unique_together`: `(curriculum, day, time_slot)` — a class can't be double-booked into two slots at once
- `unique_together`: `(venue, day, time_slot)` — a venue can't be double-booked

> ⚠️ **Note:** `Timetable` previously had direct FKs to `Session`, `Tclass`, `Course`, and `Lecturer`, plus separate `start_time` / `end_time` fields. These are now derived via the linked `Curriculum` entry.

---

## 🏟️ Venue

> A physical room, lecture hall, lab, or auditorium used for classes and exams.
> Shared infrastructure — referenced by both `Timetable` and `ExamVenue`.

**Relationships**

- `building` → `Building` (ForeignKey)
- `timetable_slots` ← `Timetable` (reverse FK)
- `exam_venues` ← `ExamVenue` (reverse FK)

| Field           | Type          | Notes                                                    |
| --------------- | ------------- | -------------------------------------------------------- |
| `record_id`     | UUIDField     | Primary key                                              |
| `venue_name`    | CharField     | Unique — e.g. `SCI 101`, `Auditorium A`                  |
| `building`      | ForeignKey    | → [`Building`](#-building)                               |
| `capacity`      | IntegerField  | Maximum sitting capacity                                 |
| `floor`         | IntegerField  | Default: `0` (ground floor)                              |
| `has_computers` | BooleanField  | Default: `False` — needed to host practical/lab sessions |
| `is_active`     | BooleanField  | Default: `True`                                          |
| `created_at`    | DateTimeField | Auto-set                                                 |
| `updated_at`    | DateTimeField | Auto-updated                                             |

> ⚠️ **Note:** `building` is now a proper FK to [`Building`](#-building)
> instead of a free-text field, now that `Building` is documented below.

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
- `venue` → [`Venue`](#-venue) (ForeignKey)
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

> 🔧 **Optional extension:** `invigilator` is a single ForeignKey today — one
> invigilator per venue. If a hall needs a squad (chief + assistants), route
> it through [`ExamInvigilatorAssignment`](#-examinvigilatorassignment)
> instead (`invigilators = models.ManyToManyField('Lecturer', through='ExamInvigilatorAssignment')`).

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

> ℹ️ **A note on `Historical*` tables.** Several models in the wider system
> (`Deferment`, `Reporting`, `Complaint`, `Enrollment`, `Curriculum`,
> `StudentFeeAccount`, `Payment`, and the new `Club`/`Council`/`Candidate`/
> `Grievance` models below) use `django-simple-history`'s
> `history = HistoricalRecords()` field. Each one silently generates a
> matching `Historical<ModelName>` table (`HistoricalDeferment`,
> `HistoricalComplaint`, etc.) that snapshots every field on every save —
> automatic, not something you hand-model. They aren't documented as
> individual sections here; if you need to query change history, it's
> `Model.history.all()` / `instance.history.all()`.

---

## 🔧 LecturerAssignment

> _(Optional)_ Through-table for `Curriculum.professor`, if you need more
> than a flat list of lecturers per curriculum entry — see the note under
> [Curriculum](#-curriculum).

**Relationships**

- `curriculum` → `Curriculum` (ForeignKey)
- `lecturer` → `Lecturer` (ForeignKey)

| Field                      | Type                 | Notes                                                   |
| -------------------------- | -------------------- | ------------------------------------------------------- |
| `record_id`                | UUIDField            | Primary key                                             |
| `curriculum`               | ForeignKey           | → `Curriculum`                                          |
| `lecturer`                 | ForeignKey           | → `Lecturer`                                            |
| `is_primary`               | BooleanField         | Default: `True` — main instructor who grades exams      |
| `allocated_workload_hours` | PositiveIntegerField | Default: `3` — weekly contact hours for this assignment |
| `status`                   | CharField            | `Draft` / `Assigned` / `Confirmed` / `Substituted`      |
| `date_assigned`            | DateTimeField        | Auto-set on creation                                    |

**Constraints**

- `unique_together`: `(curriculum, lecturer)`
- Only one `is_primary=True` assignment allowed per curriculum entry
- A lecturer's summed `allocated_workload_hours` across a session shouldn't exceed a sane weekly cap (enforce in `clean()`)

---

## 🥽 LabTechnicalStaff

> Handles laboratory technicians for engineering, chemistry, computing, etc.

**Relationships**

- `user` → `User` (OneToOne)
- `department` → `Department` (ForeignKey)

| Field          | Type          | Notes                                          |
| -------------- | ------------- | ---------------------------------------------- |
| `record_id`    | UUIDField     | Primary key                                    |
| `user`         | OneToOneField | → `User`                                       |
| `staff_number` | CharField     | Unique                                         |
| `department`   | ForeignKey    | → `Department`                                 |
| `role`         | CharField     | `Laboratory Technician` / `Laboratory Manager` |
| `created_at`   | DateTimeField | Auto-set                                       |
| `updated_at`   | DateTimeField | Auto-updated                                   |

---

## 🩺 MedicalStaff

> Staff located inside the campus health unit/clinic.

**Relationships**

- `user` → `User` (OneToOne)
- `clinic_visits` ← `ClinicEncounter` (reverse FK, as `attending_clinician`)

| Field          | Type          | Notes                                                   |
| -------------- | ------------- | ------------------------------------------------------- |
| `record_id`    | UUIDField     | Primary key                                             |
| `user`         | OneToOneField | → `User`                                                |
| `staff_number` | CharField     | Unique                                                  |
| `role`         | CharField     | `Campus Medical Doctor` / `Campus Nurse` / `Pharmacist` |
| `created_at`   | DateTimeField | Auto-set                                                |
| `updated_at`   | DateTimeField | Auto-updated                                            |

---

## 📚 LibraryStaff

> Manages library systems; nullable school scope for staff at the main/central library.

**Relationships**

- `user` → `User` (OneToOne)
- `school` → `School` (ForeignKey, nullable)

| Field          | Type          | Notes                                                |
| -------------- | ------------- | ---------------------------------------------------- |
| `record_id`    | UUIDField     | Primary key                                          |
| `user`         | OneToOneField | → `User`                                             |
| `staff_number` | CharField     | Unique                                               |
| `school`       | ForeignKey    | → `School`, nullable — blank if central/main library |
| `role`         | CharField     | `University Librarian` / `Library Assistant`         |
| `created_at`   | DateTimeField | Auto-set                                             |
| `updated_at`   | DateTimeField | Auto-updated                                         |

> ⚠️ **Overlap note:** `LabTechnicalStaff`, `MedicalStaff`, and `LibraryStaff`
> join the existing flat staff models (`Lecturer`, `DeptAdmin`, `SchoolAdmin`,
> `InstitutionAdmin`, `ItStaff`, `FinanceStaff`, `HostelWarden`) as more
> independent, single-purpose tables rather than subclasses of a shared
> `StaffProfile`. If you later introduce a shared abstract base (staff-number
> generation, a unified directory search, contract tracking), all eight of
> these are the ones that would inherit from it. Separately: the broader
> ERP concept of `AdministrativeStaff` (a single role-based table covering
> VC/DVC/Registrar/dept-admin/school-admin/institution-admin) overlaps with
> this project's existing `DeptAdmin`/`SchoolAdmin`/`InstitutionAdmin` — treat
> those three as this project's answer to that concept rather than adding a
> fourth, redundant table.

---

## 🎫 Application

> A prospective student's admission application — the pipeline stage before a `Student` record exists.

**Relationships**

- `program_applied` → `Programme` (ForeignKey)
- `term_applied` → `Session` (ForeignKey)
- `reviewed_by` → `User` (ForeignKey, nullable)
- `documents` ← `ApplicationDocument` (reverse FK)
- `transfer_credits` ← `TransferCreditEvaluation` (reverse FK)
- Creates a `Student` record once `status = enrolled`

| Field             | Type          | Notes                                                                                |
| ----------------- | ------------- | ------------------------------------------------------------------------------------ |
| `record_id`       | UUIDField     | Primary key                                                                          |
| `applicant_name`  | CharField     |                                                                                      |
| `email`           | EmailField    |                                                                                      |
| `phone`           | CharField     | Blank allowed                                                                        |
| `program_applied` | ForeignKey    | → `Programme`                                                                        |
| `term_applied`    | ForeignKey    | → `Session`                                                                          |
| `status`          | CharField     | `submitted` / `under_review` / `docs_pending` / `accepted` / `rejected` / `enrolled` |
| `submitted_on`    | DateTimeField | Auto-set on creation                                                                 |
| `reviewed_by`     | ForeignKey    | → `User`, nullable                                                                   |

---

## 📎 ApplicationDocument

> Supporting document uploaded alongside an application.

**Relationships**

- `application` → `Application` (ForeignKey)
- `verified_by` → `User` (ForeignKey, nullable)

| Field         | Type         | Notes                                                            |
| ------------- | ------------ | ---------------------------------------------------------------- |
| `record_id`   | UUIDField    | Primary key                                                      |
| `application` | ForeignKey   | → `Application`                                                  |
| `doc_type`    | CharField    | `transcript` / `id_proof` / `recommendation` / `essay` / `other` |
| `file`        | FileField    | Uploads to `admissions/documents/`                               |
| `verified`    | BooleanField | Default: `False`                                                 |
| `verified_by` | ForeignKey   | → `User`, nullable                                               |

---

## 🔁 TransferCreditEvaluation

> Reviews an external course for credit-transfer equivalency against the internal catalog.

**Relationships**

- `application` → `Application` (ForeignKey)
- `equivalent_course` → `Course` (ForeignKey, nullable)
- `evaluated_by` → `User` (ForeignKey, nullable)

| Field                  | Type                      | Notes                |
| ---------------------- | ------------------------- | -------------------- |
| `record_id`            | UUIDField                 | Primary key          |
| `application`          | ForeignKey                | → `Application`      |
| `external_course_name` | CharField                 |                      |
| `external_institution` | CharField                 |                      |
| `equivalent_course`    | ForeignKey                | → `Course`, nullable |
| `credits_awarded`      | PositiveSmallIntegerField | Default: `0`         |
| `evaluated_by`         | ForeignKey                | → `User`, nullable   |
| `approved`             | BooleanField              | Default: `False`     |

---

## 🪪 IDCard

> Issued physical/digital student ID card.

**Relationships**

- `student` → `Student` (OneToOne)

| Field         | Type          | Notes                |
| ------------- | ------------- | -------------------- |
| `record_id`   | UUIDField     | Primary key          |
| `student`     | OneToOneField | → `Student`          |
| `card_number` | CharField     | Unique               |
| `issued_date` | DateField     | Auto-set on creation |
| `expiry_date` | DateField     |                      |
| `is_active`   | BooleanField  | Default: `True`      |
| `photo`       | ImageField    | Nullable             |

---

## 🏥 StudentMedicalProfile

> Core health registry for a student — loaded once at admission, updated for chronic/long-term conditions.

**Relationships**

- `student` → `Student` (OneToOne, primary key)
- `clinic_visits` ← `ClinicEncounter` (reverse FK)

| Field                            | Type          | Notes                                                                          |
| -------------------------------- | ------------- | ------------------------------------------------------------------------------ |
| `student`                        | OneToOneField | → `Student` — primary key                                                      |
| `blood_group`                    | CharField     | `A+`/`A-`/`B+`/`B-`/`AB+`/`AB-`/`O+`/`O-`/`Unknown`                            |
| `known_allergies`                | TextField     | Default: `"None Registered"`                                                   |
| `chronic_conditions`             | TextField     | Default: `"None"`                                                              |
| `requires_special_accommodation` | BooleanField  | Default: `False` — e.g. ground-floor hostel, exam time extension               |
| `accommodation_notes`            | TextField     | Nullable — required if the flag above is `True`                                |
| `odpc_consent_signed`            | BooleanField  | Default: `False` — required before processing under Kenyan data-protection law |
| `consent_date`                   | DateTimeField | Nullable                                                                       |

---

## 🩹 ClinicEncounter

> A single visit to the campus clinic or sick bay.

**Relationships**

- `student` → `Student` (ForeignKey)
- `attending_clinician` → `User` (ForeignKey, staff)

| Field                         | Type                 | Notes                                                              |
| ----------------------------- | -------------------- | ------------------------------------------------------------------ |
| `encounter_id`                | AutoField            | Primary key (integer, not UUID)                                    |
| `student`                     | ForeignKey           | → `Student`                                                        |
| `attending_clinician`         | ForeignKey           | → `User`, must be staff                                            |
| `date_of_visit`               | DateTimeField        | Auto-set on creation                                               |
| `encounter_type`              | CharField            | `Freshman_Check` / `Outpatient` / `Emergency` / `Sports_Clearance` |
| `symptoms_reported`           | TextField            |                                                                    |
| `diagnosis`                   | CharField            |                                                                    |
| `treatment_plan`              | TextField            | Prescribed drugs, rest orders, referral details                    |
| `recommended_sick_leave_days` | PositiveIntegerField | Default: `0` — feeds into attendance/exam clearance exemptions     |
| `data_classification`         | CharField            | `Standard` / `Restricted` (Dean-of-Students review only)           |

---

## 📢 Complaint

> Formal student grievance filed through the registrar/administrative channel.
> Distinct from [`Grievance`](#-grievance), which routes through student
> governance/welfare — see the note at the end of that section.

**Relationships**

- `student` → `Student` (ForeignKey)
- `assigned_staff` → `User` (ForeignKey, nullable)
- `documents` ← `ComplaintDocument` (reverse FK)
- `escalation_history` ← `ComplaintEscalationHistory` (reverse FK)

| Field                     | Type          | Notes                                                                              |
| ------------------------- | ------------- | ---------------------------------------------------------------------------------- |
| `record_id`               | UUIDField     | Primary key                                                                        |
| `student`                 | ForeignKey    | → `Student`                                                                        |
| `category`                | CharField     | `Academic` / `Harassment` / `Administrative` / `Facilities` / `Catering` / `Other` |
| `priority`                | CharField     | `Low` / `Medium` / `High` / `Critical`                                             |
| `status`                  | CharField     | `Open` / `In_Progress` / `Escalated` / `Resolved`                                  |
| `subject`                 | CharField     | Brief headline                                                                     |
| `description`             | TextField     |                                                                                    |
| `assigned_staff`          | ForeignKey    | → `User`, nullable                                                                 |
| `resolution_remarks`      | TextField     | Nullable — required before `status` can be `Resolved`                              |
| `date_opened`             | DateTimeField | Auto-set on creation                                                               |
| `date_resolved`           | DateTimeField | Nullable — auto-set when `status` becomes `Resolved`                               |
| `is_anonymous_to_faculty` | BooleanField  | Default: `False` — hides identity from lecturers, visible only to Dean of Students |

**Notes**

- `category = Harassment` auto-escalates `priority` to `Critical` on save.
- `status = Resolved` requires `resolution_remarks` to be set.

---

## 📎 ComplaintDocument

> Evidence uploaded alongside a complaint — by the student or by the resolving officer.

**Relationships**

- `complaint` → `Complaint` (ForeignKey)
- `uploaded_by_user` → `User` (ForeignKey)

| Field              | Type          | Notes                                                   |
| ------------------ | ------------- | ------------------------------------------------------- |
| `record_id`        | UUIDField     | Primary key                                             |
| `complaint`        | ForeignKey    | → `Complaint`                                           |
| `file`             | FileField     | Uploads to `complaints/%Y/%m/`                          |
| `original_name`    | CharField     | Auto-preserved from upload                              |
| `uploaded_by_role` | CharField     | `student` (evidence) / `officer` (investigation report) |
| `uploaded_by_user` | ForeignKey    | → `User`                                                |
| `uploaded_at`      | DateTimeField | Auto-set                                                |

---

## 📈 ComplaintEscalationHistory

> Tracks a complaint's sequential movement up the administrative hierarchy.

**Relationships**

- `complaint` → `Complaint` (ForeignKey)
- `escalated_by` → `User` (ForeignKey)

| Field                   | Type          | Notes                                                        |
| ----------------------- | ------------- | ------------------------------------------------------------ |
| `id`                    | AutoField     | Primary key (integer, not UUID)                              |
| `complaint`             | ForeignKey    | → `Complaint`                                                |
| `escalated_from_level`  | CharField     | `Department` / `School` / `Division` / `Senate` / `External` |
| `escalated_to_level`    | CharField     | Same choices as above                                        |
| `escalated_by`          | ForeignKey    | → `User`                                                     |
| `date_escalated`        | DateTimeField | Auto-set on creation                                         |
| `reason_for_escalation` | TextField     | Why it couldn't be resolved at the lower level               |

**Constraints**

- `escalated_from_level` and `escalated_to_level` can't be the same value

---

## 🔀 StatusChangeRequest

> A student's request for a leave of absence, withdrawal, readmission, or program transfer.

**Relationships**

- `student` → `Student` (ForeignKey)
- `processed_by` → `User` (ForeignKey, nullable)

| Field                 | Type       | Notes                                                       |
| --------------------- | ---------- | ----------------------------------------------------------- |
| `record_id`           | UUIDField  | Primary key                                                 |
| `student`             | ForeignKey | → `Student`                                                 |
| `change_type`         | CharField  | `leave` / `withdrawal` / `readmission` / `program_transfer` |
| `reason`              | TextField  | Blank allowed                                               |
| `supporting_document` | FileField  | Nullable                                                    |
| `status`              | CharField  | `pending` / `approved` / `rejected`                         |
| `processed_by`        | ForeignKey | → `User`, nullable                                          |
| `effective_date`      | DateField  | Nullable                                                    |

---

## 🧮 DegreeAudit

> A running, recalculable check of a student's credit completion and GPA against graduation eligibility.

**Relationships**

- `student` → `Student` (OneToOne)

| Field               | Type                 | Notes                                 |
| ------------------- | -------------------- | ------------------------------------- |
| `record_id`         | UUIDField            | Primary key                           |
| `student`           | OneToOneField        | → `Student`                           |
| `credits_completed` | PositiveIntegerField | Default: `0`                          |
| `credits_remaining` | PositiveIntegerField | Default: `0`                          |
| `gpa`               | DecimalField         | Nullable                              |
| `result`            | CharField            | `on_track` / `deficient` / `eligible` |
| `last_reviewed`     | DateTimeField        | Auto-updated on every save            |

> ⚠️ **Note:** as a single `OneToOneField`, re-running the audit overwrites
> the previous result — there's no history of past audit runs. If you need
> to show "the audit said X last term, Y this term," add a companion
> `DegreeAuditRun` log model rather than relying on `updated_at` alone.

---

## 🎓 Graduation

> A student's graduation candidacy record — tracks eligibility through to conferral.

**Relationships**

- `student` → `Student` (OneToOne)
- `Tclass` → `Tclass` (ForeignKey) — the cohort graduated with
- `diploma` ← `Diploma` (reverse OneToOne)
- `convocations` ← `Convocation` (reverse M2M)

| Field                  | Type          | Notes                                                                  |
| ---------------------- | ------------- | ---------------------------------------------------------------------- |
| `record_id`            | UUIDField     | Primary key                                                            |
| `student`              | OneToOneField | → `Student`                                                            |
| `Tclass`               | ForeignKey    | → `Tclass`                                                             |
| `status`               | CharField     | `nominated` / `verified` / `approved` / `conferred`                    |
| `final_classification` | CharField     | `First_Class` / `Second_Upper` / `Second_Lower` / `Pass` / `Satisfied` |
| `with_honours`         | BooleanField  | Default: `True`                                                        |
| `thesis_title`         | TextField     | Nullable — required for postgraduate awards                            |

**Notes**

- Postgraduate students (programme code starting `MSC`/`PHD`/`MA`) must have `thesis_title` set.
- Doctoral candidates cannot have `with_honours = True`.

---

## 📜 Diploma

> The physical/digital degree certificate, tied to one graduation candidacy.

**Relationships**

- `candidacy` → `Graduation` (OneToOne)

| Field            | Type          | Notes            |
| ---------------- | ------------- | ---------------- |
| `record_id`      | UUIDField     | Primary key      |
| `candidacy`      | OneToOneField | → `Graduation`   |
| `diploma_number` | CharField     | Unique           |
| `conferred_date` | DateField     |                  |
| `issued`         | BooleanField  | Default: `False` |
| `file`           | FileField     | Nullable         |

---

## 🎉 Convocation

> A graduation ceremony event — one ceremony seats many `Graduation` candidacies.

**Relationships**

- `candidates` → `Graduation` (ManyToMany)

| Field        | Type            | Notes                         |
| ------------ | --------------- | ----------------------------- |
| `record_id`  | UUIDField       | Primary key                   |
| `name`       | CharField       | e.g. `"42nd Convocation"`     |
| `date`       | DateField       |                               |
| `venue`      | CharField       | Blank allowed                 |
| `candidates` | ManyToManyField | → `Graduation`, blank allowed |

---

## 🏘️ HostelListing

> External/off-campus hostel guide entry for a student-facing housing directory —
> **not** the same as [`Hostel`](#-hostel), which tracks on-campus rooms and allocations.

| Field                       | Type                 | Notes                                                                                                      |
| --------------------------- | -------------------- | ---------------------------------------------------------------------------------------------------------- |
| `record_id`                 | UUIDField            | Primary key                                                                                                |
| `name`                      | CharField            |                                                                                                            |
| `badge`                     | CharField            | Nullable — `popular` / `students` / `scenic` / `community` / `views` / `other`                             |
| `location`                  | CharField            | Street address / landmark                                                                                  |
| `distance_note`             | CharField            | e.g. `"2 min walk to North Gate"`                                                                          |
| `price_per_month`           | PositiveIntegerField | KES                                                                                                        |
| `room_type`                 | CharField            | `single` / `single_ensuite` / `shared_2` / `shared_4` / `studio` / `mixed`                                 |
| `has_wifi` … `has_ethernet` | BooleanField (×10)   | Amenity toggles — wifi, meals, laundry, gym, parking, kitchen, study rooms, lounge, bike storage, ethernet |
| `wifi_note`                 | CharField            | Blank allowed                                                                                              |
| `phone`                     | CharField            |                                                                                                            |
| `email`                     | EmailField           |                                                                                                            |
| `is_published`              | BooleanField         | Default: `True`                                                                                            |
| `sort_order`                | PositiveIntegerField | Default: `0` — lower sorts first                                                                           |

**Properties**

| Property        | Returns                                               |
| --------------- | ----------------------------------------------------- |
| `amenity_chips` | List of `(icon, label)` tuples for template rendering |

---

## 🏗️ Building

> A physical structure on campus containing one or more `Venue`s.

**Relationships**

- `venues` ← `Venue` (reverse FK)

| Field             | Type                 | Notes                             |
| ----------------- | -------------------- | --------------------------------- |
| `record_id`       | UUIDField            | Primary key                       |
| `building_name`   | CharField            | Unique — e.g. `"Science Complex"` |
| `building_code`   | CharField            | Unique — e.g. `SCI`, `ADM`, `LIB` |
| `total_floors`    | PositiveIntegerField | Default: `1`                      |
| `has_lift`        | BooleanField         | Default: `False`                  |
| `has_ramp_access` | BooleanField         | Default: `False`                  |

---

## 📆 DailyClassExecution

> Tracks the actual day-to-day execution and attendance of a `Timetable` slot — did the class actually happen.

**Relationships**

- `timetable_slot` → `Timetable` (ForeignKey)
- `class_representative` → `Student` (ForeignKey, nullable)
- `rescheduled_by` → `User` (ForeignKey, nullable)
- `rescheduled_to_venue` → `Venue` (ForeignKey, nullable)

| Field                          | Type          | Notes                                                             |
| ------------------------------ | ------------- | ----------------------------------------------------------------- |
| `record_id`                    | UUIDField     | Primary key                                                       |
| `timetable_slot`               | ForeignKey    | → `Timetable`                                                     |
| `calendar_date`                | DateField     | The actual calendar date of this instance                         |
| `status`                       | CharField     | `Scheduled` / `Attended` / `Missed` / `Cancelled` / `Rescheduled` |
| `class_representative`         | ForeignKey    | → `Student`, nullable — required if `status=Attended`             |
| `student_confirmed_at`         | DateTimeField | Nullable, auto-set when confirmed                                 |
| `rescheduled_by`               | ForeignKey    | → `User`, nullable                                                |
| `reschedule_requested_by_role` | CharField     | `LECTURER` / `STUDENT` / `ADMIN`                                  |
| `rescheduled_to_date`          | DateField     | Nullable                                                          |
| `rescheduled_to_time_slot`     | CharField     | Nullable — one of `Timetable`'s time slots                        |
| `rescheduled_to_venue`         | ForeignKey    | → `Venue`, nullable                                               |
| `notes`                        | TextField     | Blank allowed                                                     |

**Constraints**

- `unique_together`: `(timetable_slot, calendar_date)`
- `status=Attended` requires `class_representative` set
- `status=Rescheduled` requires all four `rescheduled_to_*` target fields set, and they must differ from the original slot

---

## 🧑‍⚖️ ExamInvigilatorAssignment

> _(Optional)_ Through-table for `ExamVenue` invigilators, if a hall needs more
> than one — see the note under [ExamVenue](#-examvenue).

**Relationships**

- `exam_venue` → `ExamVenue` (ForeignKey)
- `lecturer` → `Lecturer` (ForeignKey)

| Field         | Type          | Notes                                                                  |
| ------------- | ------------- | ---------------------------------------------------------------------- |
| `record_id`   | UUIDField     | Primary key                                                            |
| `exam_venue`  | ForeignKey    | → `ExamVenue`                                                          |
| `lecturer`    | ForeignKey    | → `Lecturer`                                                           |
| `role`        | CharField     | `Chief` (room lead) / `Assistant` / `Relief`                           |
| `status`      | CharField     | `Draft` / `Published` / `Confirmed` / `Excused` / `Present` / `Absent` |
| `assigned_at` | DateTimeField | Auto-set on creation                                                   |

**Constraints**

- `unique_together`: `(exam_venue, lecturer)`
- Only one active `role=Chief` per venue
- A lecturer can't be double-booked across two active assignments at the same date/time slot

---

## 🏛️ Club

> A student club or society.

**Relationships**

- `patron` ← `ClubPatron` (reverse OneToOne)
- `memberships` ← `ClubMembership` (reverse FK)
- `recruitment_drives` ← `ClubRecruitmentDrive` (reverse FK)
- `events` ← `ClubEvent` (reverse FK)
- `activity_reports` ← `ClubActivityReport` (reverse FK)
- `budget` ← `ClubBudget` (reverse OneToOne)

| Field          | Type          | Notes                                                            |
| -------------- | ------------- | ---------------------------------------------------------------- |
| `record_id`    | UUIDField     | Primary key                                                      |
| `name`         | CharField     | Unique                                                           |
| `category`     | CharField     | `Academic` / `Sports` / `Cultural` / `Tech` / `Social` / `Other` |
| `description`  | TextField     | Blank allowed                                                    |
| `founded_date` | DateField     | Nullable                                                         |
| `status`       | CharField     | `Active` / `Inactive` / `Suspended`                              |
| `created_at`   | DateTimeField | Auto-set                                                         |
| `updated_at`   | DateTimeField | Auto-updated                                                     |

---

## 🧑‍🏫 ClubPatron

> The faculty advisor formally overseeing a club — see [Lecturer "Club Patron" role](#-lecturer) discussed earlier in this project.

**Relationships**

- `club` → `Club` (OneToOne)
- `lecturer` → `Lecturer` (ForeignKey)

| Field            | Type          | Notes                |
| ---------------- | ------------- | -------------------- |
| `record_id`      | UUIDField     | Primary key          |
| `club`           | OneToOneField | → `Club`             |
| `lecturer`       | ForeignKey    | → `Lecturer`         |
| `appointed_date` | DateField     | Auto-set on creation |
| `is_active`      | BooleanField  | Default: `True`      |

---

## 📣 ClubRecruitmentDrive

> A membership recruitment window for a club.

**Relationships**

- `club` → `Club` (ForeignKey)
- `memberships` ← `ClubMembership` (reverse FK, via `joined_via`)

| Field             | Type                 | Notes           |
| ----------------- | -------------------- | --------------- |
| `record_id`       | UUIDField            | Primary key     |
| `club`            | ForeignKey           | → `Club`        |
| `title`           | CharField            |                 |
| `opens_date`      | DateField            |                 |
| `closes_date`     | DateField            |                 |
| `max_new_members` | PositiveIntegerField | Nullable        |
| `is_active`       | BooleanField         | Default: `True` |

---

## 🪪 ClubMembership

> Links a student to a club they've joined.

**Relationships**

- `club` → `Club` (ForeignKey)
- `student` → `Student` (ForeignKey)
- `joined_via` → `ClubRecruitmentDrive` (ForeignKey, nullable)
- `leadership_positions` ← `ClubLeadershipPosition` (reverse FK)

| Field        | Type          | Notes                                      |
| ------------ | ------------- | ------------------------------------------ |
| `record_id`  | UUIDField     | Primary key                                |
| `club`       | ForeignKey    | → `Club`                                   |
| `student`    | ForeignKey    | → `Student`                                |
| `joined_via` | ForeignKey    | → `ClubRecruitmentDrive`, nullable         |
| `status`     | CharField     | `pending` / `active` / `inactive` / `left` |
| `joined_at`  | DateTimeField | Auto-set on creation                       |

**Constraints**

- `unique_together`: `(club, student)`

---

## 👑 ClubLeadershipPosition

> An executive role held within a club membership.

**Relationships**

- `membership` → `ClubMembership` (ForeignKey)

| Field        | Type         | Notes                                                              |
| ------------ | ------------ | ------------------------------------------------------------------ |
| `record_id`  | UUIDField    | Primary key                                                        |
| `membership` | ForeignKey   | → `ClubMembership`                                                 |
| `title`      | CharField    | `Chairperson` / `Secretary` / `Treasurer` / `Vice-Chair` / `Other` |
| `term_start` | DateField    |                                                                    |
| `term_end`   | DateField    | Nullable                                                           |
| `is_active`  | BooleanField | Default: `True`                                                    |

---

## 📅 ClubEvent

> A club-organised event.

**Relationships**

- `club` → `Club` (ForeignKey)
- `venue` → `Venue` (ForeignKey, nullable)
- `attendees` ← `ClubEventAttendance` (reverse FK)

| Field          | Type         | Notes                          |
| -------------- | ------------ | ------------------------------ |
| `record_id`    | UUIDField    | Primary key                    |
| `club`         | ForeignKey   | → `Club`                       |
| `title`        | CharField    |                                |
| `description`  | TextField    | Blank allowed                  |
| `date`         | DateField    |                                |
| `venue`        | ForeignKey   | → `Venue`, nullable            |
| `is_mandatory` | BooleanField | Default: `False` — for members |

---

## ✅ ClubEventAttendance

> Attendance record for a club event.

**Relationships**

- `event` → `ClubEvent` (ForeignKey)
- `student` → `Student` (ForeignKey)

| Field       | Type          | Notes            |
| ----------- | ------------- | ---------------- |
| `record_id` | UUIDField     | Primary key      |
| `event`     | ForeignKey    | → `ClubEvent`    |
| `student`   | ForeignKey    | → `Student`      |
| `attended`  | BooleanField  | Default: `False` |
| `marked_at` | DateTimeField | Auto-set         |

**Constraints**

- `unique_together`: `(event, student)`

---

## 📊 ClubActivityReport

> Periodic activity summary submitted by a club (to student affairs, or the patron).

**Relationships**

- `club` → `Club` (ForeignKey)
- `submitted_by` → `User` (ForeignKey, nullable)

| Field          | Type          | Notes              |
| -------------- | ------------- | ------------------ |
| `record_id`    | UUIDField     | Primary key        |
| `club`         | ForeignKey    | → `Club`           |
| `title`        | CharField     |                    |
| `period_start` | DateField     |                    |
| `period_end`   | DateField     |                    |
| `summary`      | TextField     |                    |
| `submitted_by` | ForeignKey    | → `User`, nullable |
| `submitted_at` | DateTimeField | Auto-set           |

---

## 💰 ClubBudget

> A club's allocated budget for a session.

**Relationships**

- `club` → `Club` (OneToOne)
- `session` → `Session` (ForeignKey)
- `transactions` ← `ClubTransaction` (reverse FK)

| Field              | Type          | Notes        |
| ------------------ | ------------- | ------------ |
| `record_id`        | UUIDField     | Primary key  |
| `club`             | OneToOneField | → `Club`     |
| `session`          | ForeignKey    | → `Session`  |
| `allocated_amount` | DecimalField  |              |
| `created_at`       | DateTimeField | Auto-set     |
| `updated_at`       | DateTimeField | Auto-updated |

---

## 🧾 ClubTransaction

> Individual income/expense entry against a club budget.

**Relationships**

- `budget` → `ClubBudget` (ForeignKey)
- `recorded_by` → `User` (ForeignKey, nullable)

| Field              | Type          | Notes                |
| ------------------ | ------------- | -------------------- |
| `record_id`        | UUIDField     | Primary key          |
| `budget`           | ForeignKey    | → `ClubBudget`       |
| `transaction_type` | CharField     | `income` / `expense` |
| `amount`           | DecimalField  |                      |
| `description`      | CharField     |                      |
| `receipt`          | FileField     | Nullable             |
| `recorded_by`      | ForeignKey    | → `User`, nullable   |
| `recorded_at`      | DateTimeField | Auto-set             |

---

## 🏛️ CouncilTerm

> A single term of the student governing body.

**Relationships**

- `positions` ← `CouncilPosition` (reverse FK)
- `elections` ← `Election` (reverse FK)
- `meetings` ← `CouncilMeeting` (reverse FK)

| Field        | Type         | Notes                              |
| ------------ | ------------ | ---------------------------------- |
| `record_id`  | UUIDField    | Primary key                        |
| `name`       | CharField    | e.g. `"2025/2026 Student Council"` |
| `start_date` | DateField    |                                    |
| `end_date`   | DateField    |                                    |
| `is_active`  | BooleanField | Default: `False`                   |

---

## 🪑 CouncilPosition

> An occupied or vacant seat within a council term.

**Relationships**

- `term` → `CouncilTerm` (ForeignKey)
- `student` → `Student` (ForeignKey, nullable — vacant until filled)
- `proposals` ← `CouncilProposal` (reverse FK)

| Field        | Type       | Notes                                                    |
| ------------ | ---------- | -------------------------------------------------------- |
| `record_id`  | UUIDField  | Primary key                                              |
| `term`       | ForeignKey | → `CouncilTerm`                                          |
| `title`      | CharField  | e.g. `President`, `VP`, `Secretary-General`, `Treasurer` |
| `student`    | ForeignKey | → `Student`, nullable                                    |
| `start_date` | DateField  |                                                          |
| `end_date`   | DateField  | Nullable                                                 |

---

## 🗳️ Election

> A student council election cycle.

**Relationships**

- `term` → `CouncilTerm` (ForeignKey)
- `positions` ← `ElectionPosition` (reverse FK)

| Field              | Type       | Notes                                                                           |
| ------------------ | ---------- | ------------------------------------------------------------------------------- |
| `record_id`        | UUIDField  | Primary key                                                                     |
| `term`             | ForeignKey | → `CouncilTerm`                                                                 |
| `title`            | CharField  |                                                                                 |
| `nomination_start` | DateField  |                                                                                 |
| `nomination_end`   | DateField  |                                                                                 |
| `voting_start`     | DateField  |                                                                                 |
| `voting_end`       | DateField  |                                                                                 |
| `status`           | CharField  | `upcoming` / `nominations_open` / `voting_open` / `closed` / `results_declared` |

---

## 📋 ElectionPosition

> A specific seat being contested in an election.

**Relationships**

- `election` → `Election` (ForeignKey)
- `candidates` ← `Candidate` (reverse FK)
- `votes` ← `Vote` (reverse FK)

| Field             | Type                      | Notes        |
| ----------------- | ------------------------- | ------------ |
| `record_id`       | UUIDField                 | Primary key  |
| `election`        | ForeignKey                | → `Election` |
| `position_title`  | CharField                 |              |
| `seats_available` | PositiveSmallIntegerField | Default: `1` |

---

## 🙋 Candidate

> A student running for an election position.

**Relationships**

- `election_position` → `ElectionPosition` (ForeignKey)
- `student` → `Student` (ForeignKey)

| Field               | Type       | Notes                                   |
| ------------------- | ---------- | --------------------------------------- |
| `record_id`         | UUIDField  | Primary key                             |
| `election_position` | ForeignKey | → `ElectionPosition`                    |
| `student`           | ForeignKey | → `Student`                             |
| `manifesto`         | TextField  | Blank allowed                           |
| `status`            | CharField  | `pending` / `approved` / `disqualified` |

**Constraints**

- `unique_together`: `(election_position, student)`

---

## ✔️ Vote

> A single cast ballot — one student, one vote, per contested position.

**Relationships**

- `election_position` → `ElectionPosition` (ForeignKey)
- `voter` → `Student` (ForeignKey)
- `candidate` → `Candidate` (ForeignKey)

| Field               | Type          | Notes                |
| ------------------- | ------------- | -------------------- |
| `record_id`         | UUIDField     | Primary key          |
| `election_position` | ForeignKey    | → `ElectionPosition` |
| `voter`             | ForeignKey    | → `Student`          |
| `candidate`         | ForeignKey    | → `Candidate`        |
| `cast_at`           | DateTimeField | Auto-set             |

**Constraints**

- `unique_together`: `(election_position, voter)` — one vote per student per contested seat

---

## 📜 CouncilProposal

> A motion tabled by a council position.

**Relationships**

- `position` → `CouncilPosition` (ForeignKey)
- `supporters` ← `ProposalSupport` (reverse FK)

| Field         | Type          | Notes                                                       |
| ------------- | ------------- | ----------------------------------------------------------- |
| `record_id`   | UUIDField     | Primary key                                                 |
| `position`    | ForeignKey    | → `CouncilPosition` — who tabled it                         |
| `title`       | CharField     |                                                             |
| `description` | TextField     |                                                             |
| `status`      | CharField     | `draft` / `tabled` / `under_review` / `passed` / `rejected` |
| `tabled_at`   | DateTimeField | Auto-set on creation                                        |

---

## ✍️ ProposalSupport

> A student's endorsement signature on a proposal.

**Relationships**

- `proposal` → `CouncilProposal` (ForeignKey)
- `student` → `Student` (ForeignKey)

| Field       | Type          | Notes               |
| ----------- | ------------- | ------------------- |
| `record_id` | UUIDField     | Primary key         |
| `proposal`  | ForeignKey    | → `CouncilProposal` |
| `student`   | ForeignKey    | → `Student`         |
| `signed_at` | DateTimeField | Auto-set            |

**Constraints**

- `unique_together`: `(proposal, student)`

---

## 📅 CouncilMeeting

> A scheduled council meeting.

**Relationships**

- `term` → `CouncilTerm` (ForeignKey)
- `attendees` ← `CouncilMeetingAttendance` (reverse FK)

| Field          | Type       | Notes           |
| -------------- | ---------- | --------------- |
| `record_id`    | UUIDField  | Primary key     |
| `term`         | ForeignKey | → `CouncilTerm` |
| `title`        | CharField  |                 |
| `date`         | DateField  |                 |
| `agenda`       | TextField  | Blank allowed   |
| `minutes_file` | FileField  | Nullable        |

---

## ✅ CouncilMeetingAttendance

> Attendance record for a council meeting.

**Relationships**

- `meeting` → `CouncilMeeting` (ForeignKey)
- `student` → `Student` (ForeignKey)

| Field       | Type         | Notes              |
| ----------- | ------------ | ------------------ |
| `record_id` | UUIDField    | Primary key        |
| `meeting`   | ForeignKey   | → `CouncilMeeting` |
| `student`   | ForeignKey   | → `Student`        |
| `attended`  | BooleanField | Default: `False`   |

**Constraints**

- `unique_together`: `(meeting, student)`

---

## 🆘 Grievance

> A welfare grievance submitted through the student governance/council channel.

**Relationships**

- `student` → `Student` (ForeignKey)
- `updates` ← `GrievanceUpdate` (reverse FK)

| Field          | Type          | Notes                                                   |
| -------------- | ------------- | ------------------------------------------------------- |
| `record_id`    | UUIDField     | Primary key                                             |
| `student`      | ForeignKey    | → `Student`                                             |
| `category`     | CharField     |                                                         |
| `description`  | TextField     |                                                         |
| `status`       | CharField     | `submitted` / `under_review` / `resolved` / `dismissed` |
| `submitted_at` | DateTimeField | Auto-set on creation                                    |
| `resolved_at`  | DateTimeField | Nullable                                                |

> ⚠️ **Overlap note:** `Grievance` and [`Complaint`](#-complaint) are two
> near-duplicate concepts entering the system through different doors —
> `Complaint` through the registrar/Dean of Students formal channel,
> `Grievance` through student council/welfare representatives. Decide which
> one is canonical before both exist in production, or make one route into
> the other (e.g. an unresolved `Grievance` escalates by creating a
> `Complaint`) rather than maintaining two parallel, unconnected pipelines.

---

## 🔄 GrievanceUpdate

> A status update/log entry on a grievance.

**Relationships**

- `grievance` → `Grievance` (ForeignKey)
- `updated_by` → `User` (ForeignKey, nullable)

| Field         | Type          | Notes              |
| ------------- | ------------- | ------------------ |
| `record_id`   | UUIDField     | Primary key        |
| `grievance`   | ForeignKey    | → `Grievance`      |
| `update_text` | TextField     |                    |
| `updated_by`  | ForeignKey    | → `User`, nullable |
| `created_at`  | DateTimeField | Auto-set           |

---

## 📜 Accreditation

> A regulatory accreditation held by a programme, or institution-wide.

**Relationships**

- `programme` → `Programme` (ForeignKey, nullable — blank for institution-wide accreditations)
- `documents` ← `AccreditationDocument` (reverse FK)
- `reports` ← `RegulatoryReport` (reverse FK)

| Field                | Type         | Notes                                                                |
| -------------------- | ------------ | -------------------------------------------------------------------- |
| `record_id`          | UUIDField    | Primary key                                                          |
| `programme`          | ForeignKey   | → `Programme`, nullable                                              |
| `code`               | CharField    | Unique                                                               |
| `name`               | CharField    |                                                                      |
| `body`               | CharField    | Accrediting agency, e.g. `CUE`, `KASNEB`, `Nursing Council of Kenya` |
| `accreditation_type` | CharField    | `Institutional` / `Programme` / `Specialized`                        |
| `status`             | CharField    | `Active` / `Pending` / `Review` / `Conditional` / `Expired`          |
| `valid_from`         | DateField    |                                                                      |
| `valid_to`           | DateField    | Nullable                                                             |
| `description`        | TextField    | Blank allowed                                                        |
| `version`            | IntegerField | Default: `1`                                                         |

**Properties**

| Property           | Returns                                                                          |
| ------------------ | -------------------------------------------------------------------------------- |
| `is_expiring_soon` | `True` if within the agency's renewal lead time (default 180 days) of `valid_to` |

---

## 📎 AccreditationDocument

> Evidence document supporting an accreditation.

**Relationships**

- `accreditation` → `Accreditation` (ForeignKey)

| Field           | Type          | Notes                                       |
| --------------- | ------------- | ------------------------------------------- |
| `record_id`     | UUIDField     | Primary key                                 |
| `accreditation` | ForeignKey    | → `Accreditation`                           |
| `file`          | FileField     | Uploads to `accreditation_documents/%Y/%m/` |
| `original_name` | CharField     | Auto-preserved from upload                  |
| `description`   | CharField     | Blank allowed                               |
| `uploaded_at`   | DateTimeField | Auto-set                                    |

---

## 🗓️ RegistrationWindow

> Generic open/close window for any registration-type activity tied to a session
> — course registration, bursary, hostel, exam registration, backlog exams,
> graduation candidacy, club membership, scholarships. One model instead of
> a scattered date-pair per activity.

**Relationships**

- `session` → `Session` (ForeignKey)
- `programme` → `Programme` (ForeignKey, nullable — blank for institution-wide windows)

| Field              | Type         | Notes                                                                                                                                            |
| ------------------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `record_id`        | UUIDField    | Primary key                                                                                                                                      |
| `session`          | ForeignKey   | → `Session`                                                                                                                                      |
| `window_type`      | CharField    | `course_registration` / `bursary` / `hostel` / `exam_registration` / `backlog_exam` / `graduation_candidacy` / `club_membership` / `scholarship` |
| `programme`        | ForeignKey   | → `Programme`, nullable                                                                                                                          |
| `opens_date`       | DateField    |                                                                                                                                                  |
| `closes_date`      | DateField    |                                                                                                                                                  |
| `late_closes_date` | DateField    | Nullable — grace/late period end date, if allowed                                                                                                |
| `is_active`        | BooleanField | Default: `True` — manual kill-switch to close early                                                                                              |

**Constraints**

- `unique_together`: `(session, window_type, programme)`

**Properties**

| Property         | Returns                                                                                 |
| ---------------- | --------------------------------------------------------------------------------------- |
| `is_open`        | `True` if active and today is within `opens_date`–`closes_date` (or `late_closes_date`) |
| `is_late_period` | `True` if today is within the grace period past `closes_date`                           |

---

## 📄 RegulatoryReport

> A statutory report submission tracked against a regulator's requirements and deadline.

**Relationships**

- `related_accreditation` → `Accreditation` (ForeignKey, nullable)
- `session` → `Session` (ForeignKey, nullable)
- `documents` ← `RegulatoryReportDocument` (reverse FK)

| Field                   | Type         | Notes                                                                                       |
| ----------------------- | ------------ | ------------------------------------------------------------------------------------------- |
| `record_id`             | UUIDField    | Primary key                                                                                 |
| `related_accreditation` | ForeignKey   | → `Accreditation`, nullable                                                                 |
| `session`               | ForeignKey   | → `Session`, nullable                                                                       |
| `code`                  | CharField    | Unique                                                                                      |
| `name`                  | CharField    |                                                                                             |
| `agency`                | CharField    |                                                                                             |
| `report_type`           | CharField    | e.g. `Enrolment_Return`, `Graduation_Audit`, `Staff_Ledger`, `Financial_Statement`, `Other` |
| `custom_report_title`   | CharField    | Nullable — required if `report_type = Other`                                                |
| `trigger_type`          | CharField    | `recurring` / `accreditation_renewal` / `ad_hoc`                                            |
| `status`                | CharField    | `Draft` / `Submitted` / `Review` / `Approved` / `Rejected`                                  |
| `description`           | TextField    | Blank allowed                                                                               |
| `due_date`              | DateField    |                                                                                             |
| `submission_date`       | DateField    | Nullable — auto-set when marked `Submitted`                                                 |
| `version`               | IntegerField | Default: `1`                                                                                |

**Properties**

| Property     | Returns                                                      |
| ------------ | ------------------------------------------------------------ |
| `is_overdue` | `True` if not yet `Submitted`/`Approved` and past `due_date` |

**Methods**

| Method                           | Description                                                                                |
| -------------------------------- | ------------------------------------------------------------------------------------------ |
| `set_status(new_status)`         | Enforces `submission_date` gets set exactly once, when moving to `Submitted`               |
| `rollover_for_session(from, to)` | Class method — clones all `recurring` reports into the next session with shifted due dates |

---

## 📎 RegulatoryReportDocument

> Evidence uploaded alongside an official statutory report.

**Relationships**

- `report` → `RegulatoryReport` (ForeignKey)

| Field           | Type          | Notes                                  |
| --------------- | ------------- | -------------------------------------- |
| `record_id`     | UUIDField     | Primary key                            |
| `report`        | ForeignKey    | → `RegulatoryReport`                   |
| `file`          | FileField     | Uploads to `regulatory_reports/%Y/%m/` |
| `original_name` | CharField     | Auto-preserved from upload             |
| `description`   | CharField     | Blank allowed                          |
| `uploaded_at`   | DateTimeField | Auto-set                               |

---

## 🗓️ ComplianceCalendarEvent

> A denormalized projection over `Accreditation`, `RegulatoryReport`, and
> `RegistrationWindow` deadlines, so a calendar view queries one table
> instead of joining three. Regenerate via a management command/signal when
> a source record's dates change — don't hand-maintain.

| Field         | Type      | Notes                                                                |
| ------------- | --------- | -------------------------------------------------------------------- |
| `record_id`   | UUIDField | Primary key                                                          |
| `source_type` | CharField | `accreditation_expiry` / `report_deadline` / `registration_window`   |
| `source_id`   | CharField | The source record's ID — resolved against `source_type` at read time |
| `title`       | CharField |                                                                      |
| `due_date`    | DateField |                                                                      |
| `recurrence`  | CharField | `none` / `semester` / `annual`                                       |

**Methods**

| Method             | Description                               |
| ------------------ | ----------------------------------------- |
| `days_remaining()` | Returns days between today and `due_date` |

---

## 📣 Announcement

> A lecturer/staff post to a class, a specific unit, or a whole department.

**Relationships**

- `author` → `User` (ForeignKey)
- `curriculum` → `Curriculum` (ForeignKey, nullable)
- `documents` ← `AnnouncementDocument` (reverse FK)

| Field          | Type          | Notes                                                                               |
| -------------- | ------------- | ----------------------------------------------------------------------------------- |
| `record_id`    | UUIDField     | Primary key                                                                         |
| `author`       | ForeignKey    | → `User`                                                                            |
| `title`        | CharField     |                                                                                     |
| `body`         | TextField     |                                                                                     |
| `scope`        | CharField     | `class` (specific class) / `curriculum` (specific unit) / `dept` (whole department) |
| `curriculum`   | ForeignKey    | → `Curriculum`, nullable                                                            |
| `is_urgent`    | BooleanField  | Default: `False` — fires SMS instead of portal-only notification                    |
| `published_at` | DateTimeField | Nullable                                                                            |

---

## 📎 AnnouncementDocument

> Slides, briefs, or other files attached to an announcement. Portal-delivered only — SMS notifications carry a link, not the file.

**Relationships**

- `announcement` → `Announcement` (ForeignKey)

| Field          | Type                 | Notes                                               |
| -------------- | -------------------- | --------------------------------------------------- |
| `record_id`    | UUIDField            | Primary key                                         |
| `announcement` | ForeignKey           | → `Announcement`                                    |
| `file`         | FileField            | Uploads to `lecturer_announcements/%Y/%m/`          |
| `description`  | CharField            | Blank allowed                                       |
| `order`        | PositiveIntegerField | Default: `0` — display order in the attachment list |
| `uploaded_at`  | DateTimeField        | Auto-set                                            |

---

> 🔗 Back to [Project Index](../README.md)
> 🔗 Back to [Documentation Index](./README.md)
> 🔗 See the [ER Diagram](er-diagram.md) for a visual representation of these relationships
> 🔗 See the models source files for the concrete implementation
