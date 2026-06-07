from django.test import TestCase
from django.db import DatabaseError, transaction

from ..models import School, Department, Programme, Tclass, User, Student, Session, Reporting, FeeStructure, StudentFeeAccount, Payment, OverDraft

import datetime


class ModelsTestCase(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            school_name="Education"
        )

        self.department = Department.objects.create(
            department_name='English and Literature',
            school=self.school
        )

        self.programme = Programme.objects.create(
            programme_name='B.A in English and Literature',
            department=self.department
        )

        self.tclass = Tclass.objects.create(
            class_name='LIT/26',
            programme=self.programme
        )

        self.programme.current_class = self.tclass
        self.programme.save()

        self.student = User.objects.create(
            first_name='john',
            last_name='doe',
            surname='human',
            gender='M',
            email='john@email.com',
            role='student'
        )

        self.instance = Student.objects.create(
            user=self.student,
            marital_status='U',
            father_name='riley davis',
            father_id_no='267598276',
            father_date_of_birth=datetime.date(1970, 4, 12),
            mother_name='jane seymour',
            mother_id_no='84567231',
            mother_date_of_birth=datetime.date(1972, 6, 3),
            national_id='56045944',
            religion='christian',
            nationality='kenyan',
            ethnicity='Nandi',
            date_of_birth=datetime.date(2000, 4, 12),
            place_of_birth='turbo',
            telephone_no='0712345678',
            school_email='lit00426@inst.i.c',
            county='nandi',
            location='tambach',
            domicile='kenya',
            division='tapkigen',
            sub_county='tambach',
            constituency='tambach',
            home_adress='0038-56-tambach',
            emergency_contact_name='jane seymour',
            emergency_contact_phone='0784673738',
            emergency_contact_email='seymour@mail.co.ne',
            emergency_contact_relationship='Mother',
            emergency_contact_address='0038-56-tambach',
            emergency_contact_2_name='jane seymour',
            emergency_contact_2_phone='0784673738',
            emergency_contact_2_email='seymour@mail.co.ne',
            emergency_contact_2_relationship='Mother',
            emergency_contact_2_address='0038-56-tambach',
            registration_number='lit/004/26',
            class_entered=self.tclass,
            stay='outside',
            name_of_secondary_school='tambach secondary',
            address_of_secondary_school='0038-56-tambach'
        )

        self.session = Session.objects.create(
            academic_year="2025/2026",
            semester="1",
            start_date=datetime.date(2025, 8, 26),
            end_date=(
                datetime.date(2025, 8, 26) + datetime.timedelta(days=90)
            ),
            is_active=True
        )

        self.reporting = Reporting.objects.create(
            student=self.student,
            session=self.session,
            reported_via="online"
        )

        self.fee_structure = FeeStructure.objects.create(
            tclass=self.tclass,
            session=self.session,
            breakdown={
                "tuition": 45000,
                "registration": 5000,
                "hostel": 12000
            }
        )

        self.student_account = StudentFeeAccount.objects.create(
            student=self.instance,
            session=self.session,
            fee_structure=self.fee_structure,
        )

        self.payment = Payment.objects.create(
            account=self.student_account,
            amount=10000,
            method='mpesa',
            transaction_ref="random-string",
        )

    def test_school_creation(self):
        """test that school was created correctly
        """
        school = School.objects.get(school_name="Education")
        self.assertEqual(school.school_name, 'Education')

    def test_department_creation(self):
        """test creation of a department
        """
        department = Department.objects.get(
            department_name='English and Literature')

        self.assertEqual(department.department_name, 'English and Literature')

    def test_programme_creation(self):
        """test creation of programme"""

        programme = Programme.objects.get(
            programme_name="B.A in English and Literature"
        )

        self.assertEqual(
            programme.programme_name,
            'B.A in English and Literature'
        )

    def test_class_creation(self):
        """test creation of a class
        """

        tclass = Tclass.objects.get(class_name='LIT/26')

        self.assertEqual(tclass.class_name, 'LIT/26',
                         'class created sucessfuly')

    def test_user_creation(self):
        """tests if user was created succesfully
        """
        user = User.objects.get(email='john@email.com')
        student = Student.objects.get(user=user)

        self.assertEqual(student.registration_number, 'lit/004/26')

    def test_reported(self):
        instance = Reporting.objects.get(
            reporting_id=self.reporting.reporting_id
        )

        self.assertIsNot(
            instance,
            None
        )

        self.assertEqual(
            self.reporting.session.end_date.month,
            datetime.date(2025, 11, 26).month
        )

        self.assertEqual(
            self.reporting.reported_via,
            'online'
        )

    def test_fee_account(self):

        instance = StudentFeeAccount.objects.get(
            account_id=self.student_account.account_id
        )

        try:
            with transaction.atomic():
                Payment.objects.create(
                    account=self.student_account,
                    amount=56000,
                    method='mpesa',
                    transaction_ref="random",
                )

        except DatabaseError:
            print('db error')

        instance.refresh_from_db()

        try:
            with transaction.atomic():
                Payment.objects.create(
                    account=self.student_account,
                    amount=6000,
                    method='mpesa',
                    transaction_ref="rando",
                )

                instance.refresh_from_db()
        except DatabaseError:
            print('db error')

        overdraft = OverDraft.objects.filter(account=instance)

        self.assertNotEqual(instance, None)
        self.assertNotEqual(overdraft, None)
        self.assertTrue(instance.is_cleared)
        self.assertEqual(instance, overdraft[0].account)
