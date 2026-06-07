# 🏗️ Fees & Payments Class Diagram

> Model structure and relationships in the fee module.

---

```mermaid
classDiagram
    class FeeStructure {
        +UUID record_id
        +JSON breakdown
        +total_amount() Decimal
    }
    class StudentFeeAccount {
        +UUID record_id
        +Decimal amount_paid
        +amount_billed() Decimal
        +balance() Decimal
        +is_cleared() bool
    }
    class Payment {
        +UUID record_id
        +Decimal amount
        +String method
        +String transaction_ref
        +DateTime paid_at
        +save()
    }
    class OverDraft {
        +UUID record_id
        +Decimal amount
        +String status
        +process()
    }
    class Student {
        +UUID record_id
        +String registration_number
    }
    class Session {
        +UUID record_id
        +String academic_year
        +String semester
        +bool is_active
    }
    class Tclass {
        +UUID record_id
        +String class_name
    }

    FeeStructure --> Tclass : tclass
    FeeStructure --> Session : session
    StudentFeeAccount --> Student : student
    StudentFeeAccount --> Session : session
    StudentFeeAccount --> FeeStructure : fee_structure
    StudentFeeAccount "1" --> "many" Payment : payments
    StudentFeeAccount "1" --> "many" OverDraft : overdrafts
    Payment --> OverDraft : triggers on overpayment
    OverDraft --> StudentFeeAccount : applied_to
```

---

## 📊 OverDraft Status Reference

| Status        | Meaning                                       |
| ------------- | --------------------------------------------- |
| ⏳ `pending`  | Just recorded, not yet processed              |
| ✅ `carried`  | Applied as credit to next session fee account |
| 💸 `refunded` | Flagged for manual refund                     |

---

> 🔗 Back to [Fees Module](index.md)
