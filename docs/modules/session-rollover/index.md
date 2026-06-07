# 🔄 Session Rollover Module

> How the system transitions from one academic semester to the next.
> One method call handles everything — curriculum cloning, session switching, and overdraft processing.

---

## 📋 Overview

At the end of every semester, `Session.rollover_academic_session()` is called.
It generates the next session name, clones the curriculum from the equivalent
semester in the previous year, deactivates the current session, activates the
next one, and processes all pending overdrafts.

The entire operation runs inside `transaction.atomic()` — if anything fails,
nothing is committed and the current session stays active.

**Models involved:** `Session` · `Curriculum` · `OverDraft` · `StudentFeeAccount`

---

## 🔗 How It Connects

```
Current Session (is_active=True)
     ↓
Generate next semester name
     ↓
Clone Curriculum from previous same-semester session
     ↓
Deactivate current → Activate next
     ↓
Process pending OverDrafts
     ↓
New Session (is_active=True)
```

---

## 📊 Diagrams

| Diagram                      | What it shows                       |
| ---------------------------- | ----------------------------------- |
| [🔀 Flowchart](flowchart.md) | Step-by-step rollover process       |
| [🔁 Sequence](sequence.md)   | How models interact during rollover |

---

> 🔗 Back to [Project Index](../../../README.md)
> 🔗 Back to [Documentation Index](../../README.md)
