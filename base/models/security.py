from django.db import models
from django.core.exceptions import ValidationError

from base.models import User, BaseModelMixin

# --- SECURITY EVENT TIER LISTS ---
AUDIT_ACTION_CHOICES = [
    ('ACCESS', 'Read / View Sensitive Data Profile'),
    ('CREATE', 'Insert / Provision New Entity Record'),
    ('UPDATE', 'Modify / Mutate Existing Row State'),
    ('DELETE', 'Purge / Delete Data Instance'),
    ('EXPORT', 'Mass CSV/PDF Bulk Data Extract Download'),
    ('AUTH_LOGIN', 'Successful System Security Authentication'),
    ('AUTH_FAIL', 'Failed Authentication / Unauthorized Breach Attempt'),
]


class SecurityAuditTrail(BaseModelMixin):
    """
    Centralized, append-only system access log ledger.
    Mandatory under the Kenya Data Protection Act (ODPC Compliance) for tracking
    PII (Personally Identifiable Information) touchpoints.
    """
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # User Context (Null handles anonymous attempts or unauthenticated firewall blocks)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_audit_logs'
    )
    username_snapshot = models.CharField(
        max_length=150,
        blank=True,
        help_text="Preserves actor identity even if the User account is later deleted from the register."
    )

    # Network Footprint Variables
    ip_address = models.GenericIPAddressField(db_index=True)
    user_agent = models.TextField(
        blank=True,
        help_text="Tracks browser signature, device profile, or API client type."
    )

    # The Payload Vector (What action was executed)
    action_type = models.CharField(
        max_length=15,
        choices=AUDIT_ACTION_CHOICES,
        db_index=True
    )

    # The Resource Locator Pointer (Which object model row was touched)
    target_model = models.CharField(
        max_length=100,
        db_index=True,
        help_text="The target database table name (e.g., 'Student', 'StudentMedicalProfile', 'Complaint')."
    )
    record_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="The primary key or identification string of the entity row touched."
    )

    # Operational Log context
    action_summary = models.TextField(
        help_text="Human-readable technical summary of the security event footprint."
    )

    class Meta:
        verbose_name = "Security Audit Log"
        verbose_name_plural = "Security Audit Logs"
        ordering = ['-timestamp']

        # Hard lock database controls to prevent modification of written lines
        permissions = [
            ("can_view_security_logs",
             "Can view centralized system security audit logs"),
        ]

    def clean(self):
        """
        Append-Only Enforcement: Blocks database modifications via application code
        once a row payload is signed off and committed.
        """
        if self.pk:
            raise ValidationError(
                "Security Compliance Infraction: Audit log trails are strictly append-only and immutable.")

    def save(self, *args, **kwargs):
        # Cache username state string safely before committing row IO loops
        if self.user and not self.username_snapshot:
            self.username_snapshot = self.user.username
        super().save(*args, **kwargs)

    def __str__(self):
        actor = self.username_snapshot if self.username_snapshot else "ANONYMOUS"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {actor} -> {self.action_type} on {self.target_model}"
