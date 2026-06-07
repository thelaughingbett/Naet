# 🗃️ Database Schema

> The full entity relationship diagram for the School Management System.
> Every table, every relationship, all in one place.

---

## 📊 ER Diagram

```mermaid

---
title: Portal Entity Diagram
---
erDiagram
direction LR

User {
  name String
  gender String
  profile_pic Blob
  email Email
  is_active boolean
  is_staff boolean
  role enum
  is_activated boolean
}

Student{

  National_id string
  Date_Of_Birth DateTime

  Marital_Status Enum
  Nationality Enum
  Religion Enum
  Disability String
  Tribe String
  KCSE_YEAR dateTime
  Co-Curricular string[]
  KCSE_Index string

  Telephone_no string
  schoolEmail email
  County String
  Domicile string
  SubCounty string
  Constituency string
  Home_Adress String

  emargency_contact_name string
  emargency_contact_Phone string
  emargency_contact_Email string
  emargency_contact_Relationship string
  emargency_contact_Adress string

  registration_number string
  class Class
  stay enum
  hostel string(conditional-on-stay)
  enrolled date
  graduated date
  year_of_study string

  password_hash string

  enrolled_course Course[]

}

Lecturer {
  title string
  staff_number string
  department Department
  lecture_assignments curriculum[]

}

DeptAdmin{
  staff_number string
  department Department
}

SchoolAdmin {
  staff_number string
  department Department
}

InstitutionAdmin {
  staff_number string
  department Department
}

Programme {
  name string
  department Department
  school School
}

Course {
  name string
  department department
  year_of_study string
  lecturer_assigned Lecturer[]
  type enum(core-elective-commonUnit)
}

Department{
  DepartmentName string
}

School{
  SchoolName String
}

Reporting {
  student Student
  Session session
  reported_at date
  reported_via enum
}

Session {
  session enum
  academic_year datetime_range
}

Timetable{
  session Session
  lecturer Lecturer
  time datetime
  venue string
  course Course
  class tclass
}

fee_structure {
  programme Programme
  year_of_study date
  semester string
  class  Class(eg-com-22)
  data json(account-amount)
}

tclass {
  programme Programme
  class String
  students Student[]
}

curriculum {
  programme Programme
  course Course
  enrollemnents Student
  lecturer_assignments Lecturer
}

User || -- || Student : has
User || -- || Lecturer : has
User || -- || DeptAdmin : has
User || -- || SchoolAdmin : has
User || -- || InstitutionAdmin : has

Student }o -- || tclass : has
Programme || -- o{ tclass : has
Department || -- o{ Programme : has
School || -- o{ Department : has
Student }o -- o{ Reporting : has
Session }o -- o{ Reporting : has

Course }o -- || Department : has

Timetable }o -- o{ Session : has
Timetable }o -- o{ tclass : has
Timetable }o -- o{ Course : has

curriculum }o -- o{ Course : has
curriculum }o -- o{ Programme : has
curriculum }o -- o{ Student : has
curriculum }o -- o{ Lecturer : has

fee_structure }| -- o{ Programme : has
```

---

## 🔑 Key Relationships Explained

**👤 User → Profiles**
Every user has exactly one profile depending on their role.
A `Student` user has a `Student` profile, a `Staff` user becomes a `Lecturer`, an `Admin` becomes a `DeptAdmin`, `SchoolAdmin`, or `InstitutionAdmin`.

**🎓 Student → Class → Programme → Department → School**
The full academic hierarchy chain. A student belongs to a class, which belongs to a programme, which belongs to a department, which belongs to a school.

**💰 Fee Flow**
`FeeStructure` defines what a class owes per session →
`StudentFeeAccount` is the per-student ledger →
`Payment` records individual transactions →
`OverDraft` captures any overpayment for carry-forward or refund.

---

> 🔗 Back to [Project Index](../README.md)
> 🔗 Back to [Documentation Index](./README.md)
