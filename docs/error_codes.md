# 🚨 Error Codes

> Business error codes for the School Management System.
> These are domain-level errors — distinct from HTTP status codes or
> Django exceptions. Every error has a code, a message, and a clear
> description of what caused it and how to recover.

---

## 📑 Contents

| Domain                                               | Prefix | Codes           |
| ---------------------------------------------------- | ------ | --------------- |
| [👤 User & Auth](#-user--auth-errors)                | `USR`  | USR001 – USR006 |
| [🎓 Student](#-student-errors)                       | `STU`  | STU001 – STU007 |
| [📚 Enrollment](#-enrollment-errors)                 | `ENR`  | ENR001 – ENR006 |
| [🗓️ Session](#-session-errors)                       | `SES`  | SES001 – SES004 |
| [💰 Fees & Payments](#-fees--payment-errors)         | `FEE`  | FEE001 – FEE007 |
| [⚠️ Overdraft](#-overdraft-errors)                   | `OVD`  | OVD001 – OVD003 |
| [🏛️ Academic Structure](#-academic-structure-errors) | `ACD`  | ACD001 – ACD005 |
| [📋 Curriculum](#-curriculum-errors)                 | `CUR`  | CUR001 – CUR004 |
| [✅ Reporting](#-reporting-errors)                   | `RPT`  | RPT001 – RPT003 |
| [🕐 Timetable](#-timetable-errors)                   | `TBL`  | TBL001 – TBL004 |
| [📊 Results](#-results-errors)                       | `RES`  | RES001 – RES003 |
| [🔄 Session Rollover](#-session-rollover-errors)     | `ROL`  | ROL001 – ROL004 |

---

## 👤 User & Auth Errors

| Code     | Message                  | Cause                                                | Resolution                                                                  |
| -------- | ------------------------ | ---------------------------------------------------- | --------------------------------------------------------------------------- |
| `USR001` | User not found           | No `User` exists with the given identifier           | Verify the email or UUID before querying                                    |
| `USR002` | Email already registered | A `User` with this email already exists              | Use a different email or retrieve the existing account                      |
| `USR003` | Invalid credentials      | Email and password combination does not match        | Verify credentials. Account may be locked — check `django-axes`             |
| `USR004` | Account inactive         | `user.is_active` is `False`                          | Contact an institution admin to reactivate the account                      |
| `USR005` | Account not activated    | `user.is_activated` is `False`                       | Complete the activation step before logging in                              |
| `USR006` | Profile already exists   | A profile for this role already exists for this user | Each user can have only one profile per role. Retrieve the existing profile |

---

## 🎓 Student Errors

| Code     | Message                   | Cause                                                    | Resolution                                                                      |
| -------- | ------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `STU001` | Student not found         | No `Student` profile exists for this user                | Verify the user has a student profile. Check `hasattr(user, 'student_profile')` |
| `STU002` | Registration number taken | A student with this `registration_number` already exists | Registration numbers are unique. Verify the number before creating              |
| `STU003` | National ID taken         | A student with this `national_id` already exists         | Each national ID can only be registered once. Check for duplicate records       |
| `STU004` | School email taken        | A student with this `school_email` already exists        | School emails are unique per institution. Generate a new one                    |
| `STU005` | Student already deferred  | `student.deffered` is already `True`                     | Cannot defer a student twice. Contact registrar to reinstate first              |
| `STU006` | Student already graduated | `student.graduated` is already set                       | Cannot modify academic status of a graduated student                            |
| `STU007` | No class assigned         | `student.class_entered` is not set                       | Assign the student to a class before proceeding                                 |

---

## 📚 Enrollment Errors

| Code     | Message                    | Cause                                                                           | Resolution                                                                          |
| -------- | -------------------------- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `ENR001` | Already enrolled           | Student is already enrolled in this `Curriculum` entry                          | Check existing enrollments before adding. Use `get_or_create`                       |
| `ENR002` | Elective limit reached     | Student has reached `MAX_ELECTIVES` for this session                            | Student must drop an elective before registering a new one                          |
| `ENR003` | Unit not available         | The `Curriculum` entry does not belong to the student's class or active session | Verify the curriculum entry is for the student's `class_entered` and active session |
| `ENR004` | Cannot enroll in core unit | Core (`C`) and Common Unit (`CC`) courses are auto-enrolled                     | These units are managed by the system. Manual enrollment is not permitted           |
| `ENR005` | Cannot drop core unit      | Attempt to drop a `C` or `CC` course                                            | Only elective (`E`) units can be dropped by students                                |
| `ENR006` | No active session          | Enrollment attempted when no session has `is_active=True`                       | Activate a session before processing enrollments                                    |

---

## 🗓️ Session Errors

| Code     | Message                | Cause                                                                   | Resolution                                                                                             |
| -------- | ---------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `SES001` | Session not found      | No `Session` exists with the given identifier                           | Verify the session ID or academic year/semester combination                                            |
| `SES002` | No active session      | No `Session` has `is_active=True`                                       | Activate a session before performing session-dependent operations                                      |
| `SES003` | Session already active | Another session is already active when attempting to activate a new one | Deactivate the current session before activating a new one. Use `rollover_academic_session()`          |
| `SES004` | Duplicate session      | A session with this `academic_year` and `semester` already exists       | The `unique_together (academic_year, semester)` constraint was violated. Retrieve the existing session |

---

## 💰 Fees & Payment Errors

| Code     | Message                         | Cause                                                               | Resolution                                                                                             |
| -------- | ------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `FEE001` | Fee structure not found         | No `FeeStructure` exists for this class and session                 | Create a fee structure for the class before creating student accounts                                  |
| `FEE002` | Fee account not found           | No `StudentFeeAccount` exists for this student and session          | The account is auto-created on first visit to the fee page — ensure the view has been called           |
| `FEE003` | Account already cleared         | Payment attempted on an account with `is_cleared=True`              | No further payment is needed. Create an overdraft record if an overpayment is intentional              |
| `FEE004` | Duplicate transaction reference | A `Payment` with this `transaction_ref` and `method` already exists | Each transaction reference must be unique per payment method. Verify the M-Pesa code or bank ref       |
| `FEE005` | Invalid payment amount          | `amount` is zero or negative                                        | Payment amount must be greater than zero                                                               |
| `FEE006` | Fee structure already exists    | A `FeeStructure` for this class and session already exists          | The `unique_together (tclass, session)` constraint was violated. Update the existing structure instead |
| `FEE007` | Offline payment not permitted   | Payment submitted without a confirmed server connection             | Payments require a live connection. Do not queue payment submissions for background sync               |

---

## ⚠️ Overdraft Errors

| Code     | Message                     | Cause                                                                     | Resolution                                                                                                    |
| -------- | --------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `OVD001` | Overdraft not found         | No `OverDraft` exists with the given identifier                           | Verify the overdraft ID                                                                                       |
| `OVD002` | Overdraft already processed | `OverDraft.status` is `carried` or `refunded`                             | Already processed overdrafts cannot be reprocessed. Review the audit trail                                    |
| `OVD003` | No next fee account         | Overdraft carry-forward attempted but student has no next session account | The overdraft will be flagged for refund instead. Trigger `overdraft.process()` after next session is created |

---

## 🏛️ Academic Structure Errors

| Code     | Message                        | Cause                                            | Resolution                                                             |
| -------- | ------------------------------ | ------------------------------------------------ | ---------------------------------------------------------------------- |
| `ACD001` | School not found               | No `School` exists with the given identifier     | Verify the school ID                                                   |
| `ACD002` | Department not found           | No `Department` exists with the given identifier | Verify the department ID and that it belongs to the expected school    |
| `ACD003` | Programme not found            | No `Programme` exists with the given identifier  | Verify the programme ID and that it belongs to the expected department |
| `ACD004` | Class not found                | No `Tclass` exists with the given identifier     | Verify the class ID and that it belongs to the expected programme      |
| `ACD005` | Programme has no current class | `programme.current_class` is `None`              | Assign a current class to the programme before registering students    |

---

## 📋 Curriculum Errors

| Code     | Message                    | Cause                                                                   | Resolution                                                                                           |
| -------- | -------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `CUR001` | Curriculum entry not found | No `Curriculum` entry exists with the given identifier                  | Verify the curriculum ID, class, and session combination                                             |
| `CUR002` | Duplicate curriculum entry | A `Curriculum` entry for this course, class, and session already exists | The `unique_together (course, Tclass, session)` constraint was violated. Retrieve the existing entry |
| `CUR003` | No professor assigned      | The `Curriculum` entry has no professors in `professor` M2M             | Assign at least one lecturer before publishing the timetable                                         |
| `CUR004` | Clone source session empty | `clone_curriculum()` called on a session with no curriculum entries     | The source session has no curriculum to clone. Build it manually for the new session                 |

---

## ✅ Reporting Errors

| Code     | Message           | Cause                                                            | Resolution                                                                                                   |
| -------- | ----------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `RPT001` | Already reported  | A `Reporting` record already exists for this student and session | The `unique_together (student, session)` constraint was violated. A student can only report once per session |
| `RPT002` | No active session | Reporting attempted when no session has `is_active=True`         | Activate a session before students can report                                                                |
| `RPT003` | Student deferred  | Reporting attempted for a deferred student                       | Deferred students cannot report. Reinstate the student first                                                 |

---

## 🕐 Timetable Errors

| Code     | Message                  | Cause                                                                            | Resolution                                                                                                              |
| -------- | ------------------------ | -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `TBL001` | Venue clash              | A timetable slot already exists for this venue, day, and time in this session    | The `unique_together (session, venue, day, start_time)` constraint was violated. Choose a different venue or time       |
| `TBL002` | Lecturer clash           | A timetable slot already exists for this lecturer, day, and time in this session | The `unique_together (session, lecturer, day, start_time)` constraint was violated. Choose a different lecturer or time |
| `TBL003` | Class clash              | A timetable slot already exists for this class, day, and time                    | A class cannot have two subjects at the same time. Choose a different slot                                              |
| `TBL004` | Timetable slot not found | No `Timetable` entry exists with the given identifier                            | Verify the slot ID, session, and class combination                                                                      |

---

## 📊 Results Errors

| Code     | Message            | Cause                                                                          | Resolution                                                                                             |
| -------- | ------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| `RES001` | Result not found   | No `Result` exists for this student and curriculum entry                       | Verify the student is enrolled in the course and results have been published                           |
| `RES002` | Score out of range | `score` is outside the permitted range for the result type                     | Validate score before saving. CAT max is typically 30, Exam max is 70 — confirm with institution rules |
| `RES003` | Duplicate result   | A result of the same type already exists for this student and curriculum entry | Update the existing result rather than creating a new one                                              |

---

## 🔄 Session Rollover Errors

| Code     | Message                     | Cause                                                          | Resolution                                                                          |
| -------- | --------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `ROL001` | No active session           | Rollover called when no session has `is_active=True`           | Activate a session before attempting rollover                                       |
| `ROL002` | Next session already active | The session that would be created already has `is_active=True` | Rollover has already been performed. Check the current active session               |
| `ROL003` | Rollover transaction failed | The `transaction.atomic()` block failed and was rolled back    | Check database logs for the root cause. No changes were committed — safe to retry   |
| `ROL004` | Curriculum clone failed     | `clone_curriculum()` returned zero cloned entries              | The source session had no curriculum. Build curriculum for the new session manually |

---

## 🏗️ Using Error Codes in Code

Define all errors as constants — never hardcode strings in logic:

```python
# utils/errors.py


class PortalError(Exception):
    def __init__(self, code: str, message: str, detail: str = ""):
        self.code    = code
        self.message = message
        self.detail  = detail
        super().__init__(f"[{code}] {message}")

    def to_dict(self):
        return {
            "code":    self.code,
            "message": self.message,
            "detail":  self.detail,
        }


# ── User & Auth ────────────────────────────────────────────────────
USR001 = lambda: PortalError("USR001", "User not found")
USR002 = lambda: PortalError("USR002", "Email already registered")
USR003 = lambda: PortalError("USR003", "Invalid credentials")
USR004 = lambda: PortalError("USR004", "Account inactive")
USR005 = lambda: PortalError("USR005", "Account not activated")
USR006 = lambda: PortalError("USR006", "Profile already exists")

# ── Student ────────────────────────────────────────────────────────
STU001 = lambda: PortalError("STU001", "Student not found")
STU002 = lambda: PortalError("STU002", "Registration number taken")
STU003 = lambda: PortalError("STU003", "National ID taken")
STU004 = lambda: PortalError("STU004", "School email taken")
STU005 = lambda: PortalError("STU005", "Student already deferred")
STU006 = lambda: PortalError("STU006", "Student already graduated")
STU007 = lambda: PortalError("STU007", "No class assigned")

# ── Enrollment ────────────────────────────────────────────────────
ENR001 = lambda: PortalError("ENR001", "Already enrolled")
ENR002 = lambda: PortalError("ENR002", "Elective limit reached")
ENR003 = lambda: PortalError("ENR003", "Unit not available")
ENR004 = lambda: PortalError("ENR004", "Cannot enroll in core unit")
ENR005 = lambda: PortalError("ENR005", "Cannot drop core unit")
ENR006 = lambda: PortalError("ENR006", "No active session")

# ── Session ───────────────────────────────────────────────────────
SES001 = lambda: PortalError("SES001", "Session not found")
SES002 = lambda: PortalError("SES002", "No active session")
SES003 = lambda: PortalError("SES003", "Session already active")
SES004 = lambda: PortalError("SES004", "Duplicate session")

# ── Fees & Payments ───────────────────────────────────────────────
FEE001 = lambda: PortalError("FEE001", "Fee structure not found")
FEE002 = lambda: PortalError("FEE002", "Fee account not found")
FEE003 = lambda: PortalError("FEE003", "Account already cleared")
FEE004 = lambda: PortalError("FEE004", "Duplicate transaction reference")
FEE005 = lambda: PortalError("FEE005", "Invalid payment amount")
FEE006 = lambda: PortalError("FEE006", "Fee structure already exists")
FEE007 = lambda: PortalError("FEE007", "Offline payment not permitted")

# ── Overdraft ─────────────────────────────────────────────────────
OVD001 = lambda: PortalError("OVD001", "Overdraft not found")
OVD002 = lambda: PortalError("OVD002", "Overdraft already processed")
OVD003 = lambda: PortalError("OVD003", "No next fee account")

# ── Academic Structure ────────────────────────────────────────────
ACD001 = lambda: PortalError("ACD001", "School not found")
ACD002 = lambda: PortalError("ACD002", "Department not found")
ACD003 = lambda: PortalError("ACD003", "Programme not found")
ACD004 = lambda: PortalError("ACD004", "Class not found")
ACD005 = lambda: PortalError("ACD005", "Programme has no current class")

# ── Curriculum ────────────────────────────────────────────────────
CUR001 = lambda: PortalError("CUR001", "Curriculum entry not found")
CUR002 = lambda: PortalError("CUR002", "Duplicate curriculum entry")
CUR003 = lambda: PortalError("CUR003", "No professor assigned")
CUR004 = lambda: PortalError("CUR004", "Clone source session empty")

# ── Reporting ─────────────────────────────────────────────────────
RPT001 = lambda: PortalError("RPT001", "Already reported")
RPT002 = lambda: PortalError("RPT002", "No active session")
RPT003 = lambda: PortalError("RPT003", "Student deferred")

# ── Timetable ─────────────────────────────────────────────────────
TBL001 = lambda: PortalError("TBL001", "Venue clash")
TBL002 = lambda: PortalError("TBL002", "Lecturer clash")
TBL003 = lambda: PortalError("TBL003", "Class clash")
TBL004 = lambda: PortalError("TBL004", "Timetable slot not found")

# ── Results ───────────────────────────────────────────────────────
RES001 = lambda: PortalError("RES001", "Result not found")
RES002 = lambda: PortalError("RES002", "Score out of range")
RES003 = lambda: PortalError("RES003", "Duplicate result")

# ── Rollover ──────────────────────────────────────────────────────
ROL001 = lambda: PortalError("ROL001", "No active session")
ROL002 = lambda: PortalError("ROL002", "Next session already active")
ROL003 = lambda: PortalError("ROL003", "Rollover transaction failed")
ROL004 = lambda: PortalError("ROL004", "Curriculum clone failed")
```

---

### Raising with context

```python
from utils.errors import ENR002, FEE003, RPT001

# enrollment limit check
if enrolled_electives >= MAX_ELECTIVES:
    raise ENR002()

# payment on cleared account
if account.is_cleared:
    raise FEE003()

# duplicate reporting
if Reporting.objects.filter(student=student, session=session).exists():
    raise RPT001()
```

### Raising with detail

```python
from utils.errors import PortalError

raise PortalError(
    "TBL001",
    "Venue clash",
    detail=f"Hall A is already booked on MON at 09:00 in session {session}"
)
```

### API response shape

```json
{
  "code": "ENR002",
  "message": "Elective limit reached",
  "detail": "Maximum of 3 electives allowed per session. Student has 3."
}
```

---

> 🔗 Back to [Documentation Index](docs/README.md)
