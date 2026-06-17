# 📧 Email Generation Module

> How a registration number like `BSC/001/2024` becomes an institutional
> email address — and how to plug in a different format, or hand the
> whole decision off to an external API, without touching core code.
> Strategies only ever propose an address. They never check uniqueness
> and never write to the database — that responsibility stays entirely
> with `SchoolEmailGenerator`.

---

## 🗺️ Overview

```
SCHOOL_EMAIL_STRATEGY setting (string key / dotted path / API dict)
      ↓
SchoolEmailGenerator._resolve_strategy()     ← resolves the setting into a strategy instance
      ↓
strategy.generate(registration_number, domain)   ← proposes an email, touches nothing else
      ↓
SchoolEmailGenerator.generate_unique()        ← checks the DB, appends .2 .3 ... on collision
      ↓
caller saves the result onto Student.school_email
```

`SchoolEmailGenerator` is exposed as a ready-to-use global instance
(`email_generator`) so most call sites never need to construct one
themselves.

---

## 🏗️ Architecture

```
base/modules/email_generation/
├── __init__.py            # exports AbstractEmailGenerationStrategy, EmailGenerationResult, email_generator
├── base.py                 # the contract
├── generator.py             # SchoolEmailGenerator — resolution, uniqueness, the global instance
└── strategies/
    ├── builtin.py            # DefaultEmailStrategy, InitialsYearStrategy, NumericOnlyStrategy
    ├── api_strategy.py        # ApiEmailGenerationStrategy — delegates to an external API
    ├── examples/
    │   └── custom.py            # UOELDStrategy — institution-specific reference implementation
    └── contrib/
        └── __init__.py           # community-contributed strategies
```

---

## 🔄 Strategy Resolution Order

`SchoolEmailGenerator._resolve_strategy()` reads `SCHOOL_EMAIL_STRATEGY`
and walks through these cases in order:

| `SCHOOL_EMAIL_STRATEGY` is...                 | Resolves to                                                                                                              |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| a `dict`                                      | `ApiEmailGenerationStrategy` built from its `url` / `method` / `headers` / `timeout`                                     |
| a string matching a `BUILT_IN_STRATEGIES` key | the corresponding built-in class                                                                                         |
| any other string                              | treated as a dotted import path via `import_string()`; falls back to `DefaultEmailStrategy` on `ImportError`/`TypeError` |
| already an `AbstractEmailGenerationStrategy`  | used as-is                                                                                                               |
| unset, or anything else                       | `DefaultEmailStrategy`                                                                                                   |

> ⚠️ **`'api'` is not actually one of the built-in string keys.**
> It's documented alongside `default` / `initials_year` / `numeric_only`
> as a "built-in strategy," but `BUILT_IN_STRATEGIES` only contains those
> three. Setting `SCHOOL_EMAIL_STRATEGY = 'api'` (the bare string) falls
> into the dotted-import-path branch, fails `import_string('api')`, and
> silently resolves to `DefaultEmailStrategy` instead — no error, just
> the wrong strategy. To actually get `ApiEmailGenerationStrategy`, pass
> the full dict config, not the string `'api'`.

---

## 📐 The Contract

```python
class AbstractEmailGenerationStrategy(ABC):

    @abstractmethod
    def generate(self, registration_number: str, domain: str) -> EmailGenerationResult:
        """
        registration_number: e.g. 'BSC/001/2024'
        domain:              e.g. 'university.ac.ke'
        Must return an EmailGenerationResult. Must not raise.
        Must return the email in lowercase.
        """
        raise NotImplementedError

    def describe(self) -> str:
        """Shown in admin/management-command output. Override per strategy."""
        return self.__class__.__name__
```

Four rules every strategy is expected to follow:

1. **Never write to the DB inside `generate()`** — uniqueness is `SchoolEmailGenerator.generate_unique()`'s job alone.
2. **Never raise** — catch exceptions internally and return `EmailGenerationResult(success=False, message=...)`.
3. **Always return the email lowercase** — case-insensitive addresses are still stored as plain strings, so `CS001@x.com` and `cs001@x.com` would otherwise collide as "different" rows.
4. **Always use the `domain` parameter** — never hardcode a domain inside a strategy; the institution controls it via `SCHOOL_EMAIL_DOMAIN`.

### 📦 The dataclass

```python
@dataclass
class EmailGenerationResult:
    success:  bool
    email:    Optional[str] = None   # None if success=False
    message:  str = ""
    fallback: bool = False           # True if a local fallback ran instead of the primary method
```

---

## 🧰 Built-in Strategies

| Key             | Class                        | Example                                               |
| --------------- | ---------------------------- | ----------------------------------------------------- |
| `default`       | `DefaultEmailStrategy`       | `BSC/001/2024` → `bsc001@domain`                      |
| `initials_year` | `InitialsYearStrategy`       | `BSC/001/2024` → `bsc001.2024@domain`                 |
| `numeric_only`  | `NumericOnlyStrategy`        | `BSC/001/2024` → `0012024@domain`                     |
| _(dict config)_ | `ApiEmailGenerationStrategy` | delegates to an external API, falls back to `default` |

