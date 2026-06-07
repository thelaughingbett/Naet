# 🔁 Fees & Payments Sequence Diagram

> How admin, models, and system interact during payment processing.

---

## 💳 Payment Sequence

```mermaid
sequenceDiagram
    actor Admin
    participant PaymentAdmin
    participant Payment
    participant StudentFeeAccount
    participant OverDraft

    Admin->>PaymentAdmin: Submit payment
    PaymentAdmin->>StudentFeeAccount: Check is_cleared
    alt Account already cleared
        StudentFeeAccount-->>PaymentAdmin: Return early
        PaymentAdmin-->>Admin: No payment saved
    else Not cleared
        PaymentAdmin->>Payment: save()
        Payment->>StudentFeeAccount: Get balance
        alt Normal payment
            Payment->>StudentFeeAccount: amount_paid += amount
        else Overpayment
            Payment->>StudentFeeAccount: amount_paid += balance
            Payment->>OverDraft: Create(amount=excess, status=pending)
        end
        StudentFeeAccount-->>Admin: Account updated
    end
```

---

## ⚠️ Overdraft Processing Sequence

```mermaid
sequenceDiagram
    participant Session
    participant OverDraft
    participant StudentFeeAccount

    Session->>Session: rollover_academic_session()
    Session->>OverDraft: filter(status=pending)
    loop Each pending overdraft
        OverDraft->>StudentFeeAccount: Find next session account
        alt Next account exists
            OverDraft->>StudentFeeAccount: amount_paid += overdraft.amount
            OverDraft->>OverDraft: status = carried
        else No next account
            OverDraft->>OverDraft: status = refunded
        end
    end
```

---

> 🔗 Back to [Fees Module](index.md)
