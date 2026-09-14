from datetime import timezone

from django.apps import apps
from django.contrib.auth.models import BaseUserManager
from django.db import models

from base.models.staff import StaffProfile


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        # these guards make createsuperuser fail loudly rather than silently
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class DeferredStudentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deferred=True)


class ResidentStudentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(stay='resident')


class GraduatedStudentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(graduated__isnull=False)


# staff
class StaffQuerySet(models.QuerySet):
    """Reusable queryset methods for individual staff child tables."""

    def active(self):
        """Returns only active staff members."""
        return self.filter(is_active=True)

    def permanent(self):
        """Returns full-time permanent staff."""
        return self.filter(employment_type__in=['tenured', 'probationary', 'contract_ft'])

    def academic_only(self):
        """Filters for core teaching and research staff."""
        return self.filter(staff_category__in=['academic', 'teaching_only', 'research_only', 'admin_academic'])

    def non_academic_only(self):
        """Filters for operational, administrative, and support staff."""
        return self.exclude(staff_category__in=['academic', 'teaching_only', 'research_only', 'admin_academic'])


class StaffManager(models.Manager):
    """Default manager applying the custom StaffQuerySet logic."""

    def get_queryset(self):
        return StaffQuerySet(self.model, using=self._db)

    def active(self): return self.get_queryset().active()
    def permanent(self): return self.get_queryset().permanent()
    def academic(self): return self.get_queryset().academic_only()
    def non_academic(self): return self.get_queryset().non_academic_only()

    def expiring_contracts(self, days=30):
        """Finds staff members whose contracts are expiring within a specific window."""
        today = timezone.now().date()
        future_limit = today + timezone.timedelta(days=days)
        return self.filter(
            is_active=True,
            contract_end_date__range=[today, future_limit]
        )

    def active_grants(self):
        """Filters out all personnel actively funded by non-expired research grants."""
        today = timezone.now().date()
        return self.filter(
            employment_type='grant_funded',
            grant_expiry_date__gt=today
        )


class GlobalStaffUniverse:
    """Utility class to query across all separate concrete staff tables."""

    @staticmethod
    def _get_concrete_staff_models():
        return [
            model for model in apps.get_models()
            if issubclass(model, StaffProfile) and not model._meta.abstract
        ]

    @classmethod
    def all_active_academics(cls):
        """Fetches active academic records from all staff tables combined into a list."""
        results = []
        for model in cls._get_concrete_staff_models():
            results.extend(list(model.objects.active().academic()))
        return results

    @classmethod
    def all_active_non_academics(cls):
        """Fetches active non-academic records from all staff tables combined into a list."""
        results = []
        for model in cls._get_concrete_staff_models():
            results.extend(list(model.objects.active().non_academic()))
        return results
