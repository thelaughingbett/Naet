# 🔐 Data Protection & Privacy

> This document explains how the system handles personal data,
> the legal framework it operates under, and the responsibilities
> of anyone deploying or contributing to this codebase.

---

## ⚖️ Legal Framework

This system is designed for use by Kenyan educational institutions and
operates under the **Kenya Data Protection Act, 2019 (DPA)** and is
subject to oversight by the **Office of the Data Protection Commissioner (ODPC)**.

Any institution deploying this system is a **data controller** under the
DPA and must register with the ODPC at [odpc.go.ke](https://odpc.go.ke)
before going live.

---

## 📋 What Personal Data This System Collects

### Standard Personal Data

| Category | Fields | Lawful Basis |
|---|---|---|
| 🪪 Identity | Full name, national ID, ID type, date of birth | Contractual necessity |
| 📧 Contact | Email, telephone, school email | Contractual necessity |
| 🏠 Address | County, sub-county, constituency, home address | Contractual necessity |
| 🎓 Academic | Registration number, class, year of study, results | Legal obligation |
| 💰 Financial | Fee account, payments, transaction references | Legal obligation |
| 🏥 Emergency | Emergency contact names, phones, relationships | Legitimate interest |
| 👨‍👩‍👧 Family | Father/mother names, ID numbers, dates of birth | Legal obligation |

### ⚠️ Special Category Data

The following fields are **special category data** under Section 46 of the DPA
and require **explicit consent** or a specific legal basis before collection:

| Field | Category | Requirement |
|---|---|---|
| `religion` | Religious belief | Explicit consent at registration |
| `ethnicity` | Ethnic origin | Explicit consent at registration |

> **For developers:** If your institution does not use these fields for any
> functional purpose, remove them. Every field you don't collect is a field
> you cannot be held liable for.

---

## 🧱 How the System Protects Personal Data

### Access Control

Personal data is scoped by role — no user sees more than their jurisdiction allows:

```
Institution Admin  → all data
School Admin       → own school's data only
Dept Admin         → own department's data only
Lecturer           → view-only, own department's students
Student            → own data only
```

See [docs/modules/auth/index.md](docs/modules/auth/index.md) for the full access matrix.

### Technical Measures

| Measure | Implementation |
|---|---|
| 🔑 Password hashing | Django's `set_password()` — bcrypt by default |
| 🆔 UUID primary keys | No sequential IDs exposed in URLs |
| 🔒 Role-based admin | `ScopedAdminMixin` restricts queryset per role |
| 📝 Admin audit log | Django admin logs all changes with user + timestamp |
| 🚫 Login protection | Add `django-axes` for brute force prevention |
| 🔐 HTTPS | Required in production — never deploy over HTTP |

### Recommended Production Settings

```python
# settings/production.py

SECURE_SSL_REDIRECT          = True
SECURE_HSTS_SECONDS          = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SESSION_COOKIE_SECURE        = True
CSRF_COOKIE_SECURE           = True
SECURE_BROWSER_XSS_FILTER    = True
X_FRAME_OPTIONS              = 'DENY'
```

---

## 👤 Student Data Rights

Under the DPA, students have the following rights over their personal data:

| Right | Description | How it's handled |
|---|---|---|
| 📥 Access | View all personal data held about them | Settings page + data export |
| ✏️ Rectification | Correct inaccurate data | Settings page |
| 🗑️ Erasure | Request deletion of their data | Deletion request workflow |
| 📦 Portability | Receive their data in a portable format | `/settings/export/` endpoint |
| 🚫 Objection | Object to processing for specific purposes | Contact data controller |

### Data Export Endpoint

Students can download all their personal data at:

```
GET /settings/export/
```

Returns a JSON file containing all personal, academic, and financial
data held about that student. This satisfies the **right to data portability**
under Section 26 of the DPA.

---

## 🤝 Consent

### What requires consent

- Collection of special category data (religion, ethnicity)
- Any processing beyond the original purpose of education delivery
- Marketing or communications beyond academic notices

### Consent fields on the Student model

```python
data_processing_consent  = models.BooleanField(default=False)
consent_date             = models.DateTimeField(null=True)
privacy_notice_version   = models.CharField(max_length=10, default='1.0')
```

Consent must be recorded at registration with a clear privacy notice
explaining what is being collected and why.

### Sample privacy notice text for registration

> *"By submitting this form, you agree to the collection and processing
> of your personal data by [Institution Name] for the purposes of
> administering your academic enrolment, fee management, and related
> institutional services. Your data is processed under the Kenya Data
> Protection Act, 2019. You have the right to access, correct, and
> request deletion of your data. Contact the Data Protection Officer
> at [dpo@institution.ac.ke] to exercise these rights."*

---

## 🗄️ Data Retention

| Data type | Retention period | Reason |
|---|---|---|
| Academic records | Indefinite | Legal obligation — proof of qualification |
| Financial records | 7 years | Kenya tax and audit requirements |
| Personal contact data | Duration of enrolment + 2 years | Legitimate interest |
| Special category data | Duration of enrolment | Consent-based — delete on withdrawal |
| Login/audit logs | 1 year | Security monitoring |

---

## 🚨 Data Breach Response

If a data breach occurs, the DPA requires notification to the ODPC
**within 72 hours** of becoming aware of it.

**Immediate steps:**
1. Isolate the affected system
2. Document what data was exposed and how many individuals affected
3. Notify the ODPC via [odpc.go.ke](https://odpc.go.ke)
4. Notify affected individuals if there is high risk to their rights
5. Review and patch the vulnerability

**Contact for reporting:**
- ODPC: [odpc.go.ke](https://odpc.go.ke)
- Email: complaints@odpc.go.ke

---

## 👨‍💻 Responsibilities by Role

### Institution (Data Controller)
- Register with ODPC before going live
- Appoint a Data Protection Officer (DPO)
- Maintain a Record of Processing Activities (ROPA)
- Conduct a Data Protection Impact Assessment (DPIA) for large-scale processing
- Ensure staff handling data are trained on the DPA

### Developers / Contributors
- Do not log or print personal data in plaintext
- Do not commit real student data to version control — use anonymised fixtures
- Do not add new personal data fields without documenting the lawful basis
- Do not bypass role-based access controls
- Run `py manage.py check --deploy` before any production deployment

### System Administrators
- Enable HTTPS — no exceptions
- Restrict database access to application server only
- Enable automated backups with encryption at rest
- Monitor and rotate secret keys periodically

---

## 🔗 Related Documents

| Document | Description |
|---|---|
| [docs/modules/auth/index.md](docs/modules/auth/index.md) | Role-based access control |
| [docs/actors.md](docs/actors.md) | Who can access what |
| [docs/models.md](docs/models.md) | Full field-by-field model reference |
| [README.md](README.md) | Project overview |

---

## 📞 Data Protection Officer Contact

> Fill in the institution's appointed DPO details before deploying.

```
Name:   [DPO Name]
Email:  dpo@institution.ac.ke
Phone:  +254 7XX XXX XXX
Office: [Physical address]
```

---

*This document should be reviewed and updated whenever:*
- *New personal data fields are added to the system*
- *The ODPC issues new guidance*
- *The system is deployed at a new institution*
- *A data breach occurs*

*Last reviewed: June 2026*
