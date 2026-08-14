# 🔄 Role-Based Workflows

> How each role actually moves through the system — Mermaid flowcharts,
> one per domain, following the same breakdown as the role walkthrough.
> Diamonds are decision/approval gates; model and method names in node
> labels map directly to what's in the codebase.

---

## 1. Student Lifecycle (cross-role, end to end)

The spine everything else hangs off — admission through graduation, with
the roles that touch each stage.

```mermaid
flowchart TD
    classDef student fill:#ffe3c2,stroke:#e08a2e,color:#000
    classDef staff fill:#cfe2ff,stroke:#4a7fd6,color:#000
    classDef decision fill:#fff3b0,stroke:#c9a300,color:#000
    classDef finance fill:#e0e0e0,stroke:#888,color:#000

    A["Application submitted"]:::student
    B{"Reviewed by\nAdmissions"}:::decision
    C["Application.status = 'enrolled'\n→ Student record created"]:::staff
    D["Reporting — check-in\nfor the session"]:::student
    E["Enrollment per Curriculum\n(core/common auto-approved)"]:::student
    F{"Elective?"}:::decision
    G["HOD.approve()"]:::staff
    H["StudentFeeAccount billed\nagainst FeeStructure"]:::finance
    I["Payment.confirm()\n/ Charge / Refund / ScholarshipAward"]:::finance
    J["Result entries accumulate\neach Curriculum"]:::staff
    K["DegreeAudit\neligibility check"]:::staff
    L{"Eligible?"}:::decision
    M["Graduation → Diploma\n→ Convocation"]:::staff

    A --> B
    B -- rejected --> A
    B -- accepted --> C
    C --> D --> E --> F
    F -- no --> H
    F -- yes --> G --> H
    H --> I
    I --> J --> K --> L
    L -- not yet --> J
    L -- yes --> M
```

---

## 2. Academic Staffing & Approval Chain

Lecturer → HOD → Dean/Director — teaching assignment, elective
enrollment, and complaint escalation all share this ladder.

```mermaid
flowchart TD
    classDef lecturer fill:#d3f2d3,stroke:#4caf50,color:#000
    classDef hod fill:#cfe2ff,stroke:#4a7fd6,color:#000
    classDef dean fill:#b3c7f7,stroke:#2f56b0,color:#000
    classDef decision fill:#fff3b0,stroke:#c9a300,color:#000

    A["LecturerAssignment\non a Curriculum entry"]:::lecturer
    B["Shows up on Timetable"]:::lecturer
    C["DailyClassExecution\nsigned off each session"]:::lecturer
    D["Result entered\nper Enrollment"]:::lecturer

    E["AcademicAppointment\nappointment_type='hod'"]:::hod
    F["Enrollment.approve()\nfor department electives"]:::hod
    G["Curriculum / LecturerAssignment\nstaffing for dept courses"]:::hod
    H["ComplaintEscalationHistory\nfirst tier"]:::hod

    I["Dean / Director\n(School-scoped appointment)"]:::dean
    J["ComplaintEscalationHistory\nnext tier"]:::dean
    K{"Resolved\nat School level?"}:::decision
    L["Escalates to Registrar"]:::dean

    A --> B --> C --> D
    E --> F
    E --> G
    H --> I --> J --> K
    K -- no --> L
    K -- yes --> J
```

---

## 3. Complaint / Grievance Escalation Chain

The same ladder as above, generalized — this is what
`ComplaintEscalationHistory` actually encodes.

```mermaid
flowchart LR
    classDef step fill:#e0e0e0,stroke:#888,color:#000
    classDef decision fill:#fff3b0,stroke:#c9a300,color:#000

    A["Complaint filed\nby Student"]:::step
    B["Department\n(HOD)"]:::step
    C{"Resolved?"}:::decision
    D["School\n(Dean)"]:::step
    E{"Resolved?"}:::decision
    F["Division\n(Registrar)"]:::step
    G{"Resolved?"}:::decision
    H["Senate /\nExternal (VC/DVC)"]:::step

    A --> B --> C
    C -- no --> D
    C -- yes --> Z["Complaint.status='Resolved'"]
    D --> E
    E -- no --> F
    E -- yes --> Z
    F --> G
    G -- no --> H
    G -- yes --> Z
    H --> Z
```

---

## 4. Student Fee Billing & Payment

```mermaid
flowchart TD
    classDef finance fill:#e0e0e0,stroke:#888,color:#000
    classDef decision fill:#fff3b0,stroke:#c9a300,color:#000
    classDef gl fill:#d3c2ff,stroke:#6a3fd6,color:#000

    A["FeeStructure + FeeStructureItem\nper class/session"]:::finance
    B["StudentFeeAccount\ncreated for student"]:::finance
    C["Payment initiated"]:::finance
    D{"Confirmed by\nwebhook?"}:::decision
    E["Payment.confirm()"]:::finance
    F["JournalEntry.for_payment()\nDr Cash · Cr Receivable"]:::gl
    G{"Overpaid?"}:::decision
    H["Refund.approve()\n→ mark_completed()"]:::finance
    I["JournalEntry.for_refund()"]:::gl
    J["Charge added\n(fine / late fee)"]:::finance
    K["ScholarshipAward.disburse()"]:::finance
    L["StudentFeeAccount.balance\nupdated (derived, not stored)"]:::finance

    A --> B --> C --> D
    D -- pending --> D
    D -- yes --> E --> F --> L
    B --> J --> L
    B --> K --> L
    L --> G
    G -- yes --> H --> I
    G -- no --> M["is_cleared"]
```

