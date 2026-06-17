# 🔁 Enrollment Sequence Diagram

> How the signal, models, and database interact during enrollment.

---

## ⚡ Auto-Enrollment Sequence

```mermaid
sequenceDiagram
    actor Admin
    participant StudentAdmin
    participant Student
    participant Signal
    participant Session
    participant Curriculum

    Admin->>StudentAdmin: Save new Student
    StudentAdmin->>Student: save()
    Student-->>Signal: post_save fires (created=True)
    Signal->>Session: get(is_active=True)
    alt No active session
        Session-->>Signal: DoesNotExist
        Signal-->>Student: Pass silently
    else Active session found
        Session-->>Signal: session instance
        Signal->>Curriculum: filter(Tclass, session, course_type C/CC)
        alt No core courses found
            Curriculum-->>Signal: empty queryset
        else Courses found
            Curriculum-->>Signal: queryset
            Signal->>Student: enrollments.add(*core_subjects)
            Student-->>Admin: Student enrolled
        end
    end
```

---

## 🖱️ Manual Enrollment Sequence

```mermaid
sequenceDiagram
    actor Admin
    participant StudentAdmin
    participant FormField
    participant Curriculum
    participant Student

    Admin->>StudentAdmin: Open Student change form
    StudentAdmin->>FormField: formfield_for_manytomany()
    FormField->>Curriculum: filter(Tclass=student.class_entered, session__is_active=True)
    Curriculum-->>FormField: scoped queryset
    FormField-->>Admin: Render enrollment widget
    Admin->>StudentAdmin: Select courses and Save
    StudentAdmin->>Student: enrollments.set(selected)
    Student-->>Admin: Saved
```

---

> 🔗 Back to [Enrollment Module](index.md)
