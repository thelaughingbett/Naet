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

### 3.1 Complaint Routing

```mermaid
flowchart TB
    A[Student files complaint]
    A --> B{Category?}

    B -->|Academic| C[HOD / Lecturer<br/>Department level]
    B -->|Harassment| D[Dean of Students<br/>direct — priority forced Critical]
    B -->|Facilities / Administrative /<br/>Catering / Other| E[School Student Rep]

    E --> F[Rep routes to facility head<br/>e.g. hostel warden, librarian]

```

### 3.2 Complaint Escalation Ladder

```mermaid

flowchart LR
    subgraph Academic["Academic track"]
        A1[Department:<br/>HOD / Lecturer]
        A2[School: Dean]
        A3[Dean of Students]
        A4[Registrar]
        A5[Senate]
        A1 -->|SLA breached| A2 -->|SLA breached| A3 -->|SLA breached| A4 -->|SLA breached| A5
    end

    subgraph Ops["Facilities / Administrative /<br/>Catering / Other track"]
        B1[School Student Rep]
        B2[Facility head<br/>warden, librarian, etc.]
        B3[Dean of Students]
        B4[Senate]
        B1 --> B2
        B2 -->|not acted on| B3 -->|SLA breached| B4
    end

    subgraph Harassment["Harassment track"]
        C1[Dean of Students<br/>direct entry]
        C2[Senate]
        C1 -->|not acted on| C2
    end

```

### 3.3 Complaint Escalation Trigger

```mermaid
flowchart TB
    A[Complaint sitting at<br/>current level]
    A --> B{Resolved within this<br/>category's SLA window?}

    B -->|Yes| C[Marked Resolved<br/>resolution_remarks required]

    B -->|No, SLA expired| D[System auto-escalates<br/>to next level]
    D --> E[Priority auto-raised<br/>one tier]

    A --> F{Handler manually<br/>escalates early?}
    F -->|Yes| G[Escalating user<br/>sets the priority]

    E --> H[Moves to next level<br/>in that category's ladder]
    G --> H
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

## 13. Enrollment

```mermaid

flowchart TB
    subgraph Student["🧑 Student"]
        A[Reports to school<br/>for the session]
        D[Sees electives<br/>offered for programme]
        E[Registers for<br/>an elective]
    end

    subgraph System["⚙️ System"]
        B[Auto-enrolls into Core /<br/>Common units for their year<br/>— reads Syllabus]
        C[Publishes elective list<br/>for programme + year]
        F[Creates enrollment<br/>status = pending]
    end

    subgraph Reviewer["🎓 HOD / Course Lecturer"]
        G[Reviews elective<br/>registration request]
        H{Approve?}
        I[Enrollment approved<br/>approval_method = manual]
        J[Enrollment rejected]
    end

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H -->|Yes| I
    H -->|No| J

```

---

## 14. Results

```mermaid
flowchart TB
    subgraph Lecturer["👨‍🏫 Lecturer"]
        A[Enters CAT / Assignment /<br/>Quiz score]
        B[Enters Practical /<br/>Exam score]
        Q[Reviews disputed result<br/>re-submits score]
    end

    subgraph ExamDept["🏢 Exam Department"]
        C[Enters exam score<br/>via exam portal]
    end

    subgraph System["⚙️ System"]
        D[Auto-publishes result<br/>state = published]
        Emod[Routes result to<br/>moderation queue]
        F[Notifies student<br/>result available / updated]
    end

    subgraph Approver["🎓 Dean / HOD / Exam Dept"]
        G[Reviews & moderates<br/>score]
        H{Approve?}
        I[Marks result<br/>state = published]
        J[Sends back to lecturer<br/>state = disputed]
        M[Receives student's<br/>dispute]
        N{Resolve directly?}
        O[Resolves dispute &<br/>updates result]
        P[Forwards dispute to<br/>lecturer for review]
    end

    subgraph Student["🧑 Student"]
        K[Views published result]
        L[Disputes result]
    end

    A --> D --> F
    B --> Emod
    C --> Emod
    Emod --> G --> H
    H -->|Yes| I --> F
    H -->|No| J --> B

    F --> K --> L --> M
    M --> N
    N -->|Yes, resolves it| O --> F
    N -->|No, needs lecturer input| P --> Q --> Emod
```

---

## 15. Graduation Track

```mermaid
flowchart TB
subgraph System["⚙️ System"]
A[Result published<br/>state = published]
B[Recalculates DegreeAudit:<br/>credits_completed, gpa]
C{credits_completed ≥<br/>programme's total_credits_required?}
D[DegreeAudit.result stays<br/>on_track / deficient]
E[DegreeAudit.result = eligible]
F[Creates / updates Graduation<br/>status = nominated]
end

    subgraph HOD["🎓 Dean / HOD"]
        G[Reviews nomination]
        H{Verify?}
        I[Graduation.status = verified]
        J[Returns nomination<br/>for correction]
    end

    subgraph Registrar["🏛️ Registrar"]
        K[Reviews verified nomination]
        L{Approve?}
        M[Graduation.status = approved]
        N[Sends back to HOD<br/>with remarks]
    end

    A --> B --> C
    C -->|No| D
    C -->|Yes| E --> F --> G
    G --> H
    H -->|Yes| I --> K
    H -->|No| J --> F
    K --> L
    L -->|Yes| M
    L -->|No| N --> G

```

### 16 Exam

```mermaid
flowchart TB
    subgraph PaperSetting["📝 Lecturer / Examiner"]
        A[QuestionPaper created<br/>status = draft]
        B[Submits paper<br/>status = submitted]
    end

    subgraph Moderation["🔍 Moderator"]
        C[QuestionPaperModeration<br/>reviews & comments]
        D{Approved?}
        E[Paper status = moderated]
        F[Paper status = rejected<br/>returned to setter]
    end

    subgraph ExamDay["🏫 Exam Day — Invigilator"]
        G[Student sits ExamSession]
        H[ExamAttendance recorded]
        I{Status}
        J[Present]
        K[Absent]
        L[Malpractice reported]
    end

    subgraph Grading["📊 Grading — Lecturer / System"]
        M[Result entered per type<br/>CAT / Exam / Assignment...]
        N[Result.state = published]
        O[Enrollment.finalize_grade<br/>freezes graded_score, is_passed]
    end

    subgraph Reval["⚖️ Revaluation — Student / Exam Dept"]
        P[Student files<br/>RevaluationRequest]
        Q[status = under_review]
        R{Marks changed?}
        S[status = marks_changed<br/>Enrollment.regrade]
        T[status = marks_unchanged]
    end

    subgraph Backlog["🔁 Backlog — Student"]
        U{Enrollment.is_passed?}
        V[BacklogRegistration<br/>attempt_number += 1]
    end

    subgraph Registrar["🏛️ Registrar"]
        W[GradeCard generated<br/>sgpa / cgpa]
        X[TranscriptRequest<br/>requested → processing → issued]
        Y[Certificate issued<br/>bonafide / provisional / ...]
    end

    A --> B --> C --> D
    D -->|Yes| E
    D -->|No| F --> A
    E --> G

    G --> H --> I
    I --> J --> M
    I --> K
    I --> L

    M --> N --> O
    O --> U
    U -->|No| V --> G
    U -->|Yes| W

    N --> P
    P --> Q --> R
    R -->|Yes| S --> O
    R -->|No| T

    W --> X
    W --> Y
```

---

> 🔗 Back to [Models Reference](models-reference.md)
> 🔗 Back to [ER Diagram](er-diagram.md)
> 🔗 Back to [Project Index](../README.md)