---

## 9. Exams — Coordinator to Director

```mermaid
flowchart TD
    classDef coord fill:#d3f2d3,stroke:#4caf50,color:#000
    classDef director fill:#b3c7f7,stroke:#2f56b0,color:#000
    classDef decision fill:#fff3b0,stroke:#c9a300,color:#000

    A["Exams Coordinator\n(AcademicAppointment, dept-scoped)"]:::coord
    B["ExamSession prepped\nper Curriculum"]:::coord
    C["Invigilators nominated"]:::coord
    D["Director of Examinations\n(AdministrativeStaff, institution-wide)"]:::director
    E["Consolidated timetable\napproved"]:::director
    F["detect_all_clashes()"]:::director
    G{"ExamClash\nfound?"}:::decision
    H["Clash resolved"]:::director
    I["ExamVenue + \nExamInvigilatorAssignment staffed"]:::director
    J["ExamCard.generate_serial()\nissued to students"]:::director

    A --> B --> C --> D --> E --> F --> G
    G -- yes --> H --> F
    G -- no --> I --> J
```

---

## 10. Clubs — Membership to Event

```mermaid
flowchart TD
    classDef student fill:#ffe3c2,stroke:#e08a2e,color:#000
    classDef exec fill:#d3f2d3,stroke:#4caf50,color:#000
    classDef patron fill:#cfe2ff,stroke:#4a7fd6,color:#000
    classDef decision fill:#fff3b0,stroke:#c9a300,color:#000

    A["Student applies via\nClubRecruitmentDrive"]:::student
    B["ClubMembership\nstatus='pending'"]:::student
    C{"Exec approves?"}:::decision
    D["ClubMembership.approve()"]:::exec
    E["ClubLeadershipPosition\nheld by active member"]:::exec
    F["ClubEvent created"]:::exec
    G["submit_for_approval()"]:::exec
    H{"Dean of Students\napproves?"}:::patron
    I["ClubEvent.approve()"]:::patron
    J["ClubEventAttendance\ntracked"]:::exec
    K["ClubTransaction\nrecorded against ClubBudget"]:::exec
    L["ClubActivityReport\nsubmitted"]:::exec

    A --> B --> C
    C -- no --> D2["reject()"]
    C -- yes --> D --> E
    E --> F --> G --> H
    H -- no --> G
    H -- yes --> I --> J
    F --> K --> L
```

---

## 11. Student Council — Election to Governance

```mermaid
flowchart TD
    classDef council fill:#ffe3c2,stroke:#e08a2e,color:#000
    classDef decision fill:#fff3b0,stroke:#c9a300,color:#000

    A["Election created\nfor CouncilTerm"]:::council
    B["ElectionPosition\ndefined per seat"]:::council
    C["Candidate nominated"]:::council
    D{"Vetted &\napproved?"}:::decision
    E["Voting opens"]:::council
    F["Vote cast\n(one per student per seat)"]:::council
    G["Election.declare_winners()"]:::council
    H["CouncilPosition\ninstalled"]:::council
    I["CouncilProposal\ntabled by position holder"]:::council
    J["ProposalSupport\nsignatures collected"]:::council
    K{"decided_by\napproves?"}:::decision
    L["Grievance submitted\nby student"]:::council
    M["assigned_to relevant\nportfolio (e.g. Welfare Sec)"]:::council
    N["GrievanceUpdate\nlogged until resolved"]:::council

    A --> B --> C --> D
    D -- rejected --> C
    D -- approved --> E --> F --> G --> H
    H --> I --> J --> K
    K -- rejected --> I
    L --> M --> N
```

---

## 12. Hostel Allocation

```mermaid
flowchart TD
    classDef student fill:#ffe3c2,stroke:#e08a2e,color:#000
    classDef warden fill:#cfe2ff,stroke:#4a7fd6,color:#000
    classDef decision fill:#fff3b0,stroke:#c9a300,color:#000

    A["Student requests\nhostel room"]:::student
    B{"Room capacity\navailable?"}:::decision
    C["HostelAllocation\ncreated"]:::warden
    D["Waitlisted"]:::warden
    E["Session ends"]:::student
    F["HostelEvaluation\nsubmitted"]:::student
    G["Warden reviews\nfeedback"]:::warden

    A --> B
    B -- no --> D
    B -- yes --> C --> E --> F --> G
```

---

> 🔗 Back to [Models Reference](models-reference.md)
> 🔗 Back to [ER Diagram](er-diagram.md)
> 🔗 Back to [Project Index](../README.md)
