# ⚖️ Legal Obligations

> A reference document for institutions deploying this system.
> Covers Kenyan legal obligations beyond data protection,
> including education regulation, tax, accessibility, and cybersecurity.
>
> Read alongside [DATA_PROTECTION.md](DATA_PROTECTION.md) — together
> they cover the full compliance picture.

---

## 🏛️ Kenya-Specific Laws

### 📡 1. Kenya Information and Communications Act (KICA)

Governs electronic communications and transactions.

**What applies to this system:**

- Any email or SMS sent by the system (fee reminders, result notifications)
  must not be unsolicited — students must opt in to communications
- M-Pesa transaction records must be retained — satisfied by the `Payment` model
- The system must have identifiable ownership — institution name and
  contact details must be accessible to users at all times

---

### 💻 2. Computer Misuse and Cybercrimes Act, 2018

**What applies to developers and contributors:**

- Unauthorized access to computer systems is a criminal offence —
  the role-scoped admin directly addresses this at the application level
- Credentials must never be stored in plaintext — Django's `set_password()`
  satisfies this requirement
- Logging unauthorized access attempts is good practice and provides
  defensible evidence — install `django-axes`:

```bash
pip install django-axes
```

```python
# settings.py
INSTALLED_APPS += ['axes']
MIDDLEWARE += ['axes.middleware.AxesMiddleware']
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]
AXES_FAILURE_LIMIT = 5       # lock after 5 failed attempts
AXES_COOLOFF_TIME  = 1       # unlock after 1 hour
```

**What applies to the institution:**

- Cyberattacks must be reported to the **National KE-CIRT**
  (Communications Authority of Kenya)
- Students who attempt unauthorized access to other students' data
  can be prosecuted under this act — your audit logs are evidence

---

### 🎓 3. Universities Act, 2012 — Commission for University Education (CUE)

Universities operating in Kenya are regulated by the CUE.

**What applies:**

- Academic records must be maintained **accurately and permanently** —
  your `Result`, `Enrollment`, and `Reporting` models satisfy this
- Student transcripts and certificates are legal documents —
  the `Results` model feeds directly into these
- Admission records must be retained indefinitely —
  `Student`, `Enrollment`, and `Reporting` together satisfy this
- CUE may audit academic records at any time —
  the system must be able to generate clean exports on demand

**Recommended addition — CUE export endpoint:**

```python
# Export enrollment and results data in CUE-compatible format
class CUEExportView(LoginRequiredMixin, View):
    """Institution Admin only — exports academic records for CUE audit"""

    def get(self, request):
        if not request.user.is_superuser:
            return HttpResponse('Forbidden', status=403)
        # ... generate export
```

---

### 💸 4. Tax Obligations — Kenya Revenue Authority (KRA)

If the institution collects fees through this system:

**What applies:**

- Fee receipts are financial documents — `Payment.transaction_ref`
  serves as the reference number
- M-Pesa business payments may require **ETR (Electronic Tax Register)**
  integration for large institutions — consult KRA directly
- Financial records must be retained for **7 years** —
  do not delete `Payment`, `StudentFeeAccount`, or `OverDraft` records
- If the system generates invoices or receipts, they must meet
  KRA formatting requirements (institution PIN, date, amount, description)

**Retention rule already in DATA_PROTECTION.md:**

```
Financial records → 7 years minimum
```

---

### 🎓 5. Higher Education Loans Board (HELB)

Many Kenyan students are HELB beneficiaries. Institutions are required
to verify and report student enrollment status to HELB.

**What applies:**

- The `Reporting` model (semester check-in) is exactly what HELB needs
  to confirm a student is actively enrolled
- Consider adding HELB fields to the `Student` model:

```python
helb_beneficiary = models.BooleanField(default=False)
helb_ref_number  = models.CharField(max_length=50, null=True, blank=True)
```

- Add a HELB verification export endpoint so the institution can
  generate the required enrollment confirmation reports on demand

---

### ♿ 6. Persons with Disabilities Act, 2003 — NCPWD

**What applies to the student portal:**

- The portal must be accessible to students with disabilities
- Practical target: **WCAG 2.1 AA compliance**
- Minimum requirements:
  - Screen reader compatible HTML (semantic elements, ARIA labels)
  - Sufficient colour contrast ratios (4.5:1 for normal text)
  - Keyboard navigable — no mouse-only interactions
  - Form fields with proper labels
  - Error messages that are descriptive, not just colour-based

**Consider adding to `Student` model (with consent):**

```python
requires_accessibility_support = models.BooleanField(default=False)
accessibility_notes = models.TextField(null=True, blank=True)
```

---

### 👶 7. Minors — Students Under 18

The DPA requires parental/guardian consent for processing personal
data of minors (under 18). This is relevant for diploma and certificate
programmes that admit younger students.

**What applies:**

- Age check at registration — if student is under 18, flag for
  guardian consent before completing registration
- Emergency contact fields partially satisfy the guardian requirement
  but a formal consent record should be added

