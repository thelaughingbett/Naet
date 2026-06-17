# 🎓 Enrollment Module

> Handles how students get into courses — automatically on registration
> and manually through the admin panel.

---

## 📋 Overview

When a new student is created, a Django signal fires automatically and enrolls
them into all **Core** and **Common Unit** courses for their class in the active
session. Elective courses are enrolled manually by an admin through the
enrollment widget, which is scoped to only show relevant curriculum.

**Models involved:** `Student` · `Curriculum` · `Session` · `Tclass` · `Course`

---

## 🔗 How It Connects

```
Student
└── class_entered → Tclass
    └── Curriculum (course + session + lecturer)
        └── Student.enrollments (ManyToMany)
```

---

## 📊 Diagrams

| Diagram                              | What it shows                         |
| ------------------------------------ | ------------------------------------- |
| [🔀 Flowchart](flowchart.md)         | Step-by-step enrollment logic         |
| [🔁 Sequence](sequence.md)           | Signal flow between components        |
| [🏗️ Class Diagram](class-diagram.md) | Model structure and relationships     |
| [🗺️ User Journey](user-journey.md)   | What the student and admin experience |

---

> 🔗 Back to [Project Index](../../../README.md)
> 🔗 Back to [Documentation Index](../../README.md)
