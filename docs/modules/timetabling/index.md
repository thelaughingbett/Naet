# 🕐 Timetabling Module

> Schedule management for classes — with built-in clash detection
> for both venues and lecturers.

---

## 📋 Overview

Each timetable slot assigns a class to a course, taught by a lecturer,
in a specific venue, at a specific time on a specific day.

The database enforces two clash constraints:

- A venue cannot be double-booked at the same time
- A lecturer cannot be in two places at the same time

**Models involved:** `Timetable` · `Tclass` · `Course` · `Lecturer` · `Session`

---

## 📊 Diagrams

| Diagram                              | What it shows                          |
| ------------------------------------ | -------------------------------------- |
| [🔀 Flowchart](flowchart.md)         | Timetable creation and clash detection |
| [🏗️ Class Diagram](class-diagram.md) | Model structure and constraints        |

---

## ⚡ Key Behaviours

- Two `unique_together` constraints enforce clash prevention at the database level
- `clean()` on `ExamVenue` provides early validation before save
- Timetable is scoped per session — each semester gets a fresh schedule

---

> 🔗 Back to [Project Index](../../../README.md)
> 🔗 Back to [Documentation Index](../../README.md)
