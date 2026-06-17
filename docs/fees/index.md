# 💰 Fees & Payments Module

> Handles everything money — fee structures, student accounts,
> payment recording, and overdraft carry-forward logic.

---

## 📋 Overview

Every student gets a `StudentFeeAccount` per session, linked to a
`FeeStructure` that defines what their class owes. Fees are itemised
as a JSON breakdown (tuition, registration, hostel, etc.) so the
structure is flexible per class per session.

Payments are recorded individually with a full audit trail. When a
student pays more than their balance, the excess is captured as an
`OverDraft` record — either carried forward as credit to the next
session or flagged for manual refund if the student has no next session.

**Models involved:** `FeeStructure` · `StudentFeeAccount` · `Payment` · `OverDraft`

---

## 🔗 How It Connects

```
Tclass + Session → FeeStructure (what the class owes)
     ↓
Student + Session → StudentFeeAccount (per-student ledger)
     ↓
StudentFeeAccount → Payment (individual transactions)
     ↓
Payment → OverDraft (if overpayment detected)
     ↓
OverDraft → carried to next StudentFeeAccount OR flagged for refund
```

---

## 📊 Diagrams

| Diagram                              | What it shows                           |
| ------------------------------------ | --------------------------------------- |
| [🔀 Flowchart](flowchart.md)         | Payment processing and overdraft logic  |
| [🔁 Sequence](sequence.md)           | How admin, models, and system interact  |
| [🏗️ Class Diagram](class-diagram.md) | Model structure and relationships       |
| [🗺️ User Journey](user-journey.md)   | What the student experiences end to end |

---

> 🔗 Back to [Project Index](../../../README.md)
> 🔗 Back to [Documentation Index](../../README.md)
