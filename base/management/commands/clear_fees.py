import datetime
import random
from django.core.management.base import BaseCommand

from base.models import (
    FeeStructure,
    Session,
    Student,
    StudentFeeAccount,
    Payment,
    User
)


class Command(BaseCommand):
    help = 'Creates realistic demo data for the live showcase using factories and Faker'

    def handle(self, *args, **kwargs):
        student = Student.objects.get(registration_number='MBM23/0772')
        accounts = StudentFeeAccount.objects.filter(student=student)
        for account in accounts:
            if not account.is_cleared:
                Payment.objects.create(
                    account=account,
                    amount=account.balance,
                    status='completed',
                    method='cash'
                )
