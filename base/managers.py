from django.contrib.auth.models import BaseUserManager
from django.db import models


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


class CommonUnitCurriculumManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            course__course_type='CC'
        )
