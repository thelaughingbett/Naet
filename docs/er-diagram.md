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
  first_name String
  last_name String
  surname String
  gender String
  profile_pic Blob
  email Email
  is_active boolean
  is_staff boolean
  role enum
  is_activated boolean
}

Student{

  Marital_Status Enum
  number_of_children integer

  id_type enum
  National_id string

  religion string
  nationality string
  ethnicity string

  date_of_birth date
  place_of_birth string

  telephone_no string
  school_email email

  domicile string
  county String
  sub_county string
  constituency string
  division string
  location string

  home_address string

  disabled boolean


  registration_number string
  class tclass
  stay enum

  enrolled date
  graduated date

}

SpouseRecords {
  name String
  phone string
  email string
  occupation string
}

Student || -- || SpouseRecords : has

ParentGuardian{
  student Student
  relation enum
  name String
  id_type enum
  id_no String
  date_of_birth DateTime
}

EmergencyContact {

  name string
  Phone string
  Email string
  Relationship enum
  Adress string
}

Lecturer {
  title string
  staff_number string
  department Department
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
  degree_type enum
  current_class Tclass
  duration_years integer
  semesters_per_year integer
  department Department
}

Course {
  name string
  course_code string
  department department
  offered  string
  type enum(core-elective-commonUnit)
  credits integer
  prerequisites Course[]
}

Department{
  school School
  DepartmentName string
}

School{
  School_name String
  active_session Session
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
  semseter integer
  start_date date
  end_date date
  is_active boolean
}

Timetable{
  session Session
  lecturer Lecturer
  day enum
  time enum
  venue venue
  curriculum curriculum
  class tclass
}

Timetable }o -- || Venue : has

ExamSession{
  curriculum curriculum
  exam_type enum
  date date
  time_slot  enum
}

ExamVenue{
  exam_session ExamSession
  venue venue
  invigilator Lecturer
}

ExamClash{
  student Student
  session_a ExamSession
  session_b ExamSession
  resolved boolean
}

Venue{
  capacity integer
  venue_name string
  floor integer
  ramps boolean
}

ExamCard{
  student Student
  session Session
  serial_number string
  is_active boolean
  issued_at datetime
  last_printed_at datetime
}

ExamSession || -- || curriculum : has
ExamSession || -- |{ ExamVenue : has
ExamVenue || -- |{ Lecturer : has

ExamClash }o -- || Student : has
ExamCard }o -- || Student : has
ExamCard }o -- || Session : has


fee_structure {
  session Session
  class  tclass
  Breakdown json(account-amount)
}

StudentFeeAccount {
  student Student
  fee_structure fee_structure
  amount_paid  decimal
}

Payment{
  account StudentFeeAccount
  amount decimal
  method enum
  transaction_ref string
  status enum
  provider_ref string
  phone_number string
  paid_at datetime
  initiated_at datetime
}

fee_structure || -- o{ StudentFeeAccount : has
StudentFeeAccount }o -- || Student : has
Payment }o -- || StudentFeeAccount : has


tclass {
  programme Programme
  class_name String
  year_of_study integer
  graduated date
}

curriculum {
  class Tclass
  course Course
  enrollemnents Student
  professor Lecturer[]
  session Session
}

Enrollment{
  student Student
  curriculum curriculum
  status enum
  results Results[]
  approved_by User
}

Result{
  enrollment Enrollment
  type enum
  score decimal
  title string
  entered_by User
}


DefermentDocument{
  deferment Deferment
  file File
  original_name string
  uploaded_at datetime
}

Deferment{
  student Student
  session_deferred Session
  session_returning Session
  reason enum
  reason_detail String
  status enum
  request_status enum
  approved_by User
  reinstated_at DateTime
}

HostelListing{
  name String
  badge enum
  location string
  distance string
  price_per_month integer
  room_type enum
  has_wifi boolean
  has_meals boolean
  has_laundry boolean
  has_gym boolean
  has_parking boolean
  has_kitchen boolean
  has_study_rooms boolean
  has_lounge boolean
  has_bike_storage boolean
  has_ethernet boolean
  wifi_note string

  phone string
  email string
  is_published boolean
  sort_order integer

}

CourseEvaluation{
  enrollment Enrollment
  rating integer
  comments String
}

LecturerEvaluation {
  enrollment Enrollment
  lecturer lecturer
  rating integer
  comments String
}

Hostel {
  name string
  gender enum
  warden HostelWarden
}

Room{
  hostel Hostel
  room_number string
  room_type enum
  capacity integer
  floor integer
  is_active boolean
  price_per_semester integer
}

HostelAllocation{
  student Student
  room Room
  session Session
  status enum
  allocated_at datetime
  is_active boolean
  move_in_date date
  notes string
}


HostelEvaluation {
  allocation HostelAllocation
  cleanliness_rating integer
  security_rating integer
  water_supply_rating integer
  electricity_rating integer
  noise_levels_rating integer
  maintenance_rating integer
  rating integer
  comments String
}

Hostel || -- o{ Room : has
HostelAllocation }o -- || Room : has
Student || -- o{ HostelAllocation : has
HostelEvaluation || -- || HostelAllocation : has

CourseEvaluation }o -- || Enrollment : has

LecturerEvaluation }o -- || Enrollment : has
LecturerEvaluation }o -- || Lecturer : has

User || -- || Student : has
User || -- || Lecturer : has
User || -- || DeptAdmin : has
User || -- || SchoolAdmin : has
User || -- || InstitutionAdmin : has

Lecturer || -- || Department : has
Department || -- || DeptAdmin : has
School || -- || SchoolAdmin : has

Student }o -- || tclass : has
Programme || -- o{ tclass : has
Department || -- o{ Programme : has
School || -- o{ Department : has
Student }o -- o{ Reporting : has
Session }o -- o{ Reporting : has

Course }o -- || Department : has

Timetable }o -- o{ Session : has
Timetable }o -- o{ curriculum : has

curriculum }o -- o{ Lecturer : has

curriculum }| -- || tclass : has
curriculum  }o -- || Course : has
Enrollment }o -- || curriculum : has
curriculum }o -- || Session : has
Enrollment || -- o{ Result : has
Enrollment }o -- || Student : has

Student }o -- o{ ParentGuardian : has
Student }o -- o{ EmergencyContact : has

fee_structure }| -- o{ tclass : has
fee_structure }| -- o{ Session : has

Deferment }o -- || Student : has
Deferment || -- o{ DefermentDocument : has
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
`Payment` records individual transactions

---

> 🔗 Back to [Project Index](../README.md)
> 🔗 Back to [Documentation Index](./README.md)
