# 🗺️ Enrollment User Journey

> What the student and admin experience through the enrollment process.

---

## 🎓 Student Journey

```mermaid
journey
    title Student Enrollment Journey
    section Registration
      Student arrives at institution: 5: Student
      Admin creates Student record: 4: DeptAdmin
      System auto-enrolls core courses: 3: System
    section Course Selection
      Student views available electives: 4: Student
      Admin enrolls student in electives: 4: DeptAdmin
    section Confirmation
      Student confirms enrollment: 5: Student
      Student attends first class: 5: Student, Lecturer
```

---

## 👨‍💼 Admin Journey

```mermaid
journey
    title Admin Enrollment Management Journey
    section New Student
      Receive student documents: 3: DeptAdmin
      Create User account: 4: DeptAdmin
      Create Student profile: 4: DeptAdmin
      System handles core enrollment: 5: System
    section Manual Enrollment
      Open student record: 5: DeptAdmin
      Review auto-enrolled courses: 4: DeptAdmin
      Add elective courses: 4: DeptAdmin
      Save and confirm: 5: DeptAdmin
```

---

> 🔗 Back to [Enrollment Module](index.md)