---

## 🛠️ Adding a New Strategy

### Step 1 — Decide where your file lives

Institution-specific, written for your own deployment:

```
base/modules/email_generation/strategies/your_institution.py
```

A reference implementation meant to help other institutions write their
own (the way `examples/custom.py` documents `UOELDStrategy`):

```
base/modules/email_generation/strategies/examples/your_institution.py
```

Community contribution:

```
base/modules/email_generation/strategies/contrib/your_strategy.py
```

### Step 2 — Implement the contract

```python
# base/modules/email_generation/strategies/your_institution.py

from base.modules.email_generation.base import (
    AbstractEmailGenerationStrategy,
    EmailGenerationResult,
)


class YourInstitutionStrategy(AbstractEmailGenerationStrategy):
    """
    BSC/001/2024 → s001-2024@domain
    """

    def generate(self, registration_number: str, domain: str) -> EmailGenerationResult:
        try:
            parts = registration_number.split('/')
            if len(parts) < 3:
                return EmailGenerationResult(
                    success=False,
                    message=f"Expected PROG/NUM/YEAR, got '{registration_number}'"
                )
            email = f"s{parts[1]}-{parts[2]}@{domain}".lower()
            return EmailGenerationResult(success=True, email=email)
        except Exception as e:
            return EmailGenerationResult(success=False, message=str(e))

    def describe(self):
        return "Your Institution format — BSC/001/2024 → s001-2024@domain"
```

### Step 3 — Point settings at it

No core code changes needed — a dotted import path is enough:

```python
# settings.py
SCHOOL_EMAIL_DOMAIN   = 'yourinstitution.ac.ke'
SCHOOL_EMAIL_STRATEGY = 'base.modules.email_generation.strategies.your_institution.YourInstitutionStrategy'
```

### Step 4 — (Optional) Promote it to a short key

If you'd rather configure it as `SCHOOL_EMAIL_STRATEGY = 'your_institution'`
instead of the full dotted path, add it to `BUILT_IN_STRATEGIES` in
`generator.py`. This is the one step that does touch core code, so it's
worth reserving for strategies you expect to reuse across more than one
deployment.

---

## 🔁 Uniqueness & Conflict Resolution

Strategies never check the database — `SchoolEmailGenerator` does that
after the fact:

```python
email_generator.generate_unique('BSC/001/2024')
# BSC001@domain        if free
# BSC001.2@domain      if BSC001@domain is taken
# BSC001.3@domain      if .2 is also taken
# ...
```

`is_unique()` runs a single `Student.objects.filter(school_email=...).exists()`
check; `generate_unique()` keeps incrementing a numeric suffix on the
local part until it finds a free one. This means the suffix logic is
shared across every strategy — a strategy only needs to get the _first_
proposed address right.

---

## 🚦 The Golden Rules

**1. `generate()` only proposes — it never persists or checks uniqueness**
Both of those stay the exclusive responsibility of `SchoolEmailGenerator`.

**2. Catch everything inside `generate()` — never let it raise**
Return `EmailGenerationResult(success=False, message=str(e))` instead.
A strategy that raises breaks `_resolve_strategy()`'s ability to fall
back cleanly.

**3. Lowercase the entire result, not just part of it**
See the `InitialsYearStrategy` caveat above for what happens when this
rule is only partially followed.

**4. Take `domain` as a parameter — never hardcode it**
Even an institution-specific strategy should stay portable to a domain
change without a code edit.

**5. Set `fallback=True` when a fallback path was used**
`ApiEmailGenerationStrategy` does this correctly when the API is
unreachable — it's the visible signal (in logs/admin) that a result came
from the safety net rather than the primary method.

---

## 🧪 Testing your strategy

```python
# tests/test_email_strategy.py
from django.test import TestCase
from base.modules.email_generation.strategies.your_institution import YourInstitutionStrategy


class YourInstitutionStrategyTest(TestCase):

    def setUp(self):
        self.strategy = YourInstitutionStrategy()

    def test_generate_success(self):
        result = self.strategy.generate('BSC/001/2024', 'inst.ac.ke')

        self.assertTrue(result.success)
        self.assertEqual(result.email, 's001-2024@inst.ac.ke')

    def test_generate_handles_malformed_input(self):
        result = self.strategy.generate('not-a-valid-format', 'inst.ac.ke')

        self.assertFalse(result.success)
        self.assertIsNone(result.email)

    def test_email_is_lowercase(self):
        result = self.strategy.generate('BSC/ABC/2024', 'INST.AC.KE')
        self.assertEqual(result.email, result.email.lower())
```

---

## 🔗 Where to Go Next

| Topic                           | Document                                     |
| ------------------------------- | -------------------------------------------- |
| 📰 News module                  | [News Module](news.md)                       |
| 🔌 ERP sync module              | [ERP Module](erp.md)                         |
| 💳 Payments module              | [Payments Module](payments.md)               |
| 🗃️ `Student.school_email` field | [Models Reference](../models.md)             |
| 📋 Generator & resolution logic | `base/modules/email_generation/generator.py` |

---

> 🔗 Back to [Documentation Index](../README.md)
