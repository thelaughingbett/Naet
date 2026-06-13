# Copyright 2026 Emmanuel Kipng'eno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

from .factories import (
    DepartmentFactory,
    SchoolFactory,
    SessionFactory,
    StudentFactory,
    TclassFactory,
)
from django.test import TestCase
from django.db import DatabaseError, transaction

from ..models import (
    School,
    Department,
    Programme,
    Tclass,
    User,
    Student,
    Session,
    Reporting,
    FeeStructure,
    StudentFeeAccount,
    Payment,
    OverDraft
)

import datetime


class StudentFeeAccountTest(TestCase):

    def setUp(self):
        # build minimum required objects
        self.session = Session.objects.create(
            academic_year='2024/2025',
            semester='1',
            start_date='2024-09-01',
            is_active=True
        )
        self.fee_structure = FeeStructure.objects.create(
            tclass=self.tclass,
            session=self.session,
            breakdown={
                'tuition': 45000,
                'registration': 5000
            }
        )
        self.account = StudentFeeAccount.objects.create(
            student=self.student,
            session=self.session,
            fee_structure=self.fee_structure,
            amount_paid=0
        )

    def test_total_amount(self):
        self.assertEqual(self.fee_structure.total_amount, 50000)

    def test_balance(self):
        self.assertEqual(self.account.balance, 50000)

    def test_is_not_cleared_initially(self):
        self.assertFalse(self.account.is_cleared)

    def test_is_cleared_after_full_payment(self):
        self.account.amount_paid = 50000
        self.account.save()
        self.assertTrue(self.account.is_cleared)

    def test_balance_after_partial_payment(self):
        self.account.amount_paid = 20000
        self.account.save()
        self.assertEqual(self.account.balance, 30000)


class PaymentTest(TestCase):

    def test_normal_payment_updates_balance(self):
        Payment.objects.create(
            account=self.account,
            amount=20000,
            method='mpesa',
            transaction_ref='MPESA001'
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.amount_paid, 20000)

    def test_overpayment_creates_overdraft(self):
        Payment.objects.create(
            account=self.account,
            amount=60000,  # more than the 50000 owed
            method='mpesa',
            transaction_ref='MPESA002'
        )
        self.assertTrue(
            OverDraft.objects.filter(account=self.account).exists()
        )
        overdraft = OverDraft.objects.get(account=self.account)
        self.assertEqual(overdraft.amount, 10000)

    def test_payment_rejected_if_account_cleared(self):
        self.account.amount_paid = 50000
        self.account.save()

        # should return early without saving
        Payment.objects.create(
            account=self.account,
            amount=5000,
            method='cash',
            transaction_ref='CASH001'
        )
        self.assertEqual(
            Payment.objects.filter(account=self.account).count(), 0
        )


class SessionModelTest(TestCase):

    def test_str(self):
        session = SessionFactory(academic_year='2025/2026', semester=1)
        self.assertIn('2025', str(session))

    def test_only_one_active_session(self):
        """Marking a session active should deactivate all others."""
        s1 = SessionFactory(is_active=True)
        s2 = SessionFactory(is_active=False)
        s2.is_active = True
        s2.save()
        s1.refresh_from_db()
        self.assertFalse(s1.is_active)
        self.assertTrue(s2.is_active)


class StudentModelTest(TestCase):

    def test_str(self):
        student = StudentFactory()
        self.assertIsNotNone(str(student))

    def test_student_belongs_to_class(self):
        tclass = TclassFactory()
        student = StudentFactory(class_entered=tclass)
        self.assertEqual(student.class_entered, tclass)
