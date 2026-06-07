# 🗺️ Fees & Payments User Journey

> What the student and admin experience through the fee payment process.

---

## 🎓 Student Journey

```mermaid
journey
    title Student Fee Payment Journey
    section Semester Start
      Student reports for semester: 5: Student
      Fee account auto-created: 3: System
      Student checks fee balance: 4: Student
    section Payment
      Student initiates M-Pesa payment: 5: Student
      Admin records payment in system: 4: Admin
      Student receives confirmation: 5: Student
    section Clearance
      Student checks clearance status: 4: Student
      Student cleared for exams: 5: Student
```

---

## 👨‍💼 Admin Journey

```mermaid
journey
    title Admin Fee Management Journey
    section Setup
      Create FeeStructure for class: 4: SchoolAdmin
      Set breakdown amounts: 4: SchoolAdmin
      Accounts auto-created on reporting: 3: System
    section Processing Payments
      Receive payment proof from student: 3: Admin
      Record payment in system: 4: Admin
      Verify transaction reference: 4: Admin
      Confirm account updated: 5: Admin
    section End of Session
      Review pending overdrafts: 3: Admin
      Process session rollover: 4: Admin
      Overdrafts carried or flagged: 3: System
```

---

> 🔗 Back to [Fees Module](index.md)