**Add to `Student` model:**

```python
@property
def is_minor(self):
    from datetime import date
    today = date.today()
    age = (
        today.year - self.date_of_birth.year -
        ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    )
    return age < 18

guardian_consent_obtained = models.BooleanField(default=False)
guardian_consent_date     = models.DateTimeField(null=True, blank=True)
```

---

## 🌍 If the System Goes Cross-Border

### GDPR (EU General Data Protection Regulation)

Only relevant if the institution enrolls EU citizens or hosts data
on servers within the EU.

Key difference from DPA: GDPR requires a **Data Processing Agreement (DPA)**
with every third-party processor (hosting provider, payment gateway, etc.).

---

### 🏥 Health Data (Future Modules)

If the system ever adds health records (disability details, medical
history, clinic visits, counselling records):

- These are **special category data** under both the DPA and the
  **Health Act, 2017**
- Separate explicit consent flow required — cannot be bundled with
  general registration consent
- Access must be restricted to authorised medical staff only —
  a separate role and admin scope would be required
- Never store health data in the existing `Student` model —
  create a separate `StudentHealthRecord` model with its own
  access controls

---

## 📋 Compliance Checklist

### Before Going Live

```
Legal & Regulatory
├── [ ] ODPC registration completed (institution)
├── [ ] DPO appointed and contact published
├── [ ] CUE registration current
├── [ ] KRA PIN registered for fee receipting
└── [ ] HELB institution registration confirmed

Technical
├── [ ] HTTPS enabled — no HTTP in production
├── [ ] django-axes installed and configured
├── [ ] py manage.py check --deploy passes clean
├── [ ] Automated database backups configured
├── [ ] Secret keys rotated from development values
└── [ ] Database not publicly accessible

Accessibility
├── [ ] Semantic HTML throughout
├── [ ] Colour contrast 4.5:1 minimum
├── [ ] All forms have proper labels
└── [ ] Keyboard navigation works end-to-end

Data
├── [ ] Privacy notice on registration form
├── [ ] Consent recorded for special category data
├── [ ] Data export endpoint working
├── [ ] Retention schedule documented and implemented
└── [ ] Staff trained on data handling
```

### Ongoing

```
Monthly
├── [ ] Review login attempt logs (django-axes)
└── [ ] Check for failed payment records needing reconciliation

Annually
├── [ ] Review and update privacy notice
├── [ ] ODPC registration renewal check
├── [ ] Staff data handling refresher training
├── [ ] Review data retention — delete what's past retention period
└── [ ] Accessibility audit

As needed
├── [ ] HELB enrollment verification exports each semester
├── [ ] CUE academic records export on audit request
└── [ ] KRA financial records export for tax filing
```

### If Something Goes Wrong

```
Data breach
├── [ ] Isolate affected system immediately
├── [ ] Document scope — what data, how many individuals
├── [ ] Notify ODPC within 72 hours
├── [ ] Notify affected individuals if high risk
└── [ ] Patch vulnerability before bringing system back online

Cyberattack
├── [ ] Preserve logs — do not wipe
├── [ ] Report to KE-CIRT (Communications Authority)
└── [ ] Engage institution legal counsel

Student complaint
└── [ ] Direct to ODPC — complaints@odpc.go.ke
```

---

## 📞 Key Regulatory Contacts

| Body       | Mandate                                   | Contact                                                  |
| ---------- | ----------------------------------------- | -------------------------------------------------------- |
| 🏛️ ODPC    | Data protection registration + complaints | [odpc.go.ke](https://odpc.go.ke) · complaints@odpc.go.ke |
| 💻 KE-CIRT | Cybersecurity incident reporting          | [ke-cirt.go.ke](https://ke-cirt.go.ke)                   |
| 🎓 CUE     | Academic records + university regulation  | [cue.or.ke](https://cue.or.ke)                           |
| 💰 HELB    | Student loan verification                 | [helb.co.ke](https://helb.co.ke)                         |
| 🧾 KRA     | Tax obligations + ETR                     | [kra.go.ke](https://kra.go.ke)                           |
| ♿ NCPWD   | Disability rights + accessibility         | [ncpwd.go.ke](https://ncpwd.go.ke)                       |

---

## 🔗 Related Documents

| Document                                                 | Description                                              |
| -------------------------------------------------------- | -------------------------------------------------------- |
| [DATA_PROTECTION.md](DATA_PROTECTION.md)                 | DPA compliance, student rights, consent, breach response |
| [docs/modules/auth/index.md](docs/modules/auth/index.md) | Role-based access control                                |
| [docs/actors.md](docs/actors.md)                         | Who can access what                                      |
| [README.md](README.md)                                   | Project overview                                         |

---

_This document should be reviewed whenever:_

- _New modules are added that collect additional personal data_
- _The system is deployed at a new institution_
- _Relevant legislation is amended_
- _A compliance incident occurs_

_Last reviewed: June 2026_
