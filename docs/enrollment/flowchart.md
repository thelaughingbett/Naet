# 🔀 Enrollment Flowchart

> Step-by-step logic for how students get enrolled into courses.

---

## ⚡ Auto-Enrollment on Registration

```mermaid
flowchart TD
    A[New Student Created] --> B[post_save signal fires]
    B --> C{Active Session exists?}
    C -- No --> D[Pass silently\nno enrollment]
    C -- Yes --> E[Filter Curriculum for\nstudent class + active session\ncourse type C or CC]
    E --> F{Courses found?}
    F -- No --> G[No enrollment]
    F -- Yes --> H[Add to student.enrollments]
    H --> I[Student enrolled in core curriculum]
```

---

## 🖱️ Manual Enrollment via Admin

```mermaid
flowchart TD
    A[Admin opens Student record] --> B[Opens Enrollments widget]
    B --> C[Widget filters Curriculum\nto student class\n+ active session only]
    C --> D[Admin selects courses]
    D --> E[Save]
    E --> F[Enrollment saved]
```

---

## 📌 Notes

- ⚠️ Auto-enrollment only runs on **creation** — not on updates
- 🔒 Enrollment widget scoped to student's class and active session
- 📚 Course types: `C` = Core, `E` = Elective, `CC` = Common Unit
- ⚡ Signal lives in `signals.py`, loaded via `apps.py` ready()

---

> 🔗 Back to [Enrollment Module](index.md)
