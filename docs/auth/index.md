# 🔑 Auth & Access Module

> Login flow, role-based permissions, and how each user's
> view of the system is automatically scoped to their jurisdiction.

---

## 📋 Overview

Authentication is email-based using a custom `AbstractBaseUser`.
On login, Django loads the user's group permissions which were
auto-assigned when the user was created based on their `role` field.

Access is enforced at two levels:

- **Model level** — which models appear in the admin sidebar
- **Row level** — which records within those models the user can see

**Models involved:** `User` · `Student` · `Lecturer` · `DeptAdmin` · `SchoolAdmin` · `InstitutionAdmin`

**Django components:** `Group` · `Permission` · `ScopedAdminMixin`

---

## 📊 Diagrams

| Diagram                            | What it shows                            |
| ---------------------------------- | ---------------------------------------- |
| [🔀 Flowchart](flowchart.md)       | Login flow and sidebar rendering         |
| [🔁 Sequence Diagram](sequence.md) | How permissions are assigned and checked |
| [🗺️ User Journey](user-journey.md) | What each role experiences in the admin  |

---

## ⚡ Key Behaviours

- Groups and permissions are created automatically on `post_migrate`
- Users are assigned to the correct group on creation via `post_save`
- `ScopedAdminMixin.get_queryset()` filters rows based on the user's profile
- `has_*_permission()` methods control what actions are available per model

---

## 🔑 Role Hierarchy

```
Institution Admin  →  full access
School Admin       →  own school's data
Dept Admin         →  own department's data
Lecturer           →  view only, own department's students
Student            →  no admin access
```

---

> 🔗 Back to [Project Index](../../../README.md)
> 🔗 Back to [Documentation Index](../../README.md)
